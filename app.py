from flask import Flask, render_template_string, request, jsonify
import json
import os
import sys
from scraper import scrape_lunch_menu

app = Flask(__name__)
VERSION = "1.0.7"

# Supabase setup (om miljövariabler finns)
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')
supabase_client = None

# Debug: visa om miljövariabler finns
print(f"==> SUPABASE_URL finns: {bool(SUPABASE_URL)}", flush=True)
print(f"==> SUPABASE_KEY finns: {bool(SUPABASE_KEY)}", flush=True)

if SUPABASE_URL and SUPABASE_KEY:
    try:
        from supabase import create_client
        supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("==> Supabase ansluten!", flush=True)
    except Exception as e:
        print(f"==> Kunde inte ansluta till Supabase: {e}", flush=True)
else:
    print("==> Supabase miljövariabler saknas - använder lokal fil", flush=True)

# Fallback till fil om ingen databas
DATA_FILE = 'restaurants.json'


def load_restaurants():
    """Ladda restauranger från Supabase eller lokal fil."""
    if supabase_client:
        try:
            response = supabase_client.table('restaurants').select('*').order('id').execute()
            return [{'name': r['name'], 'url': r['url'], 'enabled': r.get('enabled', True)} for r in response.data]
        except Exception as e:
            print(f"Fel vid laddning från Supabase: {e}")
            return []
    else:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []


def save_restaurants(restaurants):
    """Spara restauranger till Supabase eller lokal fil."""
    if supabase_client:
        try:
            # Rensa tabellen först
            supabase_client.table('restaurants').delete().gte('id', 0).execute()
            # Lägg till alla restauranger
            for r in restaurants:
                supabase_client.table('restaurants').insert({
                    'name': r['name'],
                    'url': r['url'],
                    'enabled': r.get('enabled', True)
                }).execute()
            print(f"Sparade {len(restaurants)} restauranger till Supabase")
        except Exception as e:
            print(f"Fel vid sparning till Supabase: {e}")
            # Fallback till fil
            with open(DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(restaurants, f, ensure_ascii=False, indent=2)
    else:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(restaurants, f, ensure_ascii=False, indent=2)


HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="sv">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Lunchmeny</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        html, body {
            height: 100%;
            overflow-x: hidden;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f5f5;
            color: #333;
            line-height: 1.6;
        }

        /* Navigation */
        nav {
            background: #2c3e50;
            color: white;
            padding: 1rem;
            position: sticky;
            top: 0;
            z-index: 100;
        }
        .nav-container {
            max-width: 1200px;
            margin: 0 auto;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .logo { font-size: 1.3rem; font-weight: bold; }
        .nav-btn {
            background: rgba(255,255,255,0.15);
            border: none;
            color: white;
            padding: 0.6rem 1rem;
            border-radius: 8px;
            cursor: pointer;
            font-size: 0.95rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        .nav-btn:hover { background: rgba(255,255,255,0.25); }
        .nav-btn:active { background: rgba(255,255,255,0.3); }

        /* Main content */
        main {
            max-width: 1200px;
            margin: 0 auto;
            padding: 1.5rem;
            padding-bottom: 100px;
        }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1.5rem;
            gap: 1rem;
        }
        h1 { font-size: 1.5rem; color: #2c3e50; }

        /* Buttons */
        .btn {
            padding: 0.75rem 1.25rem;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 1rem;
            transition: all 0.2s;
            -webkit-tap-highlight-color: transparent;
        }
        .btn-primary { background: #3498db; color: white; }
        .btn-primary:hover:not(:disabled) { background: #2980b9; }
        .btn-primary:active:not(:disabled) { background: #2472a4; transform: scale(0.98); }
        .btn-primary:disabled { background: #95a5a6; cursor: not-allowed; }
        .btn-danger {
            background: #e74c3c;
            color: white;
            padding: 0.6rem 0.8rem;
            font-size: 1.1rem;
            min-width: 44px;
            min-height: 44px;
        }
        .btn-danger:hover { background: #c0392b; }
        .btn-danger:active { background: #a93226; }

        /* Menu Cards */
        .menu-card {
            background: white;
            border-radius: 12px;
            padding: 1.25rem;
            margin-bottom: 1rem;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }
        .menu-card.error { border-left: 4px solid #e74c3c; }
        .menu-card.loading { border-left: 4px solid #f39c12; }
        .menu-card.success { border-left: 4px solid #27ae60; }
        .menu-card.disabled { opacity: 0.5; border-left: 4px solid #95a5a6; }
        .menu-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.75rem;
            padding-bottom: 0.75rem;
            border-bottom: 1px solid #eee;
            gap: 0.5rem;
        }
        .menu-header h2 { color: #2c3e50; font-size: 1.1rem; }
        .menu-header a { color: #3498db; text-decoration: none; font-size: 0.85rem; }
        .source-info {
            font-size: 0.75rem;
            color: #7f8c8d;
            margin-bottom: 0.75rem;
            padding: 0.4rem 0.6rem;
            background: #f8f9fa;
            border-radius: 6px;
        }
        .badge {
            display: inline-block;
            padding: 0.15rem 0.4rem;
            border-radius: 4px;
            font-size: 0.7rem;
            font-weight: bold;
            margin-right: 0.4rem;
        }
        .badge-pdf { background: #e74c3c; color: white; }
        .badge-html { background: #3498db; color: white; }
        .menu-content {
            white-space: pre-wrap;
            font-size: 0.9rem;
            line-height: 1.7;
            color: #444;
            max-height: 400px;
            overflow-y: auto;
        }
        .error-text { color: #e74c3c; }
        .loading-text { color: #f39c12; }
        .disabled-text { color: #95a5a6; font-style: italic; }
        .info-text {
            text-align: center;
            padding: 2.5rem 1.5rem;
            background: white;
            border-radius: 12px;
            color: #7f8c8d;
        }

        /* Sidebar Overlay */
        .sidebar-overlay {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.5);
            z-index: 200;
            opacity: 0;
            visibility: hidden;
            transition: opacity 0.3s, visibility 0.3s;
        }
        .sidebar-overlay.active {
            opacity: 1;
            visibility: visible;
        }

        /* Sidebar */
        .sidebar {
            position: fixed;
            top: 0;
            right: 0;
            width: 100%;
            max-width: 400px;
            height: 100%;
            background: white;
            z-index: 300;
            transform: translateX(100%);
            transition: transform 0.3s ease-out;
            display: flex;
            flex-direction: column;
            box-shadow: -4px 0 20px rgba(0,0,0,0.15);
        }
        .sidebar.active {
            transform: translateX(0);
        }
        .sidebar-header {
            padding: 1.25rem;
            background: #2c3e50;
            color: white;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .sidebar-header h2 {
            font-size: 1.2rem;
            font-weight: 600;
        }
        .sidebar-close {
            background: rgba(255,255,255,0.15);
            border: none;
            color: white;
            width: 40px;
            height: 40px;
            border-radius: 8px;
            font-size: 1.5rem;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .sidebar-close:hover { background: rgba(255,255,255,0.25); }

        .sidebar-content {
            flex: 1;
            overflow-y: auto;
            padding: 1.25rem;
            -webkit-overflow-scrolling: touch;
        }

        /* Add form */
        .add-section {
            background: #f8f9fa;
            border-radius: 10px;
            padding: 1rem;
            margin-bottom: 1.5rem;
        }
        .add-section h3 {
            font-size: 0.9rem;
            color: #34495e;
            margin-bottom: 0.75rem;
        }
        .form-group { margin-bottom: 0.75rem; }
        .form-group label {
            display: block;
            margin-bottom: 0.4rem;
            font-weight: 500;
            color: #34495e;
            font-size: 0.85rem;
        }
        .form-group input {
            width: 100%;
            padding: 0.75rem;
            border: 1px solid #ddd;
            border-radius: 8px;
            font-size: 1rem;
            -webkit-appearance: none;
        }
        .form-group input:focus {
            outline: none;
            border-color: #3498db;
            box-shadow: 0 0 0 3px rgba(52,152,219,0.1);
        }
        .add-btn {
            width: 100%;
            padding: 0.75rem;
            background: #27ae60;
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 1rem;
            font-weight: 500;
            cursor: pointer;
            margin-top: 0.5rem;
        }
        .add-btn:hover { background: #219a52; }
        .add-btn:active { background: #1e8449; }

        /* Restaurant list */
        .restaurant-list h3 {
            font-size: 0.9rem;
            color: #34495e;
            margin-bottom: 0.5rem;
        }
        .restaurant-list-info {
            font-size: 0.8rem;
            color: #95a5a6;
            margin-bottom: 1rem;
        }
        .restaurant-item {
            display: flex;
            align-items: center;
            padding: 0.75rem;
            background: #f8f9fa;
            border-radius: 10px;
            margin-bottom: 0.6rem;
            gap: 0.75rem;
        }
        .restaurant-item.disabled {
            opacity: 0.6;
            background: #f0f0f0;
        }
        .restaurant-checkbox {
            width: 24px;
            height: 24px;
            cursor: pointer;
            flex-shrink: 0;
        }
        .restaurant-info {
            flex: 1;
            min-width: 0;
        }
        .restaurant-name {
            font-weight: 500;
            color: #2c3e50;
            font-size: 0.95rem;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .restaurant-url {
            font-size: 0.75rem;
            color: #95a5a6;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .empty-list {
            text-align: center;
            padding: 2rem;
            color: #95a5a6;
            font-style: italic;
        }

        /* Mobile optimizations */
        @media (max-width: 768px) {
            .logo { font-size: 1.1rem; }
            h1 { font-size: 1.25rem; }
            main { padding: 1rem; }
            .header { margin-bottom: 1rem; }
            .sidebar { max-width: 100%; }
        }
    </style>
</head>
<body>
    <nav>
        <div class="nav-container">
            <div class="logo">Lunchmeny <span style="font-size:0.7rem;opacity:0.6">v{{ version }}</span></div>
            <button class="nav-btn" onclick="openSidebar()">
                <span>Restauranger</span>
            </button>
        </div>
    </nav>

    <main>
        <div class="header">
            <h1>Dagens Lunch</h1>
            <button id="refresh-btn" class="btn btn-primary" onclick="fetchAllMenus()">
                Uppdatera
            </button>
        </div>
        <div id="menus-container">
            <p class="info-text">Tryck "Uppdatera" för att hämta menyer.<br><br>
            Lägg till restauranger via knappen "Restauranger".</p>
        </div>
    </main>

    <!-- Sidebar Overlay -->
    <div class="sidebar-overlay" id="sidebar-overlay" onclick="closeSidebar()"></div>

    <!-- Sidebar -->
    <div class="sidebar" id="sidebar">
        <div class="sidebar-header">
            <h2>Restauranger</h2>
            <button class="sidebar-close" onclick="closeSidebar()">&times;</button>
        </div>
        <div class="sidebar-content">
            <div class="add-section">
                <h3>Lägg till ny</h3>
                <div class="form-group">
                    <label for="restaurant-name">Namn</label>
                    <input type="text" id="restaurant-name" placeholder="T.ex. Tildas">
                </div>
                <div class="form-group">
                    <label for="restaurant-url">Hemsida</label>
                    <input type="url" id="restaurant-url" placeholder="https://restaurang.se">
                </div>
                <button class="add-btn" onclick="addRestaurant()">+ Lägg till</button>
            </div>

            <div class="restaurant-list">
                <h3>Dina restauranger</h3>
                <p class="restaurant-list-info">Bocka ur för att dölja tillfälligt</p>
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

        function openSidebar() {
            document.getElementById('sidebar').classList.add('active');
            document.getElementById('sidebar-overlay').classList.add('active');
            document.body.style.overflow = 'hidden';
            renderSavedRestaurants();
        }

        function closeSidebar() {
            document.getElementById('sidebar').classList.remove('active');
            document.getElementById('sidebar-overlay').classList.remove('active');
            document.body.style.overflow = '';
        }

        async function renderSavedRestaurants() {
            const container = document.getElementById('saved-restaurants');
            const restaurants = await loadRestaurants();

            if (restaurants.length === 0) {
                container.innerHTML = '<p class="empty-list">Inga restauranger tillagda ännu</p>';
                return;
            }

            container.innerHTML = restaurants.map((r, i) => `
                <div class="restaurant-item ${r.enabled === false ? 'disabled' : ''}">
                    <input type="checkbox" class="restaurant-checkbox"
                           ${r.enabled !== false ? 'checked' : ''}
                           onchange="toggleRestaurant(${i}, this.checked)">
                    <div class="restaurant-info">
                        <div class="restaurant-name">${escapeHtml(r.name)}</div>
                        <div class="restaurant-url">${escapeHtml(r.url)}</div>
                    </div>
                    <button class="btn btn-danger" onclick="deleteRestaurant(${i})">🗑</button>
                </div>
            `).join('');
        }

        async function addRestaurant() {
            const nameInput = document.getElementById('restaurant-name');
            const urlInput = document.getElementById('restaurant-url');
            const name = nameInput.value.trim();
            const url = urlInput.value.trim();

            if (!name || !url) {
                alert('Fyll i både namn och URL');
                return;
            }

            await fetch('/api/restaurants', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, url, enabled: true })
            });

            nameInput.value = '';
            urlInput.value = '';
            renderSavedRestaurants();
        }

        async function toggleRestaurant(index, enabled) {
            await fetch(`/api/restaurants/${index}/toggle`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ enabled })
            });
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
                        <button class="btn btn-primary" style="margin-top:1rem" onclick="openSidebar()">
                            + Lägg till
                        </button>
                    </div>
                `;
                return;
            }

            const activeRestaurants = restaurants.filter(r => r.enabled !== false);
            const disabledRestaurants = restaurants.filter(r => r.enabled === false);

            if (activeRestaurants.length === 0) {
                container.innerHTML = `
                    <div class="info-text">
                        <p>Alla restauranger är dolda.</p>
                        <button class="btn btn-primary" style="margin-top:1rem" onclick="openSidebar()">
                            Hantera restauranger
                        </button>
                    </div>
                `;
                return;
            }

            btn.disabled = true;
            btn.textContent = 'Laddar...';

            // Loading state
            let html = activeRestaurants.map(r => `
                <div class="menu-card loading">
                    <div class="menu-header">
                        <h2>${escapeHtml(r.name)}</h2>
                    </div>
                    <div class="menu-content loading-text">Söker efter lunchmeny...</div>
                </div>
            `).join('');

            if (disabledRestaurants.length > 0) {
                html += disabledRestaurants.map(r => `
                    <div class="menu-card disabled">
                        <div class="menu-header"><h2>${escapeHtml(r.name)}</h2></div>
                        <div class="menu-content disabled-text">Dold</div>
                    </div>
                `).join('');
            }

            container.innerHTML = html;

            // Fetch menus
            const res = await fetch('/api/menus');
            const menus = await res.json();

            html = menus.map(m => `
                <div class="menu-card ${m.success ? 'success' : 'error'}">
                    <div class="menu-header">
                        <h2>${escapeHtml(m.name)}</h2>
                        <a href="${escapeHtml(m.source_url)}" target="_blank">Källa</a>
                    </div>
                    ${m.success ? `
                        <div class="source-info">
                            <span class="badge ${m.source_type === 'pdf' ? 'badge-pdf' : 'badge-html'}">
                                ${m.source_type === 'pdf' ? 'PDF' : 'Webb'}
                            </span>
                            ${escapeHtml(m.source_url)}
                        </div>
                    ` : ''}
                    <div class="menu-content ${m.error ? 'error-text' : ''}">
                        ${m.error ? 'Fel: ' + escapeHtml(m.error) : escapeHtml(m.menu)}
                    </div>
                </div>
            `).join('');

            if (disabledRestaurants.length > 0) {
                html += disabledRestaurants.map(r => `
                    <div class="menu-card disabled">
                        <div class="menu-header"><h2>${escapeHtml(r.name)}</h2></div>
                        <div class="menu-content disabled-text">Dold</div>
                    </div>
                `).join('');
            }

            container.innerHTML = html;
            btn.disabled = false;
            btn.textContent = 'Uppdatera';
        }

        // Swipe to close sidebar
        let touchStartX = 0;
        const sidebar = document.getElementById('sidebar');

        sidebar.addEventListener('touchstart', e => {
            touchStartX = e.touches[0].clientX;
        }, { passive: true });

        sidebar.addEventListener('touchend', e => {
            const touchEndX = e.changedTouches[0].clientX;
            const diff = touchEndX - touchStartX;
            if (diff > 100) closeSidebar(); // Swipe right to close
        }, { passive: true });
    </script>
</body>
</html>
'''


@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, version=VERSION)


@app.route('/api/restaurants', methods=['GET'])
def get_restaurants():
    return jsonify(load_restaurants())


@app.route('/api/restaurants', methods=['POST'])
def add_restaurant():
    data = request.get_json()
    restaurants = load_restaurants()
    restaurants.append({
        'name': data.get('name', ''),
        'url': data.get('url', ''),
        'enabled': data.get('enabled', True)
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


@app.route('/api/restaurants/<int:index>/toggle', methods=['POST'])
def toggle_restaurant(index):
    data = request.get_json()
    restaurants = load_restaurants()
    if 0 <= index < len(restaurants):
        restaurants[index]['enabled'] = data.get('enabled', True)
        save_restaurants(restaurants)
    return jsonify({'success': True})


@app.route('/api/menus', methods=['GET'])
def get_menus():
    restaurants = load_restaurants()
    results = []

    for r in restaurants:
        if r.get('enabled', True):
            result = scrape_lunch_menu(r['url'])
            result['name'] = r['name']
            results.append(result)

    return jsonify(results)


if __name__ == '__main__':
    app.run(debug=True, port=5000)
