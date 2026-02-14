# config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'pregbot-secret-key-2024')
    SQLALCHEMY_DATABASE_URI = 'mysql+mysqlconnector://pregbot:pregbot123@localhost/pregbot_db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = 'static/uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size