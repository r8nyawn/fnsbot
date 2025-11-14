import os
from dotenv import load_dotenv

# Загружаем переменные из .env файла
load_dotenv()

class Config:
    # Telegram Bot Token от @BotFather
    TELEGRAM_TOKEN = "8530864295:AAGybOHkA7dRE76-0vgXKh4qZOWwQzt8YL4"
    
    # ID Google таблицы
    SPREADSHEET_ID = "18U-BHTqxuxsVjuJrVgSioeTrfh6YceN96mxtk3JTKY0"
    
    # API ключ от FNS
    FNS_API_KEY = "3942e7783ca52fb48973abcb8e83dc1c7082b6c2"
    
    # DaData API (пока не используем)
    DADATA_API_KEY = ""
    DADATA_SECRET = ""
    
    # Файл с ключами Google API
    GOOGLE_SHEETS_CREDENTIALS = "credentials.json"

# Тестовая функция для проверки конфигурации
def test_config():
    print("=== ПРОВЕРКА КОНФИГУРАЦИИ ===")
    config = Config()
    print(f"TELEGRAM_TOKEN: {'✅' if config.TELEGRAM_TOKEN else '❌'}")
    print(f"SPREADSHEET_ID: {'✅' if config.SPREADSHEET_ID else '❌'}")
    print(f"FNS_API_KEY: {'✅' if config.FNS_API_KEY else '❌'}")
    print(f"GOOGLE_SHEETS_CREDENTIALS: {'✅' if config.GOOGLE_SHEETS_CREDENTIALS else '❌'}")
    print("=" * 40)

if __name__ == "__main__":
    test_config()