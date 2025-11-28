from flask import Flask, render_template, jsonify, request, session, redirect, url_for
from config import DISCORD_CLIENT_ID, DISCORD_CLIENT_SECRET, SECRET_KEY, SUPABASE_URL, SUPABASE_KEY, DISCORD_TOKEN
from supabase import create_client
from discord_bot import bot
import requests
from functools import wraps
import os
import hashlib

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
    return render_template('dashboard.html', username=session.get('username'))

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

if __name__ == '__main__':
    if DISCORD_TOKEN:
        print("🤖 Bot Discord lancé en arrière-plan...")
        import threading
        bot_thread = threading.Thread(target=lambda: bot.run(DISCORD_TOKEN), daemon=True)
        bot_thread.start()
    
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False, threaded=True)
