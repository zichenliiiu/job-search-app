import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY')
DATABASE_URL = os.getenv('DATABASE_URL')
RECIPIENT_EMAIL = os.getenv('RECIPIENT_EMAIL')
GMAIL_APP_PASSWORD = os.getenv('GMAIL_APP_PASSWORD')

GMAIL_CREDENTIALS_PATH = os.getenv('GMAIL_CREDENTIALS_PATH', 'config/credentials.json')
GMAIL_TOKEN_PATH = os.getenv('GMAIL_TOKEN_PATH', 'config/token.json')
LINKEDIN_LI_AT = os.getenv('LINKEDIN_LI_AT')
LINKEDIN_JSESSIONID = os.getenv('LINKEDIN_JSESSIONID')

# User login (Google OAuth)
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
FLASK_SECRET_KEY = os.getenv('FLASK_SECRET_KEY')
APP_BASE_URL = os.getenv('APP_BASE_URL', 'http://localhost:5173')
