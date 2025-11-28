from flask import Flask, request, jsonify
import os

app = Flask(__name__)

def charger_regles():
    """Charge les règles depuis regle.txt"""
    regles = {}
    if os.path.exists('regle.txt'):
        with open('regle.txt', 'r', encoding='utf-8') as f:
            for ligne in f:
                ligne = ligne.strip()
                if ligne and '|' in ligne:
                    mots_cles, reponse = ligne.split('|', 1)
                    for mot in mots_cles.split(','):
                        regles[mot.strip().lower()] = reponse.strip()
    return regles

def generer_reponse(message, regles):
    """Génère une réponse basée sur les règles"""
    message_lower = message.lower().strip()
    
    # Vérifier correspondance exacte
    if message_lower in regles:
        return regles[message_lower]
    
    # Vérifier correspondance partielle (contient)
    for mot_cle, reponse in regles.items():
        if mot_cle in message_lower:
            return reponse
    
    # Pas de correspondance
    return "Je n'ai pas bien compris. Peux-tu reformuler?"

# Charger les règles au démarrage
REGLES = charger_regles()

@app.route('/')
def index():
    return open('index.html').read()

@app.route('/chat', methods=['POST'])
def chat():
    """Endpoint pour recevoir les messages et envoyer les réponses"""
    data = request.json
    message = data.get('message', '').strip()
    
    if not message:
        return jsonify({'reponse': 'Dis-moi quelque chose!'})
    
    reponse = generer_reponse(message, REGLES)
    return jsonify({'reponse': reponse})

@app.route('/recharger-regles', methods=['POST'])
def recharger_regles():
    """Recharge les règles depuis le fichier"""
    global REGLES
    REGLES = charger_regles()
    return jsonify({'statut': 'Règles rechargées!'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
