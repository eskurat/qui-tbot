import requests
from bs4 import BeautifulSoup
from telegram import Bot
import asyncio
import json
import os

# === НАСТРОЙКИ ===
BOT_TOKEN = os.environ.get('BOT_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')

URLS = [
    "https://www.qui.help/forum/find-psychologist",
    "https://www.qui.help/forum/ask-psychologist"
]

STORAGE_FILE = "posts_cache.json"

# === ФУНКЦИИ ===

def load_old_posts():
    """Загружаем список уже известных постов"""
    if os.path.exists(STORAGE_FILE):
        with open(STORAGE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_posts(posts):
    """Сохраняем список постов"""
    with open(STORAGE_FILE, 'w', encoding='utf-8') as f:
        json.dump(posts, f, ensure_ascii=False, indent=2)
def commit_cache_to_github():
    """Зберігаємо кеш в GitHub репозиторій"""
    try:
        import subprocess
        subprocess.run(['git', 'config', '--global', 'user.email', 'bot@github.com'])
        subprocess.run(['git', 'config', '--global', 'user.name', 'QUI Bot'])
        subprocess.run(['git', 'add', STORAGE_FILE])
        subprocess.run(['git', 'commit', '-m', 'Update posts cache'])
        subprocess.run(['git', 'push'])
        print("Кеш збережено в GitHub")
    except Exception as e:
        print(f"Помилка збереження кешу: {e}")
def get_posts_from_page(url):
    """Получаем список постов со страницы"""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        posts = []
        articles = soup.select('article.post-card')
        print(f"Знайдено {len(articles)} статей на {url}")
        
        for article in articles:
            # Спочатку шукаємо заголовок в .post-title
            title_elem = article.select_one('.post-title')
            
            # Якщо немає .post-title, беремо текст з .post-content
            if not title_elem:
                title_elem = article.select_one('.post-content')
            
            link_elem = article.select_one('a.post-content-wrapper')
            
            if title_elem and link_elem:
                title = title_elem.get_text(strip=True)
                # Обрізаємо заголовок до 100 символів якщо дуже довгий
                if len(title) > 100:
                    title = title[:97] + '...'
                
                link = link_elem.get('href', '')
                
                if link and not link.startswith('http'):
                    link = 'https://www.qui.help/' + link.lstrip('/')
                
                print(f"  - Знайдено пост: {title}")
                posts.append({
                    'title': title,
                    'link': link
                })
        
        return posts
    except Exception as e:
        print(f"Помилка парсінгу {url}: {e}")
        return []

async def send_notification(bot, message):
    """Отправляем уведомление в Telegram"""
    try:
        await bot.send_message(chat_id=CHAT_ID, text=message, parse_mode='HTML')
    except Exception as e:
        print(f"Помилка відправки повідомлення: {e}")

async def check_updates():
    """Основная функция проверки обновлений"""
    bot = Bot(token=BOT_TOKEN)
    old_posts = load_old_posts()
    all_current_posts = {}
    
    for url in URLS:
        print(f"Проверяю: {url}")
        posts = get_posts_from_page(url)
        
        all_current_posts[url] = [p['link'] for p in posts]
        
        old_links = old_posts.get(url, [])
        
        # Знаходимо нові пости
        new_posts = []
        for post in posts:
            if post['link'] not in old_links:
                new_posts.append(post)
        
        # Перевертаємо список щоб старі були першими
        new_posts.reverse()
        
        # Відправляємо повідомлення з різними заголовками
        for post in new_posts:
            # Визначаємо тип повідомлення за URL
            if 'find-psychologist' in url:
                emoji = "🔍"
                header = "Новий запит!"
            elif 'ask-psychologist' in url:
                emoji = "❓"
                header = "Нове питання!"
            else:
                emoji = "🆕"
                header = "Нова публікація!"
            
            message = f"{emoji} <b>{header}</b>\n\n"
            message += f"<b>{post['title']}</b>\n\n"
            message += f"🔗 {post['link']}"
            
            await send_notification(bot, message)
            print(f"Надіслано сповіщення: {post['title']}")
    
    save_posts(all_current_posts)
    commit_cache_to_github()
    print("Перевірка завершена!")

# === ЗАПУСК ===
if __name__ == "__main__":
    asyncio.run(check_updates())
