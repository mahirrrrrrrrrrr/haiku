from flask import Flask, request, send_file
import requests
import io
from flask_cors import CORS
import traceback

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# 現在安定して利用できるVOICEVOX互換の公開エンドポイント
TARGET_API = "https://voicevox-engine.azurewebsites.net"

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
        # 1. VOICEVOXから音声設定（クエリ）を取得 (おばあちゃん等に馴染みのある話者ID: 3 または 13など)
        speaker_id = 3 # おばあちゃんや女性キャラクター等のデフォルトとして一般的なID
        q_res = requests.post(f"{TARGET_API}/audio_query", params={"text": text, "speaker": speaker_id}, timeout=15)
        
        if not q_res.ok:
            return f"クエリ作成エラー: {q_res.text}", 500
        
        q_data = q_res.json()
        q_data["speedScale"] = speed
        q_data["pitchScale"] = -0.05

        # 2. 音声合成を実行
        s_res = requests.post(f"{TARGET_API}/synthesis", params={"speaker": speaker_id}, json=q_data, timeout=20)
        
        if not s_res.ok:
            return f"音声合成エラー: {s_res.text}", 500

        # 3. 音声ファイル（WAV）をMonacaへ返す
        return send_file(io.BytesIO(s_res.content), mimetype='audio/wav')

    except Exception as e:
        traceback.print_exc()
        return str(e), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
