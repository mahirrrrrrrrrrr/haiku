from flask import Flask, request, send_file
import os
import io
import base64
from flask_cors import CORS
from google import genai
from google.genai import types
import traceback
import wave

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# 環境変数からAPIキーを取得
api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

@app.route('/proxy-speak', methods=['POST', 'OPTIONS'])
def proxy_speak():
    if request.method == 'OPTIONS':
        return '', 200

    data = request.get_json() or {}
    text = data.get('text', '')
    
    if not text:
        return "文章がありません", 400

    try:
        prompt = f"以下の俳句を、お年寄りの女性（おばあちゃん）のように、非常におっとりと優しく、落ち着いた低いトーンでゆっくり朗読してください。: {text}"

        # 【修正】存在する、かつ音声出力に対応しているモデル名に変更
        response = client.models.generate_content(
            model='gemini-2.5-flash', # または 'gemini-2.0-flash'
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"]
            )
        )

        audio_bytes = None
        if response.candidates:
            for candidate in response.candidates:
                if candidate.content and candidate.content.parts:
                    for part in candidate.content.parts:
                        if hasattr(part, 'inline_data') and part.inline_data and part.inline_data.data:
                            audio_bytes = part.inline_data.data
                            break
                    if audio_bytes:
                        break

        if not audio_bytes:
            return "音声の生成に失敗しました（データが空です）", 500

        # SDKのバージョンによっては base64文字列 で返ってくることがあるためデコード処理を追加
        if isinstance(audio_bytes, str):
            audio_bytes = base64.b64decode(audio_bytes)

        # WAVヘッダー（RIFF）がない場合、PCMデータをWAV化
        if not audio_bytes.startswith(b'RIFF'):
            wav_io = io.BytesIO()
            with wave.open(wav_io, 'wb') as wav_file:
                wav_file.setnchannels(1)  # モノラル
                wav_file.setsampwidth(2)  # 16bit (2bytes)
                wav_file.setframerate(24000) # サンプリングレート(Geminiの標準は24kHz)
                wav_file.writeframes(audio_bytes)
            audio_bytes = wav_io.getvalue()

        return send_file(io.BytesIO(audio_bytes), mimetype='audio/wav')

    except Exception as e:
        traceback.print_exc()
        # クライアント側（ブラウザのコンソール）でもエラーの具体的な内容を見えるように文字列で返す
        return f"サーバーエラーが発生しました: {str(e)}", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
