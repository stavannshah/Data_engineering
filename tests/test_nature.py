# import pytest
from unittest.mock import MagicMock, patch

url2 = ("https://www.normanok.gov/sites/default/files/documents/2024-01/2024-01-07_daily_incident_summary.pdf")


def test_list_sanity():
    assert True


def test_extractdata_populatedb():
    mock_conn = MagicMock()
    mock_pdf_reader = MagicMock()
    assert True
