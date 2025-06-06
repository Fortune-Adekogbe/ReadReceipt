# config.py
import os
from dotenv import load_dotenv

load_dotenv() # Load variables from .env file if it exists

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "YOUR_GOOGLE_GEMINI_API_KEY") # New line


# For Google Sheets (optional) - path to your service account JSON file
GOOGLE_SHEETS_SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SHEETS_SERVICE_ACCOUNT_FILE", "service_account.json")
GOOGLE_SHEET_ID_OR_URL = os.getenv("GOOGLE_SHEET_ID_OR_URL", None) # Optional: pre-configure a sheet

# Path for temporary files
TEMP_DIR = "temp_files"

# Ensure temp directory exists
if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)

# Basic check for essential keys
if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN":
    print("ERROR: TELEGRAM_BOT_TOKEN not set!")
    exit()

if not GOOGLE_API_KEY or GOOGLE_API_KEY == "YOUR_GOOGLE_GEMINI_API_KEY":
    print("ERROR: GOOGLE_API_KEY for Gemini not set!")