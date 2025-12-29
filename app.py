from flask import Flask, render_template_string, request, jsonify
import json
import os
from scraper import scrape_lunch_menu

app = Flask(__name__)

# Fil för att spara restauranger
DATA_FILE = 'restaurants.json'


def load_restaurants():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def save_restaurants(restaurants):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(restaurants, f, ensure_ascii=False, indent=2)


HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="sv">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Lunchmeny</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f5f5;
            color: #333;
            line-height: 1.6;
        }
        nav {
            background: #2c3e50;
            color: white;
            padding: 1rem;
        }
        .nav-container {
            max-width: 1200px;
            margin: 0 auto;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .logo { font-size: 1.5rem; font-weight: bold; }
        .nav-btn {
            background: rgba(255,255,255,0.1);
            border: 1px solid rgba(255,255,255,0.3);
            color: white;
            padding: 0.5rem 1rem;
            border-radius: 6px;
            cursor: pointer;
        }
        .nav-btn:hover { background: rgba(255,255,255,0.2); }
        main {
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
        }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 2rem;
            flex-wrap: wrap;
            gap: 1rem;
        }
        h1 { font-size: 2rem; color: #2c3e50; }
        .btn {
            padding: 0.75rem 1.5rem;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 1rem;
            transition: all 0.2s;
        }
        .btn-primary { background: #3498db; color: white; }
        .btn-primary:hover:not(:disabled) { background: #2980b9; }
        .btn-primary:disabled { background: #95a5a6; cursor: not-allowed; }
        .btn-danger { background: #e74c3c; color: white; padding: 0.5rem 1rem; font-size: 0.85rem; }
        .btn-danger:hover { background: #c0392b; }

        .menu-card {
            background: white;
            border-radius: 8px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .menu-card.error { border-left: 4px solid #e74c3c; }
        .menu-card.loading { border-left: 4px solid #f39c12; }
        .menu-card.success { border-left: 4px solid #27ae60; }
        .menu-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid #eee;
            flex-wrap: wrap;
            gap: 0.5rem;
        }
        .menu-header h2 { color: #2c3e50; font-size: 1.25rem; }
        .menu-header a { color: #3498db; text-decoration: none; font-size: 0.9rem; }
        .menu-header a:hover { text-decoration: underline; }
        .source-info {
            font-size: 0.8rem;
            color: #7f8c8d;
            margin-bottom: 1rem;
            padding: 0.5rem;
            background: #f8f9fa;
            border-radius: 4px;
        }
        .source-info .badge {
            display: inline-block;
            padding: 0.2rem 0.5rem;
            border-radius: 3px;
            font-size: 0.75rem;
            font-weight: bold;
            margin-right: 0.5rem;
        }
        .badge-pdf { background: #e74c3c; color: white; }
        .badge-html { background: #3498db; color: white; }
        .menu-content {
            white-space: pre-wrap;
            font-size: 0.95rem;
            line-height: 1.8;
            color: #444;
            max-height: 500px;
            overflow-y: auto;
        }
        .error-text { color: #e74c3c; }
        .loading-text { color: #f39c12; }
        .info-text {
            text-align: center;
            padding: 3rem;
            background: white;
            border-radius: 8px;
            color: #7f8c8d;
        }

        /* Modal */
        .modal-overlay {
            display: none;
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.5);
            z-index: 1000;
            justify-content: center;
            align-items: center;
        }
        .modal-overlay.active { display: flex; }
        .modal {
            background: white;
            padding: 2rem;
            border-radius: 8px;
            width: 90%;
            max-width: 500px;
            max-height: 80vh;
            overflow-y: auto;
        }
        .modal h2 { margin-bottom: 1.5rem; color: #2c3e50; }
        .form-group { margin-bottom: 1rem; }
        .form-group label {
            display: block;
            margin-bottom: 0.5rem;
            font-weight: 500;
            color: #34495e;
        }
        .form-group input {
            width: 100%;
            padding: 0.75rem;
            border: 1px solid #ddd;
            border-radius: 6px;
            font-size: 1rem;
        }
        .form-group input:focus { outline: none; border-color: #3498db; }
        .modal-buttons { display: flex; gap: 1rem; margin-top: 1.5rem; }
        .url-list { margin-top: 2rem; border-top: 1px solid #eee; padding-top: 1.5rem; }
        .url-list h3 { margin-bottom: 1rem; color: #34495e; }
        .url-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0.75rem;
            background: #f8f9fa;
            border-radius: 6px;
            margin-bottom: 0.5rem;
        }
        .url-item-info { flex: 1; overflow: hidden; }
        .url-item-name { font-weight: 500; color: #2c3e50; }
        .url-item-url {
            font-size: 0.8rem;
            color: #7f8c8d;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        @media (max-width: 768px) {
            .header { flex-direction: column; text-align: center; }
            .nav-container { flex-direction: column; gap: 1rem; }
        }
    </style>
</head>
<body>
    <nav>
        <div class="nav-container">
            <div class="logo">🍽️ Lunchmeny</div>
            <button class="nav-btn" onclick="openSettings()">⚙️ Inställningar</button>
        </div>
    </nav>

    <main>
        <div class="header">
            <h1>Dagens Lunchmenyer</h1>
            <button id="refresh-btn" class="btn btn-primary" onclick="fetchAllMenus()">
                🔄 Uppdatera
            </button>
        </div>
        <div id="menus-container">
            <p class="info-text">Klicka på "Uppdatera" för att hämta dagens menyer.<br><br>
            Lägg till restauranger via ⚙️ Inställningar.</p>
        </div>
    </main>

    <!-- Settings Modal -->
    <div class="modal-overlay" id="settings-modal">
        <div class="modal">
            <h2>Lägg till restaurang</h2>
            <div class="form-group">
                <label for="restaurant-name">Restaurangnamn</label>
                <input type="text" id="restaurant-name" placeholder="T.ex. Tildas Restaurang">
            </div>
            <div class="form-group">
                <label for="restaurant-url">URL (huvudsida eller lunchmeny)</label>
                <input type="url" id="restaurant-url" placeholder="https://example.com">
            </div>
            <div class="modal-buttons">
                <button class="btn btn-primary" onclick="addRestaurant()">Lägg till</button>
                <button class="btn" style="background:#eee" onclick="closeSettings()">Stäng</button>
            </div>
            <div class="url-list">
                <h3>Sparade restauranger</h3>
                <div id="saved-restaurants"></div>
            </div>
        </div>
    </div>

    <script>
        function escapeHtml(text) {
            if (!text) return '';
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        async function loadRestaurants() {
            const res = await fetch('/api/restaurants');
            return await res.json();
        }

        function openSettings() {
            document.getElementById('settings-modal').classList.add('active');
            renderSavedRestaurants();
        }

        function closeSettings() {
            document.getElementById('settings-modal').classList.remove('active');
        }

        async function renderSavedRestaurants() {
            const container = document.getElementById('saved-restaurants');
            const restaurants = await loadRestaurants();

            if (restaurants.length === 0) {
                container.innerHTML = '<p style="color:#95a5a6;font-style:italic">Inga restauranger tillagda.</p>';
                return;
            }

            container.innerHTML = restaurants.map((r, i) => `
                <div class="url-item">
                    <div class="url-item-info">
                        <div class="url-item-name">${escapeHtml(r.name)}</div>
                        <div class="url-item-url">${escapeHtml(r.url)}</div>
                    </div>
                    <button class="btn btn-danger" onclick="deleteRestaurant(${i})">Ta bort</button>
                </div>
            `).join('');
        }

        async function addRestaurant() {
            const name = document.getElementById('restaurant-name').value.trim();
            const url = document.getElementById('restaurant-url').value.trim();

            if (!name || !url) {
                alert('Fyll i både namn och URL');
                return;
            }

            await fetch('/api/restaurants', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, url })
            });

            document.getElementById('restaurant-name').value = '';
            document.getElementById('restaurant-url').value = '';
            renderSavedRestaurants();
        }

        async function deleteRestaurant(index) {
            if (!confirm('Ta bort denna restaurang?')) return;
            await fetch(`/api/restaurants/${index}`, { method: 'DELETE' });
            renderSavedRestaurants();
        }

        async function fetchAllMenus() {
            const btn = document.getElementById('refresh-btn');
            const container = document.getElementById('menus-container');
            const restaurants = await loadRestaurants();

            if (restaurants.length === 0) {
                container.innerHTML = `
                    <div class="info-text">
                        <p>Inga restauranger tillagda ännu.</p>
                        <button class="btn btn-primary" style="margin-top:1rem" onclick="openSettings()">
                            Lägg till restauranger
                        </button>
                    </div>
                `;
                return;
            }

            btn.disabled = true;
            btn.textContent = '⏳ Laddar...';

            // Visa loading state
            container.innerHTML = restaurants.map(r => `
                <div class="menu-card loading">
                    <div class="menu-header">
                        <h2>${escapeHtml(r.name)}</h2>
                    </div>
                    <div class="menu-content loading-text">🔍 Söker efter lunchmeny...</div>
                </div>
            `).join('');

            // Hämta menyer
            const res = await fetch('/api/menus');
            const menus = await res.json();

            container.innerHTML = menus.map(m => `
                <div class="menu-card ${m.success ? 'success' : 'error'}">
                    <div class="menu-header">
                        <h2>${escapeHtml(m.name)}</h2>
                        <a href="${escapeHtml(m.source_url)}" target="_blank">Öppna källa →</a>
                    </div>
                    ${m.success ? `
                        <div class="source-info">
                            <span class="badge ${m.source_type === 'pdf' ? 'badge-pdf' : 'badge-html'}">
                                ${m.source_type === 'pdf' ? '📄 PDF' : '🌐 HTML'}
                            </span>
                            Hämtad från: ${escapeHtml(m.source_url)}
                        </div>
                    ` : ''}
                    <div class="menu-content ${m.error ? 'error-text' : ''}">
                        ${m.error ? 'Fel: ' + escapeHtml(m.error) : escapeHtml(m.menu)}
                    </div>
                </div>
            `).join('');

            btn.disabled = false;
            btn.textContent = '🔄 Uppdatera';
        }

        document.getElementById('settings-modal').addEventListener('click', function(e) {
            if (e.target === this) closeSettings();
        });
    </script>
</body>
</html>
'''


@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route('/api/restaurants', methods=['GET'])
def get_restaurants():
    return jsonify(load_restaurants())


@app.route('/api/restaurants', methods=['POST'])
def add_restaurant():
    data = request.get_json()
    restaurants = load_restaurants()
    restaurants.append({
        'name': data.get('name', ''),
        'url': data.get('url', '')
    })
    save_restaurants(restaurants)
    return jsonify({'success': True})


@app.route('/api/restaurants/<int:index>', methods=['DELETE'])
def delete_restaurant(index):
    restaurants = load_restaurants()
    if 0 <= index < len(restaurants):
        restaurants.pop(index)
        save_restaurants(restaurants)
    return jsonify({'success': True})


@app.route('/api/menus', methods=['GET'])
def get_menus():
    restaurants = load_restaurants()
    results = []

    for r in restaurants:
        result = scrape_lunch_menu(r['url'])
        result['name'] = r['name']
        results.append(result)

    return jsonify(results)


if __name__ == '__main__':
    app.run(debug=True, port=5000)
