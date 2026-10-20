from flask import Flask, request, send_file
import requests
import io
from flask_cors import CORS

app = Flask(__name__)
# すべてのオリジンからのアクセスを許可
CORS(app, resources={r"/*": {"origins": "*"}})

TARGET_API = "https://api.voicevox.su-shiki.com/v1"

@app.route('/proxy-speak', methods=['POST', 'OPTIONS'])
def proxy_speak():
    if request.method == 'OPTIONS':
        return '', 200

    data = request.get_json() or {}
    text = data.get('text', '')
    speed = float(data.get('speed', 0.75))
    
    if not text:
        return "文章がありません", 400

    try:
        # VOICEVOXから音声設定（クエリ）を取得
        q_res = requests.post(f"{TARGET_API}/audio_query", params={"text": text, "speaker": 13})
        if not q_res.ok:
            return "クエリ作成エラー", 500
        
        q_data = q_res.json()
        q_data["speedScale"] = speed
        q_data["pitchScale"] = -0.05

        # 音声合成を実行
        s_res = requests.post(f"{TARGET_API}/synthesis", params={"speaker": 13}, json=q_data)
        if not s_res.ok:
            return "音声合成エラー", 500

        # 音声ファイル（WAV）を返す
        return send_file(io.BytesIO(s_res.content), mimetype='audio/wav')

    except Exception as e:
        return str(e), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
