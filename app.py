from flask import Flask, render_template, jsonify, request, session, redirect, url_for
from config import DISCORD_CLIENT_ID, DISCORD_CLIENT_SECRET, SECRET_KEY, SUPABASE_URL, SUPABASE_KEY, DISCORD_TOKEN
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

# Supabase REST API headers
SUPABASE_HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

def query_supabase(table, query=""):
    """Simple REST API call to Supabase"""
    try:
        url = f"{SUPABASE_URL}/rest/v1/{table}{query}"
        resp = requests.get(url, headers=SUPABASE_HEADERS, timeout=5)
        return resp.json() if resp.status_code == 200 else []
    except:
        return []

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
            return redirect(url_for('index'))
        
        access_token = token_data.get('access_token')
        user_resp = requests.get(
            f"{DISCORD_API_URL}/users/@me",
            headers={'Authorization': f'Bearer {access_token}'}
        )
        user_data = user_resp.json()
        
        if 'error' in user_data:
            return redirect(url_for('index'))
        
        session['user_id'] = user_data['id']
        session['username'] = user_data['username']
        session['email'] = user_data.get('email')
        
        # Avatar
        avatar_hash = user_data.get('avatar')
        if avatar_hash:
            avatar_format = "gif" if avatar_hash.startswith("a_") else "png"
            session['avatar_url'] = f"https://cdn.discordapp.com/avatars/{user_data['id']}/{avatar_hash}.{avatar_format}?size=256"
        else:
            session['avatar_url'] = f"https://cdn.discordapp.com/embed/avatars/{int(user_data['id']) % 5}.png"
        
        return redirect(url_for('dashboard'))
    except Exception as e:
        print(f"Discord callback error: {e}")
        return redirect(url_for('index'))

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
    try:
        user_id = session['user_id']
        services = query_supabase("services", f"?owner_id=eq.{user_id}")
        return jsonify(services), 200
    except Exception as e:
        return jsonify([]), 200

@app.route('/api/services', methods=['POST'])
@require_login
def add_service():
    try:
        user_id = session['user_id']
        data = request.json
        
        resp = requests.post(
            f"{SUPABASE_URL}/rest/v1/services",
            json={
                'name': data.get('name'),
                'url': data.get('url'),
                'status': 'online',
                'owner_id': user_id,
                'guild_id': 0
            },
            headers=SUPABASE_HEADERS,
            timeout=5
        )
        
        return jsonify(resp.json()[0] if resp.json() else {}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/services/<int:service_id>', methods=['DELETE'])
@require_login
def delete_service(service_id):
    try:
        requests.delete(
            f"{SUPABASE_URL}/rest/v1/services?id=eq.{service_id}",
            headers=SUPABASE_HEADERS,
            timeout=5
        )
        return jsonify({'status': 'deleted'}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/user')
@require_login
def get_user():
    avatar_url = session.get('avatar_url', "https://cdn.discordapp.com/embed/avatars/0.png")
    return jsonify({
        'username': session.get('username'),
        'avatar_url': avatar_url
    })

@app.route('/api/status')
def api_status():
    try:
        services = query_supabase("services", "?select=status")
        online = sum(1 for s in services if s.get('status') == 'online')
        down = sum(1 for s in services if s.get('status') == 'down')
        return jsonify({
            'online': online,
            'down': down,
            'total': len(services)
        })
    except:
        return jsonify({'online': 0, 'down': 0, 'total': 0})

@app.route('/api/logs/<int:service_id>')
@require_login
def get_logs(service_id):
    try:
        logs = query_supabase("ping_logs", f"?service_id=eq.{service_id}&order=created_at.desc&limit=100")
        return jsonify(logs[::-1]), 200
    except Exception as e:
        return jsonify([]), 200

@app.route('/api/ping/<int:service_id>', methods=['POST'])
@require_login
def manual_ping(service_id):
    try:
        services = query_supabase("services", f"?id=eq.{service_id}")
        if not services:
            return jsonify({'error': 'Service not found'}), 404
        
        service = services[0]
        if str(service['owner_id']) != str(session['user_id']):
            return jsonify({'error': 'Unauthorized'}), 403
        
        import time
        start_time = time.time()
        resp = requests.get(service['url'], timeout=5)
        latency_ms = int((time.time() - start_time) * 1000)
        new_status = "online" if resp.status_code == 200 else "down"
        
        # Enregistre le log
        log_resp = requests.post(
            f"{SUPABASE_URL}/rest/v1/ping_logs",
            json={
                "service_id": service_id,
                "owner_id": session['user_id'],
                "service_name": service['name'],
                "status": new_status,
                "latency_ms": latency_ms
            },
            headers=SUPABASE_HEADERS,
            timeout=5
        )
        
        # Update status
        requests.patch(
            f"{SUPABASE_URL}/rest/v1/services?id=eq.{service_id}",
            json={"status": new_status},
            headers=SUPABASE_HEADERS,
            timeout=5
        )
        
        return jsonify({
            'status': new_status,
            'latency_ms': latency_ms
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    if DISCORD_TOKEN:
        print("🤖 Bot Discord lancé en arrière-plan...")
        import threading
        bot_thread = threading.Thread(target=lambda: bot.run(DISCORD_TOKEN), daemon=True)
        bot_thread.start()
    
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False, threaded=True)
