from flask import Flask, request, send_file
import os
import io
from flask_cors import CORS
from google import genai
from google.genai import types
import traceback

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
        # Geminiに「おばあちゃん風の優しいトーンでゆっくり朗読する音声データを作る」ように指示
        prompt = f"以下の俳句を、おばあちゃんのようにおっとりと優しく、ゆっくりとしたトーンで読み上げてください。音声データのみを出力してください: {text}"

        # Geminiの音声出力対応モデル（例: gemini-2.5-flash または gemini-2.5-pro 等）で音声（AUDIO）を指定
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name="Puck" # またはお好みのボイス（Kore, Fenrirなど）
                        )
                    )
                )
            )
        )

        # 生成された音声バイナリを取り出す
        audio_bytes = None
        for part in response.candidates[0].content.parts:
            if part.inline_data and part.inline_data.mime_type.startswith("audio/"):
                audio_bytes = part.inline_data.data
                break

        if not audio_bytes:
            return "音声の生成に失敗しました", 500

        # Monacaへ音声ファイルとして返す
        return send_file(io.BytesIO(audio_bytes), mimetype='audio/mp3')

    except Exception as e:
        traceback.print_exc()
        return str(e), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
