from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import json
import background_news_updater  # 같은 디렉토리에 있어야 함

app = Flask(__name__)
CORS(app)

NEWS_FILE = 'positive_news.json'

@app.route('/')
def home():
    return '✅ NovaTicker AI Finder is running.'

@app.route('/data.json')
def get_all_data():
    try:
        with open(NEWS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return jsonify(data)
    except:
        return jsonify({})

@app.route('/update_news')
def trigger_news_update():
    try:
        background_news_updater.update_news()
        return '✅ News updated successfully.'
    except Exception as e:
        return f'❌ Error: {str(e)}'

@app.route('/delete_news', methods=['POST'])
def delete_news():
    try:
        symbol = request.json.get('symbol')
        date = request.json.get('date')
        title = request.json.get('title')

        with open(NEWS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if date in data:
            data[date] = [item for item in data[date] if not (item['symbol'] == symbol and item['title'] == title)]
            if not data[date]:
                del data[date]

        with open(NEWS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
