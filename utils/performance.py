import pandas as pd
from datetime import datetime
from collections import defaultdict
import plotly.graph_objects as go
from functools import lru_cache
from sheets_api import get_form_responses_1, get_form_responses_2
import requests
from fpdf import FPDF
import base64
import plotly.express as px
import json

# Task status conversion rates
TASK_CONVERSION = {
    "Completed": 100,
    "Ongoing": 60,
    "Research": 30,
    "Finishing": 90
}

df1 = get_form_responses_1()
df1.rename(columns={"Email address": "Email"}, inplace=True)
df2 = get_form_responses_2()

def calculate_task_completion_rate(row):
    """Calculate task completion rate based on the task status and deadline."""
    task_status = row["Task Status"]
    deadline = pd.to_datetime(row["Task Assigned Date"], format="%d/%m/%Y", errors='coerce')
    completed_on_time = pd.to_datetime(row["Today's Date"], format="%d/%m/%Y", errors='coerce') <= deadline

    if task_status in TASK_CONVERSION:
        return TASK_CONVERSION[task_status] if completed_on_time else 0
    return 0  # Default if status is unrecognized or past deadline

def process_attendance(df):
    """Calculate attendance based on 'Today's Date' column."""
    if "Today's Date" in df.columns and not pd.api.types.is_datetime64_any_dtype(df["Today's Date"]):
        df["Today's Date"] = pd.to_datetime(df["Today's Date"], format="%d/%m/%Y", errors='coerce')
    
    attendance = df.dropna(subset=["Today's Date"]).groupby("Email")["Today's Date"].nunique().to_dict()
    return attendance

def fetch_tasks(df):
    """Fetch tasks assigned to each intern."""
    tasks = defaultdict(list)
    for _, row in df.iterrows():
        if pd.notna(row.get("Assigned Task Name")) and pd.notna(row.get("Task Status")):
            tasks[row["Email"]].append((row["Assigned Task Name"], row["Task Status"]))
    return tasks

def compute_performance(df):
    """Compute task completion rate for each intern."""
    df["Task Completion Rate"] = df.apply(calculate_task_completion_rate, axis=1)
    performance = df.groupby("Email")["Task Completion Rate"].mean().round(2).fillna(0)
    return performance.to_dict()

@lru_cache(maxsize=32)
def compute_performance_cached(df_json):
    """Compute task completion rate for each intern with caching."""
    df = pd.read_json(df_json)
    df["Task Completion Rate"] = df.apply(calculate_task_completion_rate, axis=1)
    performance = df.groupby("Email")["Task Completion Rate"].mean().round(2).fillna(0)
    return performance.to_dict()

def generate_ai_insights(df):
    """Generate insights for performance analysis without using external API."""
    insights = {}
    all_tasks = fetch_tasks(df)
    all_emails = list(all_tasks.keys())
    
    for email in all_emails:
        tasks = all_tasks[email]
        total_tasks = len(tasks)
        completed_tasks = sum(1 for task, status in tasks if "Finishing" in status or "Completed" in status)
        days_present = len(df[df["Email"] == email]["Today's Date"].unique())
        days_absent = 30 - days_present
        ongoing_tasks = sum(1 for task, status in tasks if "Ongoing" in status)
        research_tasks = sum(1 for task, status in tasks if "Research" in status)
        
        completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        attendance_rate = (days_present / 30 * 100)
        
        if completion_rate >= 80 and attendance_rate >= 90:
            performance_level = "Excellent"
            recommendation = "Consider for promotion or additional responsibilities."
        elif completion_rate >= 70 and attendance_rate >= 80:
            performance_level = "Good"
            recommendation = "Performing well, but has room for improvement in task efficiency."
        elif completion_rate >= 50 and attendance_rate >= 70:
            performance_level = "Average"
            recommendation = "Needs improvement in task completion and consistency."
        else:
            performance_level = "Below Average"
            recommendation = "Requires immediate attention and performance improvement plan."
        
        insight = f"""Performance Level: {performance_level}
        
Task Analysis:
- Completed {completed_tasks} out of {total_tasks} tasks ({completion_rate:.1f}%)
- Currently has {ongoing_tasks} ongoing tasks and {research_tasks} in research phase
- Attendance rate: {attendance_rate:.1f}% ({days_present} days present)

Recommendation: {recommendation}

Key focus areas:
"""
        if completion_rate < 70:
            insight += "- Improve task completion rate by setting smaller milestones\n"
        if attendance_rate < 80:
            insight += "- Improve attendance and consistency\n"
        if ongoing_tasks > completed_tasks:
            insight += "- Work on finishing ongoing tasks before starting new ones\n"
        if research_tasks > (total_tasks / 3):
            insight += "- Move research tasks to implementation phase faster\n"
        
        if performance_level in ["Excellent", "Good"]:
            insight += "\nOverall, performing well with minor adjustments needed."
        else:
            insight += "\nNeeds structured guidance to improve performance metrics."
            
        insights[email] = insight
            
    return insights

def plot_performance_graph(email, performance, attendance, tasks):
    """Generate enhanced Plotly graphs for performance analysis."""
    task_trend = {}
    if email in tasks and tasks[email]:
        for task, status in tasks[email]:
            task_date = task.split(' - ')[1] if ' - ' in task else None
            if task_date:
                try:
                    date = pd.to_datetime(task_date)
                    status_value = TASK_CONVERSION.get(status, 0)
                    if date not in task_trend:
                        task_trend[date] = []
                    task_trend[date].append(status_value)
                except:
                    pass
    
    bar_fig = go.Figure(data=[
        go.Bar(name="Task Completion (%)", x=[email], y=[performance.get(email, 0)],
              marker_color='rgba(58, 71, 80, 0.6)', marker_line_color='rgba(8, 48, 107, 1.0)',
              marker_line_width=1.5),
        go.Bar(name="Days Present", x=[email], y=[attendance.get(email, 0)],
              marker_color='rgba(246, 78, 139, 0.6)', marker_line_color='rgba(178, 58, 84, 1.0)',
              marker_line_width=1.5)
    ])
    
    bar_fig.update_layout(
        barmode="group", 
        title=f"Performance Overview for {email}",
        xaxis_title="Employee",
        yaxis_title="Value",
        legend_title="Metrics",
        template="plotly_white"
    )

    task_counts = pd.Series([status for task, status in tasks[email]]).value_counts() if email in tasks else pd.Series()
    
    pie_fig = go.Figure(data=[go.Pie(
        labels=task_counts.index, 
        values=task_counts.values,
        hole=.3,
        marker=dict(colors=['#636EFA', '#EF553B', '#00CC96', '#AB63FA', '#FFA15A'])
    )])
    
    pie_fig.update_layout(
        title="Task Status Distribution",
        template="plotly_white"
    )

    return bar_fig.to_json(), pie_fig.to_json()

def calculate_performance_score(performance_rate, attendance_rate, task_completion_rate):
    """Calculate an overall performance score based on multiple metrics."""
    weights = {
        'performance': 0.4,  
        'attendance': 0.3,   
        'task_completion': 0.3
    }
    
    score = (
        weights['performance'] * performance_rate +
        weights['attendance'] * (attendance_rate/30 * 100) +
        weights['task_completion'] * task_completion_rate
    )
    
    return round(score, 1)

def analyze_deadline_performance(df):
    """Analyze how well employees meet deadlines."""
    if "Task Assigned Date" not in df.columns or "Today's Date" not in df.columns:
        return {}
        
    df["Task Assigned Date"] = pd.to_datetime(df["Task Assigned Date"], format="%d/%m/%Y", errors='coerce')
    df["Today's Date"] = pd.to_datetime(df["Today's Date"], format="%d/%m/%Y", errors='coerce')
    
    df["Days to Complete"] = (df["Today's Date"] - df["Task Assigned Date"]).dt.days
    
    deadline_performance = df.groupby("Email")["Days to Complete"].agg(
        ['mean', 'min', 'max', 'count']
    ).round(1).to_dict('index')
    
    return deadline_performance

def generate_behavior_insights(selected_email, df2, GROQ_API_KEY):
    """Generate behavioral insights for the selected intern using AI"""
    selected_feedback = df2[df2["Intern's Email"] == selected_email]

    if not selected_feedback.empty:
        prompt_text = f"""
You are an experienced AI HR analyst.

Evaluate the following behavioral feedback for the intern with email: {selected_email}. Your analysis should include the following sections, written in simple plain text without bold formatting or markdown:

- Ratings overview: List the average rating (out of 5) for each of these:
  - Punctuality & Attendance
  - Communication Skills
  - Task Discipline
  - Team Collaboration
  - Integrity & Ethics

- Strengths: Mention 2–3 key strengths in bullet points.

- Areas for improvement: Mention 2–3 things the intern can improve, also as bullet points.

- Suggestions for improvement: Give 2–3 practical, actionable ideas to help the intern grow.

Keep the tone professional, concise, and easy to read. Avoid using any special characters like *, **, or bullet symbols that might render as formatting. Just write plain, structured text.

Here is the intern feedback data:
{selected_feedback.to_json(orient='records')}
"""

        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "llama-3.2-3b-preview",
            "messages": [
                {"role": "system", "content": "You are a concise HR performance analyst."},
                {"role": "user", "content": prompt_text}
            ],
            "temperature": 0.5
        }

        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload
        )

        if response.status_code == 200:
            result = response.json()["choices"][0]["message"]["content"]
            
            # Generate PDF
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            pdf.multi_cell(0, 10, f"Behavioural Insights for: {selected_email}\n\n{result}")

            # Save and encode
            pdf_output_path = f"{selected_email}_insights.pdf"
            pdf.output(pdf_output_path)

            with open(pdf_output_path, "rb") as f:
                base64_pdf = base64.b64encode(f.read()).decode("utf-8")

            return result, base64_pdf
        
        else:
            return None, f"Failed to get insights from AI. Error: {response.text}"

    else:
        return None, "No behavioral feedback found for this intern."

def generate_individual_radar(intern_df):
    """Create radar chart for individual performance"""
    categories = ['Task Completion', 'Hours Worked', 'On-Time Submission', 
                 'Additional Tasks', 'File Submissions']
    
    completion = (intern_df['Task Status'] == 'Completed').mean()
    hours = intern_df['Number of hours worked'].mean() / 10
    on_time = (intern_df['Task Status'] != 'Overdue').mean()
    additional_tasks = intern_df['Additional Task done'].apply(lambda x: x != 'No').sum() / 5
    file_submissions = intern_df['File Upload (optional)'].notnull().sum() / 3
    
    values = [completion, hours, on_time, additional_tasks, file_submissions]
    
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=values,
        theta=categories,
        fill='toself',
        name='Performance'
    ))
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 1]
            )),
        showlegend=False,
        title="Individual Skill Radar"
    )
    return fig.to_json()

def plot_individual_timeline(intern_df):
    """Create timeline of task submissions with proper datetime handling"""
    required_cols = ["Timestamp", "Task Deadline", "Assigned Task Name", "Task Status"]
    if not all(col in intern_df.columns for col in required_cols):
        return None

    intern_df = intern_df.copy()
    intern_df['Timestamp'] = pd.to_datetime(intern_df['Timestamp'], errors='coerce')
    intern_df['Task Deadline'] = pd.to_datetime(intern_df['Task Deadline'], errors='coerce')

    intern_df = intern_df.dropna(subset=['Timestamp', 'Task Deadline'])

    if intern_df.empty:
        return None

    intern_df = intern_df.sort_values('Timestamp')

    fig = px.timeline(
        intern_df,
        x_start="Timestamp",
        x_end="Task Deadline",
        y="Assigned Task Name",
        color="Task Status",
        color_discrete_map={
            'Completed': '#2ecc71',
            'In Progress': '#f1c40f',
            'Overdue': '#e74c3c'
        },
        title="Task Timeline"
    )
    fig.update_yaxes(autorange="reversed")
    return fig.to_json()

def individual_performance_comparison(intern_df, team_df):
    """Bar chart comparing individual vs team averages"""
    def safe_tasks_per_day(df, label):
        if 'Timestamp' not in df.columns:
            return 0
        timestamp_count = df['Timestamp'].nunique()
        if timestamp_count == 0:
            return 0
        return df.shape[0] / timestamp_count

    for col in ['Task Status', 'Number of hours worked']:
        if col not in intern_df.columns or col not in team_df.columns:
            return None

    metrics = {
        'Task Completion Rate': [
            (intern_df['Task Status'] == 'Completed').mean(),
            (team_df['Task Status'] == 'Completed').mean()
        ],
        'Avg Hours/Day': [
            intern_df['Number of hours worked'].mean(),
            team_df['Number of hours worked'].mean()
        ],
        'Tasks/Day': [
            safe_tasks_per_day(intern_df, "individual"),
            safe_tasks_per_day(team_df, "team")
        ]
    }

    fig = go.Figure()
    for idx, (metric, values) in enumerate(metrics.items()):
        fig.add_trace(go.Bar(
            x=[metric],
            y=[values[0]],
            name='Individual',
            marker_color='#3498db',
            showlegend=(idx == 0)
        ))
        fig.add_trace(go.Bar(
            x=[metric],
            y=[values[1]],
            name='Team Average',
            marker_color='#bdc3c7',
            showlegend=(idx == 0)
        ))

    fig.update_layout(
        barmode='group',
        title="Individual vs Team Comparison",
        yaxis_title="Performance Metric",
        plot_bgcolor='white'
    )
    return fig.to_json()

def calculate_summary_metrics(df):
    total_interns = df['Email'].nunique()
    avg_hours = df['Number of hours worked'].mean()
    task_completion = (df[df['Task Status'] == 'Completed'].shape[0] / df.shape[0]) * 100
    avg_tasks = df.groupby('Email')['Assigned Task Name'].count().mean()
    return total_interns, avg_hours, task_completion, avg_tasks