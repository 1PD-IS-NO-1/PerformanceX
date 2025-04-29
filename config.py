import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Flask Config
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key')
    
    # Google Sheets
    CREDENTIALS_FILE = os.getenv('GOOGLE_CREDENTIALS_FILE', 'credentials.json')
    SPREADSHEET_URL = os.getenv('SPREADSHEET_URL')
    
    # Groq API
    GROQ_API_KEY = os.getenv('GROQ_API_KEY')
    
    # Performance Settings
    TASK_CONVERSION_RATES = {
        "Completed": 100,
        "Ongoing": 60,
        "Research": 30,
        "Finishing": 90
    }
    
    @staticmethod
    def init_app(app):
        pass