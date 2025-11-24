import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
SQLALCHEMY_DATABASE_URI = f'sqlite:///{os.path.join(BASE_DIR, "casaflow.db")}'
SQLALCHEMY_TRACK_MODIFICATIONS = False
SECRET_KEY = 'a-very-secret-key-that-should-be-changed'
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
# --- Email Configuration (Placeholder) ---
SMTP_SERVER = 'smtp.example.com'
SMTP_PORT = 587
SMTP_USERNAME = 'your_email@example.com'
SMTP_PASSWORD = 'your_email_password'
SENDER_EMAIL = 'noreply@casaflow.com'
