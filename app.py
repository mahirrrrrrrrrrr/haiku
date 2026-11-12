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

        response = client.models.generate_content(
            model='gemini-3.8-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"]
            )
        )

        audio_bytes = None
        debug_info = [] # 原因究明のためのデバッグ情報を格納するリスト

        # レスポンスの中身を解析
        if response.candidates:
            for i, candidate in enumerate(response.candidates):
                debug_info.append(f"Candidate[{i}] finish_reason: {candidate.finish_reason}")
                if candidate.content and candidate.content.parts:
                    for j, part in enumerate(candidate.content.parts):
                        # テキストが返ってきていないかチェック
                        if hasattr(part, 'text') and part.text:
                            debug_info.append(f"part[{j}] Text: {part.text[:20]}...")
 
                        # 音声データを探す
                        if hasattr(part, 'inline_data') and part.inline_data:
                            if hasattr(part.inline_data, 'data') and part.inline_data.data:
                                audio_bytes = part.inline_data.data
                                debug_info.append(f"part[{j}] Audio found!")
                                break
                            else:
                                debug_info.append(f"part[{j}] inline_data is empty")
                        else:
                            # どんな属性を持っているか記録
                            debug_info.append(f"part[{j}] attrs: {dir(part)}")
 
                    if audio_bytes:
                        break
                else:
                    debug_info.append("No content or parts in candidate")
        else:
            debug_info.append("No candidates in response")

        if not audio_bytes:
            # 取得したデバッグ情報をブラウザのエラー画面に表示させる
            error_details = " | ".join(debug_info)
            return f"音声データが見つかりません。APIの応答内容: {error_details}", 500

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
