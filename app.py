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
        prompt = f"以下のテキストを読み上げてください。\nテキスト: {text}"

        # エラーメッセージの指示通り、最新の gemini-3.8-flash を指定します
        response = client.models.generate_content(
            model='gemini-3.8-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction="あなたは音声合成エンジンです。テキスト出力は一切禁止し、純粋な音声データのみを生成してください。",
                response_modalities=["AUDIO"]
            )
        )

        audio_bytes = None
        
        # レスポンスから音声データを抽出
        if response.candidates:
            for candidate in response.candidates:
                if candidate.content and candidate.content.parts:
                    for part in candidate.content.parts:
                        # APIからの音声データは inline_data.data に格納される
                        if hasattr(part, 'inline_data') and part.inline_data and part.inline_data.data:
                            audio_bytes = part.inline_data.data
                            break
                if audio_bytes:
                    break

        if not audio_bytes:
            return "音声データが生成されませんでした。APIがテキストのみを返却した可能性があります。", 500

        # 文字列(Base64)で返ってきた場合はバイナリに変換
        if isinstance(audio_bytes, str):
            audio_bytes = base64.b64decode(audio_bytes)

        # 音声データをWAV形式として返却
        return send_file(io.BytesIO(audio_bytes), mimetype='audio/wav')

    except Exception as e:
        traceback.print_exc()
        return f"サーバーエラーが発生しました: {str(e)}", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
