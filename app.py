from flask import Flask, render_template, request, redirect, url_for, jsonify
import json
import os
from scraper import scrape_lunch_menu

app = Flask(__name__)

# File to store URLs
URLS_FILE = 'urls.json'


def load_urls():
    """Load saved URLs from file."""
    if os.path.exists(URLS_FILE):
        with open(URLS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def save_urls(urls):
    """Save URLs to file."""
    with open(URLS_FILE, 'w', encoding='utf-8') as f:
        json.dump(urls, f, ensure_ascii=False, indent=2)


@app.route('/')
def index():
    """Main dashboard showing today's lunch menus."""
    return render_template('index.html')


@app.route('/settings')
def settings():
    """Page to manage restaurant URLs."""
    urls = load_urls()
    return render_template('settings.html', urls=urls)


@app.route('/add_url', methods=['POST'])
def add_url():
    """Add a new restaurant URL."""
    name = request.form.get('name', '').strip()
    url = request.form.get('url', '').strip()

    if name and url:
        urls = load_urls()
        urls.append({'name': name, 'url': url})
        save_urls(urls)

    return redirect(url_for('settings'))


@app.route('/delete_url/<int:index>')
def delete_url(index):
    """Delete a restaurant URL."""
    urls = load_urls()
    if 0 <= index < len(urls):
        urls.pop(index)
        save_urls(urls)
    return redirect(url_for('settings'))


@app.route('/api/menus')
def get_menus():
    """API endpoint to fetch all lunch menus."""
    urls = load_urls()
    menus = []

    for item in urls:
        try:
            menu_text = scrape_lunch_menu(item['url'])
            menus.append({
                'name': item['name'],
                'url': item['url'],
                'menu': menu_text,
                'error': None
            })
        except Exception as e:
            menus.append({
                'name': item['name'],
                'url': item['url'],
                'menu': None,
                'error': str(e)
            })

    return jsonify(menus)


if __name__ == '__main__':
    app.run(debug=True, port=5000)
