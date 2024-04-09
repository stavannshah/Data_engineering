from pypdf import PdfReader
import urllib.request
import io
import sqlite3
from sqlite3 import Error
import re
from _datetime import datetime
import requests
import csv
import openmeteo_requests
import math
import requests_cache
import pandas as pd
from retry_requests import retry
from collections import Counter
from vincenty import vincenty_inverse
import argparse

center_lat = 35.220833
center_lon = -97.443611
location_freq = Counter()
Locationranks = {}
incident_freq = Counter()
Incidentranks = {}
bearing_to_side = {
    (0, 22.5): 'N',
    (22.5, 67.5): 'NE',
    (67.5, 112.5): 'E',
    (112.5, 157.5): 'SE',
    (157.5, 202.5): 'S',
    (202.5, 247.5): 'SW',
    (247.5, 292.5): 'W',
    (292.5, 337.5): 'NW',
    (337.5, 360): 'N'
}

EMSSTATdict = {}


def calculate_town_side_from_bearing(bearing):
    for (start, end), side in bearing_to_side.items():
        if start <= bearing < end:
            return side
    return 'Unknown'


def fetch_coordinates_from_address(address):

    url_encode_address = requests.utils.quote(address)

    base_url = f"https://nominatim.openstreetmap.org/search?q={url_encode_address}&format=json&limit=1"

    response = requests.get(base_url)

    if response.status_code == 200:
        data = response.json()
        if data and len(data) > 0:
            return float(data[0]['lat']), float(data[0]['lon'])


def initialize_incidents_database():

    conn = sqlite3.connect('resources/normanpd.db')

    cursor = conn.cursor()
    cursor.execute('''DROP TABLE IF EXISTS incidents''')
    command1 = """CREATE TABLE IF NOT EXISTS incidents (
        date DATE,
        incident_number TEXT,
        location TEXT,
        nature TEXT,
        incident_ori TEXT
        )"""
    cursor.execute(command1)
    conn.commit()
    return conn


def retrieve_incident_data_from_url(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    # Ensure that the URL is passed as a string, not as a list
    if isinstance(url, list):
        url = url[0]

        # Fetch the content using requests.get()
        response = requests.get(url, headers=headers)
        data = response.content
        remote_file_bytes = io.BytesIO(data)

        # Create a PdfReader object from the binary data
        reader = PdfReader(remote_file_bytes)

        return reader
    else:
        print(f"Failed to fetch data from URL: {url}")
        return None


def extractdata_populatedb(conn, inc_data):

    cursor = conn.cursor()
    num_pages = len(inc_data.pages)
    for i in range(0, num_pages):
        page = inc_data.pages[i]
        text = page.extract_text()
        if i == 0:
            text = text.replace(
                'Date / Time Incident Number Location Nature Incident ORI', '')
            text = text.replace('NORMAN POLICE DEPARTMENT', '')
            text = text.replace('Daily Incident Summary (Public)', '')
        text = text.replace('\n', '')
        pattern = r'(\d{1,2}/\d{1,2}/\d{4}.*?)(?=\d{1,2}/\d{1,2}/\d{4}|$)'
        table_text = re.findall(pattern, text)

        if i == num_pages - 1:
            table_text.pop(len(table_text) - 1)

        for k in range(0, len(table_text)):
            table_text[k] = table_text[k].replace('\n', '')
            ln_text = table_text[k].split(' ')
            string = ''
            end_dict = {'Date / Time': ln_text[0]+' '+ln_text[1]}

            end_dict['Incident Number'] = ln_text[2]
            end_dict['Incident ORI'] = ln_text[-1]
            ln_text.remove(ln_text[0])
            ln_text.remove(ln_text[0])
            ln_text.remove(ln_text[0])
            ln_text.remove(ln_text[-1])

            for j in range(0, len(ln_text)):
                if any(c.islower() for c in ln_text[j]):
                    l = len(ln_text[j-1])
                    if ln_text[j-1][l-3:] == 'MVA':
                        string = 'MVA ' + string
                    for a in range(j, len(ln_text)):
                        if ln_text[a-1] == '911':
                            string += ln_text[a-1] + ' '
                        string += ln_text[a] + ' '
                    break
                elif ln_text[j] == 'COP':
                    string += ln_text[j] + ' '

                elif ln_text[j] == 'EMS':
                    string += ln_text[j] + ' '

                elif ln_text[j] == 'DDACTS':
                    string += ln_text[j] + ' '

            if string.strip() == 'Breathing Problems 1400':
                string = 'Breathing Problems'

            elif string.strip() == 'Assault EMS Needed 1400':
                string = 'Assault EMS Needed'

            elif string.strip() == 'RAMPMotorist Assist':
                string = 'Motorist Assist'

            elif string.strip() == 'Sick Person 1400':
                string = 'Sick Person'

            end_dict['Incident Type'] = string.strip()

            if end_dict['Incident Type'] in incident_freq:
                incident_freq[end_dict['Incident Type']] += 1
            else:
                incident_freq[end_dict['Incident Type']] = 1

            end_dict['Location'] = ' '.join(
                ln_text).replace(string.strip(), '').strip()

            if end_dict['Location'] in location_freq:
                location_freq[end_dict['Location']] += 1
            else:
                location_freq[end_dict['Location']] = 1

            try:

                cursor.execute("INSERT INTO incidents VALUES (?, ?, ?, ?, ?)", (
                    end_dict['Date / Time'], end_dict['Incident Number'], end_dict['Location'], end_dict['Incident Type'], end_dict['Incident ORI']))
                conn.commit()
            except Error as e:
                print("Data not fetched!! ", e)
                print(end_dict)

    sortAndRankLocations(location_freq)
    sortAndRankIncidents(incident_freq)
    return True


def status(conn):
    cursor = conn.cursor()
    try:
        cursor.execute('''select nature, count(distinct incident_number) from incidents 
                            group by nature 
                            order by count(incident_number) desc, nature asc
                            ''')

    except Error as e:
        print('Data not fetched!!: ', e)

    for row in cursor.fetchall():
        print(*row, sep='|')


def writingAugmentedData(conn):
    cursor = conn.cursor()

    EMSSTATdict = {}
    cursor.execute('''SELECT * FROM incidents''')
    results = cursor.fetchall()

    for index, row in enumerate(results):
        EMSSTATdict[index] = row[4]

    for index, row in enumerate(results):
        process_row(row, index)


def sortAndRankLocations(location_freq):
    sorted_locations = sorted(location_freq.items(),
                              key=lambda x: x[1], reverse=True)

    rank = 1
    current_freq = sorted_locations[0][1]

    for location, freq in sorted_locations:
        if freq < current_freq:
            rank += 1
            current_freq = freq
        Locationranks[location] = rank


def sortAndRankIncidents(incident_freq):
    sorted_incidents = sorted(incident_freq.items(),
                              key=lambda x: x[1], reverse=True)

    if sorted_incidents:
        rank = 1
        current_freq = sorted_incidents[0][1]

        for incident, freq in sorted_incidents:
            if freq < current_freq:
                rank += 1
                current_freq = freq
            Incidentranks[incident] = rank


def process_row(row, index):
    date, time = row[0].split(' ')
    address = row[2]
    incident_Type = row[3]
    current_EMSSTAT = False
    month, day, year = date.split('/')
    month = int(month)

    if month > 90:
        month = month - 90
    elif month > 50:
        month = month - 50

    corrected_date = f"{month}/{day}/{year}"
    dateProcessing = f"{year}-{month}-{day}"
    date_obj = datetime.strptime(dateProcessing, '%Y-%m-%d')

    dateForWeather = date_obj.strftime('%Y-%m-%d')

    # Day of the Week
    dayOfTheWeek = datetime.strptime(corrected_date, "%m/%d/%Y").weekday() + 1

   # Hour of the Day
    HourOfDay = (time.split(':'))[0]

    lat = 0.0
    lon = 0.0

    try:
        lat, lon = fetch_coordinates_from_address(address)
    except TypeError:
        lat, lon = fetch_coordinates_from_address('Norman, OK')
    except Exception as e:
        print(
            f"Error retrieving location for {address}: {e}")

    # WMO Code
    cache_session = requests_cache.CachedSession('.cache', expire_after=-1)
    retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
    openmeteo = openmeteo_requests.Client(session=retry_session)
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": dateForWeather,
        "end_date": dateForWeather,
        "hourly": ["weather_code"],
    }
    responses = openmeteo.weather_api(url, params=params)

    response = responses[0]
    hourly = response.Hourly()
    hourly_weather_code = hourly.Variables(0).ValuesAsNumpy()

    hourly_data = {
        "date": pd.date_range(
            start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
            end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
            freq=pd.Timedelta(seconds=hourly.Interval()),
            inclusive="left"
        ),
        "weather_code": hourly_weather_code
    }
    hourly_dataframe = pd.DataFrame(data=hourly_data)
    WMOcode = hourly_dataframe["weather_code"].iloc[int(HourOfDay)]

    # Side of the Town
    bearing = vincenty_inverse((center_lat, center_lon), (lat, lon))
    sideOfTown = calculate_town_side_from_bearing(bearing % 360)

    if row[4] == "EMSSTAT":
        current_EMSSTAT = True
    elif index + 1 in EMSSTATdict and EMSSTATdict[index + 1] == "EMSSTAT":
        current_EMSSTAT = True
        print("Worked")

    row = [dayOfTheWeek, HourOfDay, WMOcode, Locationranks[address],
           sideOfTown, Incidentranks[incident_Type], incident_Type, current_EMSSTAT]
    print('\t'.join(map(str, row)))


def delete_incidents_from_db(conn):
    cursor = conn.cursor()

    cursor.execute('''DELETE FROM incidents''')


def main(csv_file):
    urls = []
    with open(csv_file, 'r') as file:
        reader = csv.reader(file)
        for row in reader:
            # Assuming each row contains only one URL
            url = row[0]
            urls.append(url)

        for url in urls:
            if url:
                inc_data = retrieve_incident_data_from_url([url])
                db = initialize_incidents_database()
                extractdata_populatedb(db, inc_data)
                writingAugmentedData(db)
            else:
                print("Files.csv End")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Process incidents PDF file or URLs from a CSV file")
    parser.add_argument("--urls", help="./files.csv")
    args = parser.parse_args()

    if args.urls:
        main(args.urls)
    else:
        print("Provide the --urls argument with the filename.")
