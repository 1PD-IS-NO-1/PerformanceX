import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from gspread_dataframe import set_with_dataframe

# Define the scope (permissions for Google Sheets API)
scope = ["https://spreadsheets.google.com/feeds", 
         "https://www.googleapis.com/auth/drive"]
import traceback
from sheets_api import get_form_responses_1,get_form_responses_2
df1 = get_form_responses_1()
df2 = get_form_responses_2()
# Configuration
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

def transfer_attendance_to_sheets(attendance_df):
    """
    Transfer attendance data back to Google Sheets
    Args:
        attendance_df: DataFrame containing 'Email' and "Today's Date" columns
    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        # Validate input
        if attendance_df.empty:
            return False, "Empty attendance data provided"
            
        if "Email" not in attendance_df.columns or "Today's Date" not in attendance_df.columns:
            return False, "Missing required columns (Email or Today's Date)"
        
        # Authorize and get spreadsheet
        client = authorize_gsheets()
        spreadsheet = client.open_by_url(SPREADSHEET_URL)
        worksheet = spreadsheet.worksheet(ATTENDANCE_SHEET_NAME)
        
        # Prepare data
        attendance_df = attendance_df.copy()
        attendance_df["Date"] = attendance_df["Today's Date"].dt.strftime('%m-%d-%y')
        attendance_df['Present'] = 'P'
        
        # Pivot to wide format
        attendance_wide = attendance_df.pivot_table(
            index='Email', 
            columns='Date', 
            values='Present', 
            aggfunc='first', 
            fill_value=''
        ).reset_index()
        
        # Sort columns chronologically
        date_cols = [col for col in attendance_wide.columns if col != 'Email']
        date_cols_sorted = sorted(
            date_cols, 
            key=lambda x: pd.to_datetime(x, format='%m-%d-%y')
        )
        attendance_wide = attendance_wide[['Email'] + date_cols_sorted]
        
        # Update worksheet
        worksheet.clear()
        set_with_dataframe(worksheet, attendance_wide)
        
        return True, "Attendance successfully transferred to Google Sheets"
        
    except gspread.exceptions.APIError as e:
        error_msg = f"Google Sheets API Error: {str(e)}"
        print(error_msg)
        return False, error_msg
    except Exception as e:
        error_msg = f"Error transferring attendance: {str(e)}"
        print(error_msg)
        traceback.print_exc()
        return False, error_msg

def get_spreadsheet():
    """Get the spreadsheet object"""
    try:
        client = authorize_gsheets()
        return client.open_by_url(SPREADSHEET_URL)
    except Exception as e:
        print(f"Failed to access spreadsheet: {e}")
        raise

# Existing functions from sheets_api.py
def get_form_responses_1():
    """Fetches and returns data from 'Form responses 1' as a DataFrame."""
    try:
        spreadsheet = get_spreadsheet()
        sheet1 = spreadsheet.worksheet("Form responses 1")
        df = pd.DataFrame(sheet1.get_all_records())
        # Clean column names by stripping whitespace
        df.columns = [col.strip() for col in df.columns]
        return df
    except Exception as e:
        print(f"Error fetching Form responses 1: {e}")
        return pd.DataFrame()

def get_form_responses_2():
    """Fetches and returns data from 'Form responses 2' as a DataFrame."""
    try:
        spreadsheet = get_spreadsheet()
        sheet2 = spreadsheet.worksheet("Form responses 2")
        df = pd.DataFrame(sheet2.get_all_records())
        # Clean column names by stripping whitespace
        df.columns = [col.strip() for col in df.columns]
        return df
    except Exception as e:
        print(f"Error fetching Form responses 2: {e}")
        return pd.DataFrame()

def get_attendance_data():
    """Fetches attendance data from the Attendance worksheet"""
    try:
        spreadsheet = get_spreadsheet()
        worksheet = spreadsheet.worksheet("Attendance")
        records = worksheet.get_all_records()
        df = pd.DataFrame(records)
        # Clean column names by stripping whitespace
        df.columns = [col.strip() for col in df.columns]
        return df
    except Exception as e:
        print(f"Error fetching attendance data: {e}")
        return pd.DataFrame()

# New functions for weekly performance dashboard
def get_attendance_long_format():
    """Get attendance data in long format (Email, Date, Mark)"""
    try:
        att_df = get_attendance_data()
        if att_df.empty:
            return pd.DataFrame()
            
        # Convert from wide to long format
        attendance_long = att_df.melt(
            id_vars=["Email address"], 
            var_name="Date", 
            value_name="Mark"
        )
        attendance_long.columns = [col.strip() for col in attendance_long.columns]
        
        # Convert dates and filter for present marks
        attendance_long["Date"] = pd.to_datetime(
            attendance_long["Date"], 
            format="%m-%d-%y", 
            errors='coerce'
        )
        attendance_long = attendance_long.dropna(subset=["Date"])
        return attendance_long[attendance_long["Mark"] == "P"]
        
    except Exception as e:
        print(f"Error processing attendance data: {e}")
        return pd.DataFrame()


def get_weekly_performance_data(start_date, end_date):
    """
    Get combined performance data for a specific week
    Args:
        start_date: datetime - start of week
        end_date: datetime - end of week
    Returns:
        DataFrame with combined performance data
    """
    try:
        # Get data from both forms
        df1 = get_form_responses_1()
        df2 = get_form_responses_2()
        
        # Combine and filter for date range
        combined_df = pd.concat([df1, df2], ignore_index=True)
        combined_df["Today's Date"] = pd.to_datetime(
            combined_df["Today's Date"], 
            format="%d/%m/%Y", 
            errors='coerce'
        )
        
        weekly_df = combined_df[
            (combined_df["Today's Date"].dt.date >= start_date.date()) & 
            (combined_df["Today's Date"].dt.date <= end_date.date())
        ].copy()
        
        return weekly_df
        
    except Exception as e:
        print(f"Error getting weekly performance data: {e}")
        return pd.DataFrame()
    

def get_attendance_from_sheets():
    try:
        scope = ["https://spreadsheets.google.com/feeds", 
                "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name(
            "credentials.json", scope)
        client = gspread.authorize(creds)
        
        spreadsheet = client.open_by_url(SPREADSHEET_URL)
        attendance_ws = spreadsheet.worksheet("Attendance")
        
        att_df = pd.DataFrame(attendance_ws.get_all_records())
        att_df.columns = [col.strip() for col in att_df.columns]
        
        # Convert to long format
        attendance_long = att_df.melt(
            id_vars=["Email address"], 
            var_name="Date", 
            value_name="Mark"
        )
        attendance_long["Date"] = pd.to_datetime(
            attendance_long["Date"], 
            format="%m-%d-%y", 
            errors='coerce'
        )
        attendance_long = attendance_long.dropna(subset=["Date"])
        return attendance_long[attendance_long["Mark"] == "P"]
        
    except Exception as e:
        print(f"Error loading attendance from Google Sheets: {str(e)}")
        return pd.DataFrame()
def transfer_to_sheet(dataframe, worksheet_name):
    """Helper function to transfer data to a specific worksheet"""
    try:
        client = authorize_gsheets()
        spreadsheet = client.open_by_url(SPREADSHEET_URL)
        
        # Get or create worksheet
        try:
            worksheet = spreadsheet.worksheet(worksheet_name)
        except gspread.exceptions.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(worksheet_name, rows=100, cols=20)
        
        # Clear existing data and update
        worksheet.clear()
        set_with_dataframe(worksheet, dataframe)
        
        return True, "Transfer successful"
    except Exception as e:
        return False, f"Transfer failed: {str(e)}"