from flask import Flask, jsonify, render_template
import json
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/data.json')
def get_data():
    try:
        with open('detected_gainers.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        return jsonify(data)
    except:
        return jsonify([])

if __name__ == '__main__':
    app.run()
