import logging
import requests
import gspread
import time
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from config import Config


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

class FNSAPI:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api-fns.ru/api"
        self.timeout = 15
        self.max_retries = 2
    
    def is_inn(self, query):
        return query.isdigit() and (len(query) == 10 or len(query) == 12)
    
    def search_companies(self, search_query):
        if not self.api_key:
            return {"error": "API ключ не настроен"}
        
        if self.is_inn(search_query):
            print(f"Запрос распознан как ИНН: {search_query}")
            return self.search_by_inn(search_query)
        else:
            print(f"Запрос распознан как название: {search_query}")
            return self.search_by_name(search_query)
    
    def search_by_inn(self, inn):
        for attempt in range(self.max_retries + 1):
            try:
                url = f"{self.base_url}/egr"
                params = {
                    'req': inn,
                    'key': self.api_key
                }
                
                print(f"Попытка {attempt + 1}: поиск по ИНН: {inn}")
                
                response = requests.get(url, params=params, timeout=self.timeout)
                print(f"Статус: {response.status_code}")
                
                if response.status_code != 200:
                    return {"error": f"HTTP ошибка: {response.status_code}"}
                
                data = response.json()
                print(f"Ключи в ответе: {list(data.keys())}")
                
                if 'items' in data and data['items']:
                    return {
                        'type': 'inn',
                        'items': data['items']
                    }
                else:
                    return {"error": "Компания с таким ИНН не найдена"}
                    
            except requests.exceptions.Timeout:
                print(f" Таймаут на попытке {attempt + 1}")
                if attempt < self.max_retries:
                    print("Повторная попытка...")
                    time.sleep(2)
                else:
                    return {"error": "Превышено время ожидания ответа от API ФНС"}
                    
            except Exception as e:
                print(f"Ошибка на попытке {attempt + 1}: {e}")
                return {"error": f"Ошибка соединения: {str(e)}"}
        
        return {"error": "Не удалось получить данные после нескольких попыток"}
    
    def search_by_name(self, company_name):
        for attempt in range(self.max_retries + 1):
            try:
                url = f"{self.base_url}/egr"
                params = {
                    'req': company_name,
                    'key': self.api_key
                }
                
                print(f"Попытка {attempt + 1}: поиск по названию: {company_name}")
                
                response = requests.get(url, params=params, timeout=self.timeout)
                print(f"Статус: {response.status_code}")
                
                if response.status_code != 200:
                    return {"error": f"HTTP ошибка: {response.status_code}"}
                
                data = response.json()
                print(f"Найдено результатов: {len(data.get('items', []))}")
                
                if 'items' in data and data['items']:
                    # Улучшенная фильтрация результатов
                    filtered_items = self.filter_companies_by_name(data['items'], company_name)
                    
                    print(f"После фильтрации: {len(filtered_items)} результатов")
                    
                    if filtered_items:
                        return {
                            'type': 'name',
                            'items': filtered_items,
                            'original_count': len(data['items']),
                            'filtered_count': len(filtered_items)
                        }
                    else:
                        return {"error": f"Точные совпадения с названием '{company_name}' не найдены"}
                else:
                    return {"error": f"Компании с названием '{company_name}' не найдены"}
                    
            except requests.exceptions.Timeout:
                print(f"Таймаут на попытке {attempt + 1}")
                if attempt < self.max_retries:
                    print("Повторная попытка...")
                    time.sleep(2)
                else:
                    return {"error": "Превышено время ожидания ответа от API ФНС"}
                    
            except Exception as e:
                print(f"Ошибка на попытке {attempt + 1}: {e}")
                return {"error": f"Ошибка соединения: {str(e)}"}
        
        return {"error": "Не удалось получить данные после нескольких попыток"}
    
    def normalize_company_name(self, name):
        if not name:
            return ""
        
        normalized = name.lower()

        for char in ['"', "'", ',', ';', ':', '!', '?', '«', '»']:
            normalized = normalized.replace(char, '')

        normalized = ' '.join(normalized.split())
        
        return normalized.strip()
    
    def filter_companies_by_name(self, companies, search_name):
        search_normalized = self.normalize_company_name(search_name)
        filtered = []
        
        print(f"Фильтрация по названию: '{search_name}' -> '{search_normalized}'")
        
        for i, company in enumerate(companies):
            company_name = self.get_company_name(company)
            company_normalized = self.normalize_company_name(company_name)
            
            if not company_normalized:
                continue
            
            relevance = self.calculate_relevance(company_normalized, search_normalized)
            
            if relevance > 0:
                company['_relevance'] = relevance
                company['_normalized_name'] = company_normalized
                filtered.append(company)
                
                if i < 5: 
                    print(f"   {i+1}. '{company_normalized}' -> релевантность: {relevance}")
        
        filtered.sort(key=lambda x: x.get('_relevance', 0), reverse=True)
        
        return filtered
    
    def calculate_relevance(self, company_name, search_term):
        if not company_name or not search_term:
            return 0
        

        if search_term == company_name:
            return 100
        
        if company_name.startswith(search_term):
            return 90
        
        if search_term in company_name:
            return 80
        
        search_words = search_term.split()
        company_words = company_name.split()
        
        if search_words:
            words_found = sum(1 for word in search_words if word in company_name)
            if words_found == len(search_words):
                return 70
            elif words_found > 0:
                return words_found * 10

        for word in search_words:
            if word in company_name and len(word) > 3:
                return 30
        
        return 0
    
    def get_company_name(self, company_data):
        if company_data.get('ЮЛ'):
            return (company_data['ЮЛ'].get('НаимСокрЮЛ') or 
                   company_data['ЮЛ'].get('НаимПолнЮЛ'))
        elif company_data.get('ИП'):
            ip = company_data['ИП']
            return f"{ip['ФИО']['Фамилия']} {ip['ФИО']['Имя']} {ip['ФИО'].get('Отчество', '')}"
        else:
            return company_data.get('НаимСокрЮЛ') or company_data.get('НаимПолнЮЛ')
    
    def get_company_by_inn(self, inn):
        if not self.api_key:
            return {"error": "API ключ не настроен"}
        
        for attempt in range(self.max_retries + 1):
            try:
                url = f"{self.base_url}/egr"
                params = {
                    'req': inn,
                    'key': self.api_key
                }
                
                print(f"Попытка {attempt + 1}: запрос данных по ИНН: {inn}")
                
                response = requests.get(url, params=params, timeout=self.timeout)
                print(f"Статус: {response.status_code}")
                
                if response.status_code != 200:
                    return {"error": f"HTTP ошибка: {response.status_code}"}
                
                data = response.json()
                
                if data.get('items') and len(data['items']) > 0:
                    return self.parse_company_data(data['items'][0])
                else:
                    return {"error": "Компания не найдена"}
                    
            except requests.exceptions.Timeout:
                print(f"Таймаут на попытке {attempt + 1}")
                if attempt < self.max_retries:
                    print("🔄 Повторная попытка...")
                    time.sleep(2)
                else:
                    return {"error": "Превышено время ожидания ответа от API ФНС"}
                    
            except Exception as e:
                print(f"Ошибка на попытке {attempt + 1}: {e}")
                return {"error": f"Ошибка соединения: {str(e)}"}
        
        return {"error": "Не удалось получить данные после нескольких попыток"}
    
    def parse_address(self, address_data):
        if isinstance(address_data, str):
            return address_data
        
        if isinstance(address_data, dict):
            if 'АдресПолн' in address_data:
                return address_data['АдресПолн']
            
            parts = []
            
            if 'Регион' in address_data and isinstance(address_data['Регион'], dict):
                region = address_data['Регион'].get('Наим', '')
                if region:
                    parts.append(region)
            
            if 'Город' in address_data and isinstance(address_data['Город'], dict):
                city = address_data['Город'].get('Наим', '')
                if city:
                    parts.append(f"г. {city}")
            
            if 'Улица' in address_data and isinstance(address_data['Улица'], dict):
                street = address_data['Улица'].get('Наим', '')
                if street:
                    parts.append(f"ул. {street}")
            
            if 'Дом' in address_data:
                house = address_data['Дом']
                if house:
                    parts.append(f"д. {house}")
            
            return ", ".join(parts) if parts else "Адрес не указан"
        
        return "Адрес не указан"
    
    def parse_company_data(self, company_data):
        result = {
            'name': 'Нет названия',
            'inn': '',
            'ogrn': '',
            'registration_date': '',
            'address': '',
            'okved': '',
            'status': '',
            'full_name': '',
            'kpp': ''
        }
        
        print(f"Парсим данные компании. Ключи: {list(company_data.keys())}")
        
        if company_data.get('ЮЛ'):
            ul = company_data['ЮЛ']
            
            address = "Адрес не указан"
            if 'Адрес' in ul:
                address = self.parse_address(ul['Адрес'])
            elif 'АдресПолн' in ul:
                address = ul['АдресПолн']
            
            result.update({
                'name': ul.get('НаимСокрЮЛ') or ul.get('НаимПолнЮЛ') or 'Нет названия',
                'full_name': ul.get('НаимПолнЮЛ') or '',
                'inn': company_data.get('ИНН', ''),
                'ogrn': company_data.get('ОГРН', ''),
                'kpp': company_data.get('КПП', ''),
                'registration_date': ul.get('ДатаРег', ''),
                'address': address,
                'okved': ul.get('ОКВЭД', ''),
                'status': ul.get('Статус', 'Действующая')
            })
        elif company_data.get('ИП'):
            ip = company_data['ИП']
            
            address = "Адрес не указан"
            if 'Адрес' in ip:
                address = self.parse_address(ip['Адрес'])
            elif 'АдресПолн' in ip:
                address = ip['АдресПолн']
            
            result.update({
                'name': f"{ip['ФИО']['Фамилия']} {ip['ФИО']['Имя']} {ip['ФИО'].get('Отчество', '')}",
                'full_name': f"ИП {ip['ФИО']['Фамилия']} {ip['ФИО']['Имя']} {ip['ФИО'].get('Отчество', '')}",
                'inn': company_data.get('ИНН', ''),
                'ogrn': company_data.get('ОГРН', ''),
                'registration_date': ip.get('ДатаРег', ''),
                'address': address,
                'okved': ip.get('ОКВЭД', ''),
                'status': ip.get('Статус', 'Действующий')
            })
        else:
            address = "Адрес не указан"
            if 'Адрес' in company_data:
                address = self.parse_address(company_data['Адрес'])
            elif 'АдресПолн' in company_data:
                address = company_data['АдресПолn']
            
            result.update({
                'name': company_data.get('НаимСокрЮЛ') or company_data.get('НаимПолнЮЛ') or 'Нет названия',
                'full_name': company_data.get('НаимПолнЮЛ') or '',
                'inn': company_data.get('ИНН', ''),
                'ogrn': company_data.get('ОГРН', ''),
                'kpp': company_data.get('КПП', ''),
                'registration_date': company_data.get('ДатаРег', ''),
                'address': address,
                'status': company_data.get('Статус', 'Действующая')
            })
        
        if result['address']:
            result['address'] = result['address'].replace('\n', ' ').replace('\t', ' ').strip()
        
        return result

class GoogleSheetsManager:
    def __init__(self, config):
        self.config = config
        self.gc = gspread.service_account(filename=config.GOOGLE_SHEETS_CREDENTIALS)
        self.sheet = self.gc.open_by_key(config.SPREADSHEET_ID).sheet1
        
    def add_company(self, company_data):
        """Добавить компанию в таблицу"""
        try:
            clean_name = str(company_data.get('name', ''))[:100]
            clean_inn = str(company_data.get('inn', ''))
            clean_ogrn = str(company_data.get('ogrn', ''))
            clean_date = str(company_data.get('registration_date', ''))
            clean_address = str(company_data.get('address', ''))[:200]
            clean_okved = str(company_data.get('okved', ''))
            
            row_data = [
                clean_name,
                clean_inn,
                clean_ogrn,
                clean_date,
                clean_address,
                clean_okved
            ]
            
            print(f"Добавляем в таблицу: {clean_name}")
            self.sheet.append_row(row_data)
            return True
            
        except Exception as e:
            print(f"Ошибка добавления в таблицу: {e}")
            return False

class OOOBot:
    def __init__(self, config):
        self.config = config
        self.fns_api = FNSAPI(config.FNS_API_KEY)
        self.sheets_manager = GoogleSheetsManager(config)
        self.application = Application.builder().token(config.TELEGRAM_TOKEN).build()
        self.setup_handlers()
    
    def setup_handlers(self):
        """Настройка обработчиков команд"""
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("search", self.search_command))
        self.application.add_handler(CommandHandler("inn", self.inn_command))
        self.application.add_handler(CommandHandler("save", self.save_command))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        welcome_text = """
👋 <b>Добро пожаловать в бот поиска ООО</b>

🔍 <b>Поиск по ИНН и названию</b>

📋 <b>Доступные команды:</b>
/search [название/ИНН] - Найти компании
/inn [ИНН] - Подробная информация по ИНН
/save [ИНН] - Сохранить компанию в базу
/help - Помощь

💡 <b>Примеры поиска:</b>
По ИНН: 7707083893
По названию(оно не работает)0)): Сбербанк, Газпром, Яндекс
Любой текст(тоже не работает блять): просто введите название
        """
        await update.message.reply_html(welcome_text)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help"""
        help_text = """
❓ <b>Помощь по использованию бота</b>

🔍 <b>Умный поиск компаний:</b>
• Введите ИНН (10 или 12 цифр) - поиск по ИНН
• Введите название компании - поиск по названию
• /search [запрос] - принудительный поиск
• /inn [ИНН] - только по ИНН

📊 <b>Примеры запросов:</b>
• 7707083893 - ИНН Сбербанка
• сбербанк - поиск по названию
• газпром - поиск по названию  
• 7736207543 - ИНН Яндекса
• яндекс - поиск по названию

💾 <b>Сохранение данных:</b>
• /save [ИНН] - сохранить компанию в Google таблицу
• Данные сохраняются автоматически после поиска(и да, они реально там есть)
        """
        await update.message.reply_html(help_text)
    
    async def search_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Поиск компаний в ФНС"""
        if not context.args:
            await update.message.reply_html("Укажите поисковый запрос: /search [название или ИНН]")
            return
        
        search_query = " ".join(context.args)
        await self.process_search(update, search_query)
    
    async def inn_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Получение информации по ИНН"""
        if not context.args:
            await update.message.reply_html("Укажите ИНН: /inn [номер ИНН]")
            return
        
        inn = context.args[0]
        await update.message.reply_text(f"Запрашиваем информацию по ИНН: {inn}...")
        
        company_data = self.fns_api.get_company_by_inn(inn)
        
        if 'error' in company_data:
            await update.message.reply_html(f"Ошибка: {company_data['error']}")
        else:
            response = self.format_company_details(company_data)
            await update.message.reply_html(response)
    
    async def save_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Сохранить компанию в Google Sheets"""
        if not context.args:
            await update.message.reply_html("Укажите ИНН: /save [номер ИНН]")
            return
        
        inn = context.args[0]
        await update.message.reply_text(f"Сохраняем компанию с ИНН: {inn}...")
        
        company_data = self.fns_api.get_company_by_inn(inn)
        
        if 'error' in company_data:
            await update.message.reply_html(f"Ошибка: {company_data['error']}")
        else:
            if self.sheets_manager.add_company(company_data):
                await update.message.reply_html(
                    f"✅ Компания сохранена в базу!\n"
                    f"🏢 {company_data['name']}\n"
                    f"📋 ИНН: {company_data['inn']}"
                )
            else:
                await update.message.reply_html("Ошибка при сохранении в базу")
    
    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка обычного текста - умный поиск"""
        search_query = update.message.text
        await self.process_search(update, search_query)
    
    async def process_search(self, update, search_query):
        """Обработка поискового запроса"""
        await update.message.reply_text(f"🔍 Обрабатываю запрос: {search_query}...")
        
        result = self.fns_api.search_companies(search_query)
        
        if 'error' in result:
            await update.message.reply_html(f"Ошибка: {result['error']}")
        elif result.get('items'):
            companies = result['items']

            if result.get('type') == 'name':
                if result.get('filtered_count', 0) < result.get('original_count', 0):
                    await update.message.reply_text(
                        f"📊 Найдено {result['filtered_count']} релевантных результатов из {result['original_count']} найденных компаний"
                    )
            
            response = self.format_search_results(companies, search_query, result.get('type'))
            await update.message.reply_html(response)
        else:
            await update.message.reply_html("Компании не найдены")
    
    def format_search_results(self, companies, search_query, search_type=None):
        """Форматирование результатов поиска"""
        if search_type == 'inn' and companies:
            company_data = self.fns_api.parse_company_data(companies[0])
            return self.format_company_details(company_data)
        
        response = f"🔍 <b>Результаты поиска</b>\n"
        if search_type:
            response += f"Тип: {'по ИНН' if search_type == 'inn' else 'по названию'}\n"
        response += f"Запрос: \"{search_query}\"\n"
        response += f"Найдено компаний: {len(companies)}\n\n"
        
        for i, company in enumerate(companies[:10], 1):  # ограничение 10 результатами
            name = self.fns_api.get_company_name(company) or "Нет названия"
            inn = company.get('ИНН', '')
            status = "Нет статуса"
            
            if company.get('ЮЛ'):
                status = company['ЮЛ'].get('Статус', 'Неизвестно')
            elif company.get('ИП'):
                status = company['ИП'].get('Статус', 'Неизвестно')

            relevance = company.get('_relevance', 0)
            relevance_indicator = "🎯" if relevance >= 80 else "✅" if relevance >= 50 else "🔍"
            
            response += f"{relevance_indicator} <b>{i}. {name}</b>\n"
            response += f"   📋 ИНН: {inn}\n"
            response += f"   📊 Статус: {status}\n"
            response += f"   🔍 Подробнее: /inn {inn}\n"
            response += f"   💾 Сохранить: /save {inn}\n"
            response += "   ───────────────────\n"
        
        if len(companies) > 10:
            response += f"\n📄 Показано 10 из {len(companies)} результатов"
        
        response += "\n💡 <i>Используйте /inn [ИНН] для подробной информации</i>"
        
        return response
    
    def format_company_details(self, company):
        """Форматирование детальной информации о компании"""
        response = f"🏢 <b>{company['name']}</b>\n\n"
        
        response += "📊 <b>Реквизиты:</b>\n"
        response += f"├ ИНН: {company['inn']}\n"
        if company.get('kpp'):
            response += f"├ КПП: {company['kpp']}\n"
        response += f"├ ОГРН: {company['ogrn']}\n"
        response += f"└ Статус: {company['status']}\n\n"
        
        if company.get('registration_date'):
            response += "📅 <b>Информация:</b>\n"
            response += f"├ Дата регистрации: {company['registration_date']}\n"
            if company.get('address'):
                response += f"├ Адрес: {company['address']}\n"
            if company.get('okved'):
                response += f"└ ОКВЭД: {company['okved']}\n\n"
        
        if company.get('full_name') and company['full_name'] != company['name']:
            response += f"📄 <b>Полное наименование:</b>\n{company['full_name']}\n\n"
        
        response += f"💾 <i>Сохранить в базу: /save {company['inn']}</i>"
        
        return response
    
    def run(self):
        """Запуск бота"""
        print("Запускаемся...")
        print(f"SPREADSHEET_ID: {self.config.SPREADSHEET_ID}")
        print(f"FNS_API_KEY: {'✅' if self.config.FNS_API_KEY else '❌'}")
        self.application.run_polling()

def main():
    config = Config()
    bot = OOOBot(config)
    bot.run()

if __name__ == "__main__":
    main()
