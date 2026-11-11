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
        # 読み上げるテキストのみを渡す
        prompt = text

        response = client.models.generate_content(
            model='gemini-2.5-flash', # ※エラーになる場合は gemini-3.8-flash に変更
            contents=prompt,
            config=types.GenerateContentConfig(
                # エラーの原因となった speech_config を削除し、システムプロンプトとAUDIO指定のみにする
                system_instruction="あなたはテキスト読み上げ（TTS）エンジンです。ユーザーが入力したテキストをそのまま音声として出力してください。情景描写、感情表現のト書き、テキストでの返答、勝手な文章の追加は一切行わないでください。",
                response_modalities=["AUDIO"]
            )
        )

        audio_bytes = None
        debug_info = []

        if response.candidates:
            for i, candidate in enumerate(response.candidates):
                if candidate.content and candidate.content.parts:
                    for j, part in enumerate(candidate.content.parts):
                        if hasattr(part, 'inline_data') and part.inline_data:
                            if hasattr(part.inline_data, 'data') and part.inline_data.data:
                                audio_bytes = part.inline_data.data
                                break
                    if audio_bytes:
                        break

        if not audio_bytes:
            if response.text:
                debug_info.append(f"Model returned text instead of audio: {response.text[:50]}...")
            return f"音声データが見つかりません。APIの応答内容: {' | '.join(debug_info)}", 500

        # 文字列(Base64)で返ってきた場合はバイナリに変換
        if isinstance(audio_bytes, str):
            audio_bytes = base64.b64decode(audio_bytes)

        # WAVヘッダー（RIFF）がない場合、PCMデータをWAV化
        if not audio_bytes.startswith(b'RIFF'):
            wav_io = io.BytesIO()
            with wave.open(wav_io, 'wb') as wav_file:
                wav_file.setnchannels(1)  
                wav_file.setsampwidth(2)  
                wav_file.setframerate(24000) 
                wav_file.writeframes(audio_bytes)
            audio_bytes = wav_io.getvalue()

        return send_file(io.BytesIO(audio_bytes), mimetype='audio/wav')

    except Exception as e:
        traceback.print_exc()
        return f"サーバーエラーが発生しました: {str(e)}", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
