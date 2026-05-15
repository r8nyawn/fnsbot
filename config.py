import os
from dotenv import load_dotenv
load_dotenv()
class Config:
    TELEGRAM_TOKEN = " "
    SPREADSHEET_ID = " "
    FNS_API_KEY = " "
    DADATA_API_KEY = " "
    DADATA_SECRET = " "
    GOOGLE_SHEETS_CREDENTIALS = "credentials.json"
if __name__ == "__main__":
    test_config()
