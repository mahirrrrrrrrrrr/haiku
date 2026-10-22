from flask import Flask, request, send_file
import os
import io
from flask_cors import CORS
from google import genai
from google.genai import types
import traceback
import wave

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Renderに設定した環境変数からGeminiのAPIキーを読み込む
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
        # 年配のおばあちゃん風の落ち着いたおっとりした語り口を指示するプロンプト
        prompt = f"以下の俳句を、お年寄りの女性（おばあちゃん）のように、非常におっとりと優しく、落ち着いた低いトーンでゆっくり朗読してください: {text}"

        # Geminiの音声生成モデルを使用
        response = client.models.generate_content(
            model='gemini-2.5-flash-preview-tts',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name="Aoede"  # 落ち着いたトーンの音声（より年配・上品な女性風）
                        )
                    )
                )
            )
        )

        # 生成された音声バイナリの抽出
        audio_bytes = None
        for candidate in response.candidates:
            for part in candidate.content.parts:
                if part.inline_data and part.inline_data.data:
                    audio_bytes = part.inline_data.data
                    break

        if not audio_bytes:
            return "音声の生成に失敗しました（データが空です）", 500

        # WAVヘッダーを付与してブラウザで確実に再生できるようにする
        if not audio_bytes.startswith(b'RIFF'):
            wav_io = io.BytesIO()
            with wave.open(wav_io, 'wb') as wav_file:
                wav_file.setnchannels(1)  # モノラル
                wav_file.setsampwidth(2)  # 16bit
                wav_file.setframerate(24000) # サンプリングレート
                wav_file.writeframes(audio_bytes)
            audio_bytes = wav_io.getvalue()

        return send_file(io.BytesIO(audio_bytes), mimetype='audio/wav')

    except Exception as e:
        traceback.print_exc()
        return str(e), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
