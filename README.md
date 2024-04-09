# CIS6930SP24-ASSIGNMENT2

# Author: Stavan Shah

# Assignment Description 

The task involves extracting information from multiple instances of data by parsing incident summary PDF files from the Norman Police Department and enhancing them. This enhancement entails generating tab-separated rows including details like Day of Week, Time of Data, weather, etc. 

## Table of Contents

- How to Install
- How to Run 
- Functions
- Output

## How to Install
  1. Clone repository to your local machine:
    $ git clone 
    $ cd cis6930sp24-assignment2
  2. Using Pipenv and Installing prerequisites:
    $ pipenv install
  3. Verify Installation: Once the command in step 3 is completed, verify if the dependencies are installed correctly by runing the following command:
    $ pipenv --version

## How to Run
- We must execute the following command in order to run the censor:
  ```
  pipenv run python assignment2.py --urls files.csv
  ```                  

## Functions Summary

### `calculate_town_side_from_bearing`
- Description: Determines which side of the town corresponds to a given bearing angle.

### `fetch_coordinates_from_address`
- Description: Retrieves latitude and longitude coordinates for a specified address.

### `initialize_incidents_database`
- Description: Sets up a SQLite database and creates a table named incidents to store data about incidents.

### `retrieve_incident_data_from_url`
- Description: Gathers incident data from a provided URL.

### `extractdata_populatedb`
- Description: Extracts data from a PDF file and populates the SQLite database with it.

### `status`
- Description: Presents the current status of incident data, including incident types and their respective counts.

### `writingAugmentedData`
- Description: Generates augmented data based on incident types.

### `sortAndRankLocations`
- Description: Organizes and ranks locations based on their occurrence frequency.

### `sortAndRankIncidents`
- Description: Arranges and ranks incidents based on their frequency of occurrence.

### `process_row`
- Description: Handles the processing of each row of incident data, extracting details such as date, time, location, and incident type.

### `delete_incidents_from_db`
- Description: Clears all records from the `incidents` table in the database.

### `main(csv_file)`
- Description: Primary function responsible for processing incident data from URLs specified in a CSV file.

### Output
- [Video Output](https://drive.google.com/drive/u/0/folders/1DRVznn_oRCXWsUMo9vDfUhNH_6PlbE6X)

### Author 
  - Stavan Shah
  - Email: stavannikhi.shah@ufl.edu
  - UFID: 76557015
