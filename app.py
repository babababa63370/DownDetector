from flask import Flask, render_template, jsonify, request, session, redirect, url_for
from config import DISCORD_CLIENT_ID, DISCORD_CLIENT_SECRET, SECRET_KEY, SUPABASE_URL, SUPABASE_KEY, DISCORD_TOKEN
from supabase import create_client
from discord_bot import bot
import requests
from functools import wraps
import os
import hashlib

# Discord OAuth URLs
DISCORD_OAUTH_URL = "https://discord.com/api/oauth2/authorize"
DISCORD_TOKEN_URL = "https://discord.com/api/oauth2/token"
DISCORD_API_URL = "https://discord.com/api"

app = Flask(__name__)
app.secret_key = SECRET_KEY

# Supabase
supabase = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None

# Stockage en mémoire des utilisateurs (en dev)
users_db = {}

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def require_login(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/login/discord')
def login_discord():
    callback_url = os.getenv("CALLBACK_URL", "http://localhost:5000/callback/discord")
    return redirect(
        f"{DISCORD_OAUTH_URL}?client_id={DISCORD_CLIENT_ID}&redirect_uri={callback_url}&response_type=code&scope=identify%20email"
    )

@app.route('/callback/discord')
def callback_discord():
    code = request.args.get('code')
    if not code:
        return redirect(url_for('index'))
    
    callback_url = os.getenv("CALLBACK_URL", "http://localhost:5000/callback/discord")
    try:
        resp = requests.post(DISCORD_TOKEN_URL, data={
            'client_id': DISCORD_CLIENT_ID,
            'client_secret': DISCORD_CLIENT_SECRET,
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': callback_url
        })
        
        token_data = resp.json()
        if 'error' in token_data:
            print(f"Discord error: {token_data}")
            return redirect(url_for('index'))
        
        access_token = token_data.get('access_token')
        
        user_resp = requests.get(
            f"{DISCORD_API_URL}/users/@me",
            headers={'Authorization': f'Bearer {access_token}'}
        )
        user_data = user_resp.json()
        
        if 'error' in user_data:
            print(f"Discord user error: {user_data}")
            return redirect(url_for('index'))
        
        session['user_id'] = user_data['id']
        session['username'] = user_data['username']
        session['email'] = user_data.get('email')
        
        # Récupère l'avatar Discord avec le bon format
        avatar_hash = user_data.get('avatar')
        print(f"DEBUG: Avatar data: {avatar_hash}, User ID: {user_data['id']}")
        
        if avatar_hash:
            # Détecte si c'est un animated avatar (gif) ou static (png)
            avatar_format = "gif" if avatar_hash.startswith("a_") else "png"
            session['avatar_url'] = f"https://cdn.discordapp.com/avatars/{user_data['id']}/{avatar_hash}.{avatar_format}?size=256"
        else:
            # Avatar par défaut basé sur discriminator
            session['avatar_url'] = f"https://cdn.discordapp.com/embed/avatars/{int(user_data['id']) % 5}.png"
        
        print(f"DEBUG: Avatar URL: {session['avatar_url']}")
        return redirect(url_for('dashboard'))
    except Exception as e:
        print(f"Discord callback error: {e}")
        return redirect(url_for('index'))

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username', '').strip()
    email = data.get('email', '').strip()
    password = data.get('password', '')
    
    if not username or not email or not password:
        return jsonify({'error': 'Tous les champs sont requis'}), 400
    
    if username in users_db:
        return jsonify({'error': 'Ce nom d\'utilisateur existe déjà'}), 400
    
    users_db[username] = {
        'email': email,
        'password': hash_password(password)
    }
    
    return jsonify({'success': True}), 201

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '')
    
    if username not in users_db:
        return jsonify({'error': 'Utilisateur ou mot de passe incorrect'}), 401
    
    user = users_db[username]
    if user['password'] != hash_password(password):
        return jsonify({'error': 'Utilisateur ou mot de passe incorrect'}), 401
    
    session['user_id'] = username
    session['username'] = username
    session['email'] = user['email']
    
    return jsonify({'success': True}), 200

@app.route('/dashboard')
@require_login
def dashboard():
    return render_template('dashboard.html', username=session.get('username'), avatar_url=session.get('avatar_url'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

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
        print(f"Erreur get_services: {e}")
        return jsonify([]), 200

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
        print(f"Erreur add_service: {e}")
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
        return jsonify({'online': 0, 'down': 0, 'total': 0})

@app.route('/api/logs/<int:service_id>')
@require_login
def get_logs(service_id):
    if not supabase:
        return jsonify([]), 200
    
    try:
        # Récupère les 100 derniers logs pour un service
        response = supabase.table("ping_logs").select("*").eq("service_id", service_id).order("created_at", desc=True).limit(100).execute()
        logs = response.data[::-1]  # Inverse pour avoir du plus ancien au plus récent
        
        # Si pas de logs, ajoute des données de test
        if len(logs) == 0:
            import random
            from datetime import datetime, timedelta
            test_logs = []
            for i in range(20):
                test_logs.append({
                    "service_id": service_id,
                    "owner_id": session['user_id'],
                    "service_name": "Test Data",
                    "status": "online" if random.random() > 0.1 else "down",
                    "latency_ms": random.randint(50, 500),
                    "created_at": (datetime.now() - timedelta(minutes=i*2)).isoformat()
                })
            logs = test_logs[::-1]
        
        return jsonify(logs)
    except Exception as e:
        print(f"Erreur get_logs: {e}")
        # Retourne des données de test en cas d'erreur
        import random
        from datetime import datetime, timedelta
        test_logs = []
        for i in range(20):
            test_logs.append({
                "service_id": service_id,
                "owner_id": session['user_id'],
                "service_name": "Test Data",
                "status": "online" if random.random() > 0.1 else "down",
                "latency_ms": random.randint(50, 500),
                "created_at": (datetime.now() - timedelta(minutes=i*2)).isoformat()
            })
        return jsonify(test_logs[::-1])

if __name__ == '__main__':
    if DISCORD_TOKEN:
        print("🤖 Bot Discord lancé en arrière-plan...")
        import threading
        bot_thread = threading.Thread(target=lambda: bot.run(DISCORD_TOKEN), daemon=True)
        bot_thread.start()
    
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False, threaded=True)
