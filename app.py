import os
from flask import Flask, render_template, request, jsonify, send_file, session, redirect, url_for
from performance_analysis import (
    df1, df2, process_attendance, fetch_tasks, compute_performance,
    generate_ai_insights, plot_performance_graph, generate_behavior_insights,
    generate_individual_radar, plot_individual_timeline,
    individual_performance_comparison, calculate_summary_metrics,
    analyze_deadline_performance, calculate_weekly_performance  # Add this function to performance_analysis.py
)
from dotenv import load_dotenv
import base64
import tempfile
import pandas as pd
load_dotenv()
from sheets_api import get_form_responses_1,get_form_responses_2
from oauth2client.service_account import ServiceAccountCredentials
import gspread
import pandas as pd
from datetime import datetime, timedelta
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'default-secret-key')

# Main navigation routes
from datetime import datetime

@app.route('/')
def index():
    return render_template('index.html', now=datetime.now())

@app.route('/dashboard')
def dashboard():
    try:
        emails = df1['Email'].unique().tolist()
        
        # Calculate metrics
        metrics = {
            'total_interns': len(emails),
            'avg_hours': safe_mean(df1, 'Number of hours worked'),
            'completion_rate': safe_completion_rate(df1),
            'attendance_rate': safe_attendance_rate(df1, emails),
            'avg_tasks': safe_avg_tasks(df1)
        }
        
        # Prepare performance data for charts
        performance_data = {
            'dates': get_unique_dates(df1),
            'completion_rates': get_completion_rates(df1),
            'attendance_rates': get_attendance_rates(df1, emails),
            'task_counts': df1['Task Status'].value_counts().values.tolist(),
            'task_statuses': df1['Task Status'].value_counts().index.tolist()
        }
        
        return render_template(
            'dashboard.html',
            emails=emails,
            metrics=metrics,
            performance_data=performance_data,
            now=datetime.now()
        )
    except Exception as e:
        print(f"Error in dashboard route: {str(e)}")
        return render_template(
            'dashboard.html',
            emails=[],
            metrics={
                'total_interns': 0,
                'avg_hours': 0,
                'completion_rate': 0,
                'attendance_rate': 0,
                'avg_tasks': 0
            },
            performance_data={},
            now=datetime.now()
        )

# Add these helper functions
def parse_date(date_str):
    """Consistent date parsing for the application with multiple format support"""
    try:
        # Try d/m/Y format first (e.g., 01/04/2024)
        return pd.to_datetime(date_str, format="%d/%m/%Y", errors='coerce')
    except:
        try:
            # Fallback to d/m/y format (e.g., 01/04/24)
            return pd.to_datetime(date_str, format="%d/%m/%y", errors='coerce')
        except:
            # Final fallback with dayfirst=True
            return pd.to_datetime(date_str, dayfirst=True, errors='coerce')

def format_date(date_obj):
    """Consistent date formatting for display"""
    return date_obj.strftime("%d/%m/%y") if pd.notna(date_obj) else ""
def get_unique_dates(df):
    try:
        return pd.to_datetime(df["Today's Date"], format="%d/%m/%Y").dt.strftime("%d/%m/%y").unique().tolist()
    except:
        return []

def get_completion_rates(df):
    try:
        return df.groupby("Today's Date")['Task Status'].apply(
            lambda x: (x == 'Completed').mean() * 100
        ).values.tolist()
    except:
        return []

def get_attendance_rates(df, emails):
    try:
        return df.groupby("Today's Date")['Email'].nunique().apply(
            lambda x: x / len(emails) * 100
        ).values.tolist()
    except:
        return []

def safe_avg_tasks(df):
    try:
        return df.groupby('Email')['Assigned Task Name'].count().mean()
    except:
        return 0.0
    
def safe_mean(df, column_name):
    try:
        return df[column_name].astype(float).mean()
    except:
        return 0.0

def safe_completion_rate(df):
    try:
        return (df['Task Status'] == 'Completed').mean() * 100
    except:
        return 0.0

def safe_attendance_rate(df, emails):
    try:
        unique_attendees = df['Email'].nunique()
        return unique_attendees / len(emails) * 100 if emails else 0.0
    except:
        return 0.0


# Add similar now=datetime.now() to all other routes
@app.context_processor
def inject_now():
    return {'now': datetime.now()}

@app.route('/attendance')
def attendance():
    try:
        # Load attendance sheet
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
        client = gspread.authorize(creds)

        spreadsheet = client.open_by_url("https://docs.google.com/spreadsheets/d/161ap6zuSkPNfmCXSS-3YkD-jD5lT8yT49Oo_3Q-dgf0/edit#gid=146636558")
        worksheet = spreadsheet.worksheet("Attendance")

        attendance_data = worksheet.get_all_values()
        attendance_df_raw = pd.DataFrame(attendance_data[1:], columns=attendance_data[0])
        attendance_df_raw = attendance_df_raw.rename(columns=lambda x: x.strip())

        # Get list of employees
        employees = attendance_df_raw["Email address"].unique().tolist()
        
        # Generate current month's dates
        today = datetime.today()
        start_of_month = today.replace(day=1)
        
        all_dates = []
        all_date_str_cols = []
        for i in range(today.day):
            date = start_of_month + timedelta(days=i)
            display_date = date.strftime("%d/%m/%Y")
            sheet_col_format = date.strftime("%d-%m-%y")
            all_dates.append(display_date)
            all_date_str_cols.append(sheet_col_format)
        
        # Process attendance for all employees
        employee_attendance = {}
        for email in employees:
            employee_row = attendance_df_raw[attendance_df_raw["Email address"] == email]
            if not employee_row.empty:
                present_days = 0
                status_list = []
                
                for date_str_col, display_date in zip(all_date_str_cols, all_dates):
                    if date_str_col in employee_row.columns and employee_row[date_str_col].values[0].strip().upper() == "P":
                        present_days += 1
                        status_list.append({"date": display_date, "status": "present"})
                    else:
                        status_list.append({"date": display_date, "status": "absent"})
                
                total_days = len(status_list)
                attendance_rate = (present_days / total_days * 100) if total_days > 0 else 0
                
                employee_attendance[email] = {
                    "present_days": present_days,
                    "total_days": total_days,
                    "attendance_rate": attendance_rate,
                    "status_list": status_list
                }

        # Check if employee is selected
        selected_email = request.args.get('email')
        selected_data = employee_attendance.get(selected_email) if selected_email else None

        return render_template('attendance.html',
                            employees=employees,
                            employee_attendance=employee_attendance,
                            selected_email=selected_email,
                            selected_data=selected_data,
                            current_date=today.strftime("%B %Y"))
        
    except Exception as e:
        return render_template('attendance.html',
                            error_message=f"Failed to load attendance data: {str(e)}",
                            current_date=datetime.today().strftime("%B %Y"))

@app.route('/deadlines')
def deadlines():
    deadline_stats = analyze_deadline_performance(df1)
    return render_template('deadlines.html', deadline_stats=deadline_stats)

from datetime import datetime, timedelta
import pandas as pd
import traceback
# ... (keep all your existing imports and setup)@app.route('/api/data-status')
def data_status():
    global df1, df2
    
    status = {
        'df1_loaded': not df1.empty,
        'df2_loaded': not df2.empty,
        'df1_columns': list(df1.columns) if not df1.empty else [],
        'df2_columns': list(df2.columns) if not df2.empty else [],
        'date_column_present': "Today's Date" in df1.columns if not df1.empty else False,
        'email_column_present': "Email" in df1.columns if not df1.empty else False
    }
    
    return jsonify(status)
@app.route('/weekly')
def weekly():
    try:
        # === Data Validation ===
        if df1.empty:
            return render_template('weekly.html',
                                weekly_data={},
                                error="No task data available",
                                now=datetime.now())

        # Check required columns
        required_columns = ["Today's Date", "Intern name", "Assigned Task Name",
                          "Task Status", "Number of hours worked", "Email"]
        missing_cols = [col for col in required_columns if col not in df1.columns]
        if missing_cols:
            return render_template('weekly.html',
                                weekly_data={},
                                error=f"Missing columns: {', '.join(missing_cols)}",
                                now=datetime.now())

        # === Date Handling ===
        df1["Today's Date"] = pd.to_datetime(df1["Today's Date"], format="%d/%m/%Y", errors='coerce')
        today = datetime.today()
        this_week_start = today - timedelta(days=today.weekday())  # Monday
        this_week_end = this_week_start + timedelta(days=6)        # Sunday

        # === Week Filtering ===
        weekly_df = df1[
            (df1["Today's Date"].dt.date >= this_week_start.date()) &
            (df1["Today's Date"].dt.date <= this_week_end.date())
        ].copy()

        if weekly_df.empty:
            return render_template('weekly.html',
                                weekly_data={},
                                error="No data available for this week",
                                now=datetime.now())

        # === Attendance Data (Fail Gracefully) ===
        attendance_data = None
        try:
            scope = ["https://spreadsheets.google.com/feeds", 
                    "https://www.googleapis.com/auth/drive"]
            creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
            client = gspread.authorize(creds)
            
            # DOUBLE CHECK THIS URL MATCHES YOUR SHEET
            spreadsheet = client.open_by_url(
                "https://docs.google.com/spreadsheets/d/161ap6zuSkPNfmCXSS-3YkD-jD5lT8yT49Oo_3Q-dgf0/edit#gid=146636558"
            )
            worksheet = spreadsheet.worksheet("Attendance")
            
            att_data = worksheet.get_all_values()
            att_df = pd.DataFrame(att_data[1:], columns=att_data[0])
            att_df.columns = [col.strip() for col in att_df.columns]
            
            # Convert to long format
            attendance_long = att_df.melt(id_vars=["Email address"], 
                                        var_name="Date", 
                                        value_name="Mark")
            attendance_long["Date"] = pd.to_datetime(attendance_long["Date"], 
                                                   format="%d-%m-%y", 
                                                   errors='coerce')
            attendance_long = attendance_long.dropna(subset=["Date"])
            attendance_data = attendance_long[attendance_long["Mark"] == "P"]
            
        except Exception as e:
            print(f"Attendance load warning: {str(e)}")
            # Continue without attendance data

        # === Calculate Metrics ===
        total_interns = weekly_df['Email'].nunique()
        
        # Handle hours calculation safely
        try:
            weekly_df['Number of hours worked'] = pd.to_numeric(weekly_df['Number of hours worked'], errors='coerce')
            avg_hours = weekly_df.groupby('Email')['Number of hours worked'].sum().mean()
        except:
            avg_hours = 0
            
        task_completion = (weekly_df['Task Status'] == 'Completed').mean() * 100

        # === Generate Records ===
        attendance_records = []
        summary_data = []
        
        for email in weekly_df['Email'].unique():
            intern_data = weekly_df[weekly_df['Email'] == email]
            intern_name = intern_data['Intern name'].iloc[0] if 'Intern name' in intern_data.columns else email
            
            days_present = 0
            total_hours = 0

            for day in range(7):  # Monday to Sunday
                current_date = this_week_start + timedelta(days=day)
                date_str = current_date.strftime('%Y-%m-%d')
                
                # Check attendance if data exists
                present = False
                if attendance_data is not None:
                    present = not attendance_data[
                        (attendance_data["Email address"] == email) & 
                        (attendance_data["Date"].dt.date == current_date.date())
                    ].empty
                else:
                    # Fallback: consider present if they have tasks that day
                    tasks_on_day = intern_data[
                        intern_data["Today's Date"].dt.date == current_date.date()
                    ]
                    present = not tasks_on_day.empty
                
                if present:
                    days_present += 1
                
                # Get day's tasks
                tasks_on_day = intern_data[
                    intern_data["Today's Date"].dt.date == current_date.date()
                ]
                
                hours = tasks_on_day['Number of hours worked'].sum()
                total_hours += hours
                
                tasks = tasks_on_day['Assigned Task Name'].dropna().tolist()
                statuses = tasks_on_day['Task Status'].dropna().tolist()
                additional_tasks = tasks_on_day['Additional Task done'].dropna().tolist()

                attendance_records.append({
                    'Email': email,
                    'Name': intern_name,
                    'Date': current_date.strftime('%d/%m/%Y'),
                    'Present': "✅" if present else "❌",
                    'Hours Worked': hours,
                    'Tasks Assigned': ", ".join(tasks) if tasks else "-",
                    'Task Status': ", ".join(statuses) if statuses else "-",
                    'Additional Task': ", ".join(additional_tasks) if additional_tasks else "-"
                })

            attendance_pct = (days_present / 7) * 100
            summary_data.append({
                'Email': email,
                'Name': intern_name,
                'Days Present': days_present,
                'Total Days': 7,
                'Attendance %': round(attendance_pct, 1),
                'Total Hours Worked': round(total_hours, 1)
            })

        return render_template(
            'weekly.html',
            weekly_data={
                'total_interns': total_interns,
                'avg_hours': round(avg_hours, 1),
                'task_completion': round(task_completion, 1),
                'attendance_records': attendance_records,
                'summary': summary_data
            },
            now=datetime.now()
        )

    except Exception as e:
        print(f"Error in weekly route: {str(e)}")
        return render_template(
            'weekly.html',
            weekly_data={},
            error=f"System error: {str(e)}",
            now=datetime.now()
        )

@app.route('/api/weekly-performance', methods=['POST'])
def api_weekly_performance():
    try:
        data = request.get_json()
        week_option = data.get('week_option', 'this-week')
        
        # === Date Range Calculation ===
        today = datetime.today()
        this_week_start = today - timedelta(days=today.weekday())  # Monday
        this_week_end = this_week_start + timedelta(days=6)        # Sunday

        if week_option == 'prev-week':
            week_start = this_week_start - timedelta(days=7)
            week_end = this_week_start - timedelta(days=1)
        else:
            week_start = this_week_start
            week_end = this_week_end

        # === Week Days Calculation (Excluding Sundays) ===
        week_days = [week_start + timedelta(days=i) for i in range(7) 
                    if (week_start + timedelta(days=i)).weekday() != 6]

        # === Load and Filter Task Data ===
        if not pd.api.types.is_datetime64_any_dtype(df1["Today's Date"]):
            df1["Today's Date"] = pd.to_datetime(df1["Today's Date"], format="%d/%m/%Y", errors='coerce')
        
        weekly_df = df1[
            (df1["Today's Date"].dt.date >= week_start.date()) & 
            (df1["Today's Date"].dt.date <= week_end.date())
        ].copy()

        if weekly_df.empty:
            return jsonify({
                'message': 'No data available for selected week',
                'total_interns': 0,
                'avg_hours': 0.0,
                'task_completion': 0.0,
                'attendance_records': [],
                'summary': []
            })

        # === Load Attendance Data (Exact Streamlit Logic) ===
        attendance_long = None
        try:
            scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
            creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
            client = gspread.authorize(creds)
            
            # Use the exact same URL as Streamlit
            spreadsheet = client.open_by_url(
                "https://docs.google.com/spreadsheets/d/161ap6zuSkPNfmCXSS-3YkD-jD5lT8yT49Oo_3Q-dgf0/edit#gid=146636558"
            )
            worksheet = spreadsheet.worksheet("Attendance")
            
            # Get all records (same as Streamlit)
            att_data = worksheet.get_all_records()
            att_df = pd.DataFrame(att_data)
            att_df.columns = [col.strip() for col in att_df.columns]
            
            # Melt and filter exactly like Streamlit
            attendance_long = att_df.melt(
                id_vars=["Email address"], 
                var_name="Date", 
                value_name="Mark"
            )
            attendance_long["Date"] = pd.to_datetime(
                attendance_long["Date"], 
                format="%d-%m-%y",  # Same format as Streamlit
                errors='coerce'
            )
            attendance_long = attendance_long.dropna(subset=["Date"])
            attendance_long = attendance_long[attendance_long["Mark"] == "P"]  # Exact same filter
            
        except Exception as e:
            print(f"Attendance load error: {str(e)}")
            return jsonify({
                'error': f"Failed to load attendance data: {str(e)}",
                'total_interns': 0,
                'avg_hours': 0.0,
                'task_completion': 0.0,
                'attendance_records': [],
                'summary': []
            }), 500

        # === Calculate Metrics (Same as Streamlit) ===
        total_interns = int(weekly_df['Email'].nunique())
        
        # Handle hours calculation (same as Streamlit)
        try:
            weekly_df['Number of hours worked'] = pd.to_numeric(
                weekly_df['Number of hours worked'], 
                errors='coerce'
            )
            avg_hours = float(weekly_df.groupby('Email')['Number of hours worked'].sum().mean())
        except:
            avg_hours = 0.0
            
        task_completion = float(
            (weekly_df[weekly_df['Task Status'] == 'Completed'].shape[0] / weekly_df.shape[0]) * 100 
            if weekly_df.shape[0] > 0 else 0
        )

        # === Generate Records (Exact Streamlit Logic) ===
        attendance_records = []
        summary_data = []

        for email in weekly_df['Email'].unique():
            intern_data = weekly_df[weekly_df['Email'] == email]
            intern_name = str(intern_data['Intern name'].iloc[0]) if 'Intern name' in intern_data.columns else str(email)
            
            days_present = 0
            total_hours = 0.0
            daily_records = []

            for date in week_days:
                day_str = date.strftime('%Y-%m-%d')
                tasks_on_day = intern_data[intern_data["Today's Date"].dt.date == date.date()]
                
                # Exact same attendance check as Streamlit
                present = not attendance_long[
                    (attendance_long["Email address"] == email) & 
                    (attendance_long["Date"].dt.date == date.date())
                ].empty
                
                if present:
                    days_present += 1
                
                hours = float(tasks_on_day['Number of hours worked'].sum())
                total_hours += hours
                
                tasks = [str(t) for t in tasks_on_day['Assigned Task Name'].dropna().tolist()]
                statuses = [str(s) for s in tasks_on_day['Task Status'].dropna().tolist()]
                additional_tasks = [str(a) for a in tasks_on_day['Additional Task done'].dropna().tolist()]

                daily_records.append({
                    'Email': str(email),
                    'Name': str(intern_name),
                    'Date': date.strftime('%d/%m/%Y'),
                    'Present': "✅" if present else "❌",
                    'Hours Worked': hours,
                    'Tasks Assigned': ", ".join(tasks) if tasks else "-",
                    'Task Status': ", ".join(statuses) if statuses else "-",
                    'Additional Task': ", ".join(additional_tasks) if additional_tasks else "-"
                })
            
            attendance_records.extend(daily_records)
            
            # Calculate attendance percentage (same as Streamlit)
            total_days = len(week_days)
            attendance_pct = float((days_present / total_days) * 100) if total_days > 0 else 0.0
            
            summary_data.append({
                'Email': str(email),
                'Name': str(intern_name),
                'Days Present': int(days_present),
                'Total Days': int(total_days),
                'Attendance %': round(attendance_pct, 1),
                'Total Hours Worked': round(total_hours, 1)
            })

        # Sort summary by attendance % descending (same as Streamlit)
        summary_data.sort(key=lambda x: x['Attendance %'], reverse=True)

        return jsonify({
            'total_interns': total_interns,
            'avg_hours': avg_hours,
            'task_completion': task_completion,
            'attendance_records': attendance_records,
            'summary': summary_data
        })

    except Exception as e:
        print(f"API Error: {str(e)}\n{traceback.format_exc()}")
        return jsonify({
            'error': str(e),
            'total_interns': 0,
            'avg_hours': 0.0,
            'task_completion': 0.0,
            'attendance_records': [],
            'summary': []
        }), 500
try:
    df3 = get_form_responses_1()
    df2 = get_form_responses_2()
    
    # Ensure we have the required columns
    if "Today's Date" in df3.columns:
        df3["Today's Date"] = pd.to_datetime(df3["Today's Date"], format="%d/%m/%Y", errors='coerce')
    if "Email" not in df1.columns and "Email address" in df1.columns:
        df3.rename(columns={"Email address": "Email"}, inplace=True)
        
except Exception as e:
    print(f"Failed to initialize data: {str(e)}")
    df3 = pd.DataFrame()
    df2 = pd.DataFrame()


@app.route('/api/transfer-attendance', methods=['POST'])
def transfer_attendance():
    try:
        from sheets_api import get_form_responses_1, get_form_responses_2
        from sheets_integration import authorize_gsheets, SPREADSHEET_URL
        from gspread_dataframe import set_with_dataframe

        # Step 1: Load and merge form responses
        df1 = get_form_responses_1()
        df2 = get_form_responses_2()
        df = pd.concat([df1, df2], ignore_index=True)
        
        # Step 2: Clean and verify columns
        df.columns = [col.strip() for col in df.columns]
        for col in df.select_dtypes(include=['object']).columns:
            df[col] = df[col].fillna('')

        email_col = 'Email address'
        
        required_columns = [email_col, "Today's Date"]
        missing = [col for col in required_columns if col not in df.columns]
        if missing:
            return jsonify({
                'success': False,
                'error': f"Missing required columns: {', '.join(missing)}",
                'available_columns': list(df.columns)
            }), 400

        # Step 3: Process attendance data with proper date handling
        df["Today's Date"] = pd.to_datetime(df["Today's Date"], errors='coerce', dayfirst=True)
        df = df.dropna(subset=["Today's Date"])
        if df.empty:
            return jsonify({
                'success': False,
                'error': "No valid dates found after parsing."
            }), 400

        # Convert to dd-mm-yy format for consistency
        df['Date'] = df["Today's Date"].dt.strftime('%d-%m-%y')
        df['Present'] = 'P'

        # Pivot the data
        attendance = df.pivot_table(
            index=email_col,
            columns='Date',
            values='Present',
            aggfunc='first',
            fill_value=''
        )

        # Custom sorting function for dates in dd-mm-yy format
        def date_sort_key(col):
            try:
                day, month, year = map(int, col.split('-'))
                return (year, month, day)
            except:
                return (0, 0, 0)

        # Sort columns by date
        attendance = attendance.reindex(
            sorted(attendance.columns, key=date_sort_key),
            axis=1
        )
        attendance.reset_index(inplace=True)

        # Step 4: Merge with existing sheet and update
        client = authorize_gsheets()
        spreadsheet = client.open_by_url(SPREADSHEET_URL)
        worksheet = spreadsheet.worksheet("Attendance")
        
        # Load existing data
        existing_df = pd.DataFrame(worksheet.get_all_records())

        # Normalize date formatting function
        def normalize_date_col(col):
            try:
                return pd.to_datetime(col, dayfirst=True).strftime('%d-%m-%y')
            except:
                return col

        # Normalize column names
        attendance.columns = [normalize_date_col(col) if col != email_col else col for col in attendance.columns]
        if existing_df.empty:
            # Create an empty DataFrame with just email column to merge on
            existing_df = pd.DataFrame(columns=[email_col])

        existing_df.columns = [normalize_date_col(col) if col != email_col else col for col in existing_df.columns]

        # Merge both DataFrames
        merged_df = pd.merge(existing_df, attendance, on=email_col, how='outer', suffixes=('', '_new'))

        # Combine attendance entries: keep 'P' if in either
        for col in attendance.columns:
            if col == email_col:
                continue
            col_new = f"{col}_new"
            if col_new in merged_df.columns:
                merged_df[col] = merged_df[[col_new, col]].apply(
                    lambda row: 'P' if 'P' in (row[col], row[col_new]) else '',
                    axis=1
                )
                merged_df.drop(columns=[col_new], inplace=True)

        # Final column sorting
        # Final column sorting
        date_cols = [col for col in merged_df.columns if col != email_col]
        merged_df = merged_df[[email_col] + sorted(date_cols, key=date_sort_key)]

        # Force dd-mm-yy column names as strings
        def format_header(col):
            try:
                if col != email_col:
                    return pd.to_datetime(col, dayfirst=True).strftime('%d-%m-%y')
                return col
            except:
                return col

        formatted_columns = [format_header(col) for col in merged_df.columns]
        merged_df.columns = formatted_columns

        # Clear the worksheet
        worksheet.clear()

        # Step 1: Upload headers manually as plain text (row 1)
        worksheet.update('A1', [formatted_columns])

        # Step 2: Upload data without headers starting from row 2
        from gspread_dataframe import set_with_dataframe
        set_with_dataframe(worksheet, merged_df, row=2, include_column_header=False)

        return jsonify({
            'success': True,
            'message': "✅ Attendance successfully transferred to Google Sheet!",
            'transferred_rows': len(df)
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc(),
            'available_columns': list(df.columns) if 'df' in locals() else []
        }), 500


def generate_weekly_attendance_data(weekly_df, week_start, week_end):
    """Helper function to generate attendance records and summary"""
    try:
        weekly_df = weekly_df.copy()
        weekly_df["Today's Date"] = pd.to_datetime(weekly_df["Today's Date"], errors='coerce')
        
        week_days = [week_start + timedelta(days=i) for i in range(7) 
                    if (week_start + timedelta(days=i)).weekday() != 6]
        
        attendance_records = []
        summary = []
        
        for email in weekly_df['Email'].unique():
            intern_data = weekly_df[weekly_df['Email'] == email]
            intern_name = intern_data['Intern name'].iloc[0] if 'Intern name' in intern_data.columns else email
            
            days_present = 0
            total_hours = 0
            
            for date in week_days:
                day_str = date.strftime('%d/%m/%y')  # Format as d/m/y
                
                tasks_on_day = intern_data[
                    intern_data["Today's Date"].dt.date == date.date()
                ]
                
                present = not tasks_on_day.empty
                if present:
                    days_present += 1
                
                hours = tasks_on_day['Number of hours worked'].sum() if 'Number of hours worked' in tasks_on_day.columns else 0
                total_hours += hours
                
                tasks = tasks_on_day['Assigned Task Name'].dropna().tolist() if 'Assigned Task Name' in tasks_on_day.columns else []
                statuses = tasks_on_day['Task Status'].dropna().tolist() if 'Task Status' in tasks_on_day.columns else []
                additional_tasks = tasks_on_day[tasks_on_day['Additional Task done'].notna()]['Additional Task done'].tolist() if 'Additional Task done' in tasks_on_day.columns else []

                attendance_records.append({
                    'Email': email,
                    'Name': intern_name,
                    'Date': day_str,  # Already in d/m/y format
                    'Present': "✅" if present else "❌",
                    'Hours Worked': hours,
                    'Tasks Assigned': ", ".join(tasks) if tasks else "-",
                    'Task Status': ", ".join(statuses) if statuses else "-",
                    'Additional Task': ", ".join(additional_tasks) if additional_tasks else "-"
                })
            
            attendance_pct = (days_present / len(week_days)) * 100 if len(week_days) > 0 else 0
            
            summary.append({
                'Email': email,
                'Name': intern_name,
                'Days Present': days_present,
                'Total Days': len(week_days),
                'Attendance %': attendance_pct,
                'Total Hours Worked': total_hours
            })
        
        return attendance_records, summary
    except Exception as e:
        print(f"Error in generate_weekly_attendance_data: {str(e)}")
        return [], []

# ... (keep all your existing routes and functions below)
# API endpoints
@app.route('/get_performance_data', methods=['POST'])
def get_performance_data():
    email = request.json.get('email')
    if not email:
        return jsonify({'error': 'Email is required'}), 400
    
    attendance = process_attendance(df1)
    tasks = fetch_tasks(df1)
    performance = compute_performance(df1)
    
    bar_graph, pie_graph = plot_performance_graph(email, performance, attendance, tasks)
    insights = generate_ai_insights(df1).get(email, "No insights available")
    
    intern_df = df1[df1['Email'] == email]
    radar_chart = generate_individual_radar(intern_df)
    timeline_chart = plot_individual_timeline(intern_df)
    comparison_chart = individual_performance_comparison(intern_df, df1)
    
    return jsonify({
        'email': email,
        'attendance': attendance.get(email, 0),
        'performance': performance.get(email, 0),
        'bar_graph': bar_graph,
        'pie_graph': pie_graph,
        'insights': insights,
        'radar_chart': radar_chart,
        'timeline_chart': timeline_chart,
        'comparison_chart': comparison_chart
    })

@app.route('/get_behavior_insights', methods=['POST'])
def get_behavior_insights():
    email = request.json.get('email')
    groq_api_key = os.getenv('GROQ_API_KEY')
    
    if not email:
        return jsonify({'error': 'Email is required'}), 400
    
    insights, pdf_data = generate_behavior_insights(email, df2, groq_api_key)
    
    if not insights:
        return jsonify({'error': pdf_data}), 400
    
    return jsonify({
        'email': email,
        'insights': insights,
        'pdf_data': pdf_data
    })

@app.route('/download_insights', methods=['POST'])
def download_insights():
    try:
        data = request.get_json()
        pdf_data = data.get('pdf_data')
        email = data.get('email')
        
        if not pdf_data or not email:
            return jsonify({'error': 'Missing PDF data or email'}), 400

        pdf_bytes = base64.b64decode(pdf_data)
        
        # Create in-memory file
        from io import BytesIO
        mem_file = BytesIO()
        mem_file.write(pdf_bytes)
        mem_file.seek(0)
        
        return send_file(
            mem_file,
            as_attachment=True,
            download_name=f"{email}_insights.pdf",
            mimetype='application/pdf'
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Add these new routes
@app.route('/get_filtered_data', methods=['POST'])
def get_filtered_data():
    filters = request.json
    filtered_df = df1.copy()
    
    # Apply filters
    if filters.get('emails'):
        filtered_df = filtered_df[filtered_df['Email'].isin(filters['emails'])]
    if filters.get('date_range'):
        filtered_df = filtered_df[(filtered_df['Date'] >= filters['date_range'][0]) & 
                                (filtered_df['Date'] <= filters['date_range'][1])]
    
    # Convert to dict for JSON response
    return jsonify(filtered_df.to_dict('records'))

@app.route('/export_data', methods=['POST'])
def export_data():
    data = request.json.get('data')
    format_type = request.json.get('format', 'csv')
    
    if format_type == 'csv':
        from io import StringIO
        output = StringIO()
        pd.DataFrame(data).to_csv(output)
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-disposition": "attachment; filename=export.csv"}
        )
    elif format_type == 'json':
        return jsonify(data)
    
if __name__ == '__main__':
    app.run(debug=True)