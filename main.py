from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import json
import os

app = Flask(__name__)
CORS(app)

# 홈 경로 처리 추가 (에러 해결용)
@app.route('/')
def home():
    return '✅ NovaTicker AI Finder is running.'

# 데이터 응답 API
@app.route('/data.json')
def get_data():
    try:
        with open('positive_news.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 뉴스 수동 삭제 API
@app.route('/delete_news', methods=['POST'])
def delete_news():
    try:
        req = request.get_json()
        date = req.get('date')
        title = req.get('title')
        if not date or not title:
            return jsonify({'error': 'Missing date or title'}), 400

        with open('positive_news.json', 'r', encoding='utf-8') as f:
            data = json.load(f)

        if date in data:
            before = len(data[date])
            data[date] = [item for item in data[date] if item['title'] != title]
            after = len(data[date])
            if before != after:
                with open('positive_news.json', 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                return jsonify({'message': 'Deleted'}), 200
            else:
                return jsonify({'error': 'Not found'}), 404
        else:
            return jsonify({'error': 'Date not found'}), 404

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run()
