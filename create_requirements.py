# Сохраните этот код в файл create_requirements.py и запустите его

requirements = """
python-telegram-bot==20.7
gspread==5.12
google-auth==2.23.0
pandas==2.1.0
requests==2.31.0
python-dotenv==1.0.0
"""

with open('requirements.txt', 'w', encoding='utf-8') as f:
    f.write(requirements.strip())

print("✅ Файл requirements.txt создан!")