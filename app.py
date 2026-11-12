from flask import Flask, request, send_file
import os
import io
import base64
from flask_cors import CORS
from google import genai
from google.genai import types
import traceback

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# 環境変数からAPIキーを取得
api_key = os.environ.get("GEMINI_API_KEY")

# 【重要】音声生成などの最新機能を使うため、明示的に v1alpha バージョンを指定します
client = genai.Client(
    api_key=api_key,
    http_options={'api_version': 'v1alpha'}
)

@app.route('/proxy-speak', methods=['POST', 'OPTIONS'])
def proxy_speak():
    if request.method == 'OPTIONS':
        return '', 200

    data = request.get_json() or {}
    text = data.get('text', '')
    
    if not text:
        return "文章がありません", 400

    try:
        prompt = f"以下のテキストを読み上げてください。\nテキスト: {text}"

        # モデルは現状最も安定している gemini-2.0-flash を指定します
        # ※もし再度「3.8-flashにしてください」というエラーが出た場合は、'gemini-3.8-flash'に書き換えてください。
        model_name = 'gemini-3.8-flash'

        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction="あなたは音声合成エンジンです。テキスト出力は一切禁止し、純粋な音声データのみを生成してください。",
                response_modalities=["AUDIO"],
                # v1alphaを指定したことで、音声の種類を細かく設定できるようになります
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name="Aoede" # 女性の落ち着いた声（Aoede, Puck, Charon, Kore, Fenrirから選択可能）
                        )
                    )
                )
            )
        )

        audio_bytes = None
        
        # レスポンスから音声バイナリを抽出
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
            return "音声データが生成されませんでした。APIがテキストのみを返却した可能性があります。", 500

        if isinstance(audio_bytes, str):
            audio_bytes = base64.b64decode(audio_bytes)

        # 生成された音声を直接WAVとしてMonacaアプリへ返却します
        return send_file(io.BytesIO(audio_bytes), mimetype='audio/wav')

    except Exception as e:
        traceback.print_exc()
        return f"サーバーエラーが発生しました: {str(e)}", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
