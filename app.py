from flask import Flask, render_template, jsonify, request, session, redirect, url_for
from config import DISCORD_CLIENT_ID, DISCORD_CLIENT_SECRET, SECRET_KEY, SUPABASE_URL, SUPABASE_KEY
import requests
from functools import wraps
import os

app = Flask(__name__)
app.secret_key = SECRET_KEY

# Discord OAuth
DISCORD_OAUTH_URL = "https://discord.com/api/oauth2/authorize"
DISCORD_TOKEN_URL = "https://discord.com/api/oauth2/token"
DISCORD_API_URL = "https://discord.com/api"

# En mémoire (remplacer par Supabase)
services_db = {}

def require_login(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/login')
def login():
    return redirect(
        f"{DISCORD_OAUTH_URL}?client_id={DISCORD_CLIENT_ID}&redirect_uri=http://localhost:5000/callback&response_type=code&scope=identify%20email"
    )

@app.route('/callback')
def callback():
    code = request.args.get('code')
    if not code:
        return redirect(url_for('index'))
    
    try:
        # Échanger le code pour un token
        resp = requests.post(DISCORD_TOKEN_URL, data={
            'client_id': DISCORD_CLIENT_ID,
            'client_secret': DISCORD_CLIENT_SECRET,
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': 'http://localhost:5000/callback'
        })
        
        token_data = resp.json()
        access_token = token_data.get('access_token')
        
        # Récupérer les infos de l'utilisateur
        user_resp = requests.get(
            f"{DISCORD_API_URL}/users/@me",
            headers={'Authorization': f'Bearer {access_token}'}
        )
        user_data = user_resp.json()
        
        session['user_id'] = user_data['id']
        session['username'] = user_data['username']
        session['avatar'] = user_data.get('avatar')
        
        return redirect(url_for('dashboard'))
    except Exception as e:
        print(f"Erreur OAuth: {e}")
        return redirect(url_for('index'))

@app.route('/dashboard')
@require_login
def dashboard():
    return render_template('dashboard.html', username=session.get('username'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# API Endpoints
@app.route('/api/services', methods=['GET'])
@require_login
def get_services():
    user_id = session['user_id']
    services = services_db.get(user_id, [])
    return jsonify(services)

@app.route('/api/services', methods=['POST'])
@require_login
def add_service():
    user_id = session['user_id']
    data = request.json
    
    if user_id not in services_db:
        services_db[user_id] = []
    
    service = {
        'id': len(services_db[user_id]) + 1,
        'name': data.get('name'),
        'url': data.get('url'),
        'status': 'online',
        'last_check': None
    }
    
    services_db[user_id].append(service)
    return jsonify(service), 201

@app.route('/api/services/<int:service_id>', methods=['DELETE'])
@require_login
def delete_service(service_id):
    user_id = session['user_id']
    if user_id in services_db:
        services_db[user_id] = [s for s in services_db[user_id] if s['id'] != service_id]
    return jsonify({'status': 'deleted'}), 200

@app.route('/api/status')
def api_status():
    """État global des services"""
    all_services = []
    for services in services_db.values():
        all_services.extend(services)
    
    online = sum(1 for s in all_services if s['status'] == 'online')
    down = sum(1 for s in all_services if s['status'] == 'down')
    
    return jsonify({
        'online': online,
        'down': down,
        'total': len(all_services)
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
