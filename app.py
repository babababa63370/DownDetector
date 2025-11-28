from flask import Flask, render_template, jsonify, request, session, redirect, url_for
from config import DISCORD_CLIENT_ID, DISCORD_CLIENT_SECRET, SECRET_KEY, SUPABASE_URL, SUPABASE_KEY
from supabase import create_client
import requests
from functools import wraps
import os

app = Flask(__name__)
app.secret_key = SECRET_KEY

# Discord OAuth
DISCORD_OAUTH_URL = "https://discord.com/api/oauth2/authorize"
DISCORD_TOKEN_URL = "https://discord.com/api/oauth2/token"
DISCORD_API_URL = "https://discord.com/api"

# Supabase
supabase = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None

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
    if not supabase:
        return jsonify([]), 200
    
    try:
        user_id = session['user_id']
        response = supabase.table("services").select("*").eq("owner_id", user_id).execute()
        return jsonify(response.data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/services', methods=['POST'])
@require_login
def add_service():
    if not supabase:
        return jsonify({"error": "Supabase non configuré"}), 500
    
    try:
        user_id = session['user_id']
        data = request.json
        
        response = supabase.table("services").insert({
            'name': data.get('name'),
            'url': data.get('url'),
            'status': 'online',
            'owner_id': user_id,
            'guild_id': 0
        }).execute()
        
        return jsonify(response.data[0] if response.data else {}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/services/<int:service_id>', methods=['DELETE'])
@require_login
def delete_service(service_id):
    if not supabase:
        return jsonify({"error": "Supabase non configuré"}), 500
    
    try:
        supabase.table("services").delete().eq("id", service_id).execute()
        return jsonify({'status': 'deleted'}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/status')
def api_status():
    """État global des services"""
    if not supabase:
        return jsonify({'online': 0, 'down': 0, 'total': 0})
    
    try:
        response = supabase.table("services").select("status").execute()
        all_services = response.data
        
        online = sum(1 for s in all_services if s.get('status') == 'online')
        down = sum(1 for s in all_services if s.get('status') == 'down')
        
        return jsonify({
            'online': online,
            'down': down,
            'total': len(all_services)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
