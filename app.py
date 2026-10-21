from flask import Flask, request, send_file
import requests
import io
from flask_cors import CORS
import traceback

app = Flask(__name__)
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
        # 1. VOICEVOXから音声設定（クエリ）を取得
        print(f"Requesting audio_query for text: {text}")
        q_res = requests.post(f"{TARGET_API}/audio_query", params={"text": text, "speaker": 13}, timeout=10)
        
        if not q_res.ok:
            print(f"Audio query failed: {q_res.status_code} - {q_res.text}")
            return f"クエリ作成エラー: {q_res.text}", 500
        
        q_data = q_res.json()
        q_data["speedScale"] = speed
        q_data["pitchScale"] = -0.05

        # 2. 音声合成を実行
        print("Requesting synthesis...")
        s_res = requests.post(f"{TARGET_API}/synthesis", params={"speaker": 13}, json=q_data, timeout=15)
        
        if not s_res.ok:
            print(f"Synthesis failed: {s_res.status_code} - {s_res.text}")
            return f"音声合成エラー: {s_res.text}", 500

        print("Successfully generated audio.")
        return send_file(io.BytesIO(s_res.content), mimetype='audio/wav')

    except Exception as e:
        print("Exception occurred:")
        traceback.print_exc()
        return str(e), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
