from flask import Flask, render_template, jsonify, request

app = Flask(__name__)
count = 0

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/increment', methods=['POST'])
def increment():
    global count
    count += 1
    return jsonify({'count': count})

@app.route('/reset', methods=['POST'])
def reset():
    global count
    count = 0
    return jsonify({'count': count})

@app.route('/get-count', methods=['GET'])
def get_count():
    return jsonify({'count': count})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
