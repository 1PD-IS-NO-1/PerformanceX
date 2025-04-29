import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import traceback
# Define the scope (permissions for Google Sheets API)
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# Load credentials from the JSON key file
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)

# Authenticate with Google Sheets
client = gspread.authorize(creds)

# Open the Google Sheet by ID or URL
sheet_id = "161ap6zuSkPNfmCXSS-3YkD-jD5lT8yT49Oo_3Q-dgf0"
spreadsheet = client.open_by_url(f"https://docs.google.com/spreadsheets/d/{sheet_id}")

SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/161ap6zuSkPNfmCXSS-3YkD-jD5lT8yT49Oo_3Q-dgf0"
ATTENDANCE_SHEET_NAME = "Attendance"

def authorize_gsheets():
    """Authenticate with Google Sheets API"""
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name(
            "credentials.json",
            ["https://spreadsheets.google.com/feeds", 
             "https://www.googleapis.com/auth/drive"]
        )
        return gspread.authorize(creds)
    except Exception as e:
        print(f"Authentication failed: {e}")
        traceback.print_exc()
        raise
def get_form_responses_1():
    try:
        client = authorize_gsheets()
        spreadsheet = client.open_by_url(SPREADSHEET_URL)
        sheet = spreadsheet.worksheet("Form responses 1")
        
        # Get data and clean column names
        df = pd.DataFrame(sheet.get_all_records())
        df.columns = [col.strip() for col in df.columns]
        
        # Standardize email column name
        if 'Email address' in df.columns:
            df.rename(columns={'Email address': 'Email'}, inplace=True)
            
        return df
    except Exception as e:
        
        print(f"Error loading Form responses 1: {e}")
        return pd.DataFrame() # Return empty DataFrame on error

def get_form_responses_2():
    """Fetches and returns data from 'Form responses 2' as a DataFrame."""
    sheet2 = spreadsheet.worksheet("Form responses 2")
    df2 = pd.DataFrame(sheet2.get_all_records())
    return df2

# Example usage:
df1 = get_form_responses_1()


# Define the scope (permissions for Google Sheets API)
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

def authorize_gsheets():
    """Authenticate with Google Sheets API"""
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    return gspread.authorize(creds)

def get_form_responses_1():
    """Fetches and returns data from 'Form responses 1' as a DataFrame."""
    try:
        client = authorize_gsheets()
        spreadsheet = client.open_by_url("https://docs.google.com/spreadsheets/d/161ap6zuSkPNfmCXSS-3YkD-jD5lT8yT49Oo_3Q-dgf0")
        sheet1 = spreadsheet.worksheet("Form responses 1")
        return pd.DataFrame(sheet1.get_all_records())
    except Exception as e:
        print(f"Error fetching Form responses 1: {e}")
        return pd.DataFrame()

def get_form_responses_2():
    """Fetches and returns data from 'Form responses 2' as a DataFrame."""
    try:
        client = authorize_gsheets()
        spreadsheet = client.open_by_url("https://docs.google.com/spreadsheets/d/161ap6zuSkPNfmCXSS-3YkD-jD5lT8yT49Oo_3Q-dgf0")
        sheet2 = spreadsheet.worksheet("Form responses 2")
        return pd.DataFrame(sheet2.get_all_records())
    except Exception as e:
        print(f"Error fetching Form responses 2: {e}")
        return pd.DataFrame()

def get_attendance_data():
    """Fetches attendance data from the Attendance worksheet"""
    try:
        client = authorize_gsheets()
        spreadsheet = client.open_by_url("https://docs.google.com/spreadsheets/d/161ap6zuSkPNfmCXSS-3YkD-jD5lT8yT49Oo_3Q-dgf0")
        worksheet = spreadsheet.worksheet("Attendance")
        records = worksheet.get_all_records()
        return pd.DataFrame(records)
    except Exception as e:
        print(f"Error fetching attendance data: {e}")
        return pd.DataFrame()