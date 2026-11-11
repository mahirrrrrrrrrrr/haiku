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
        # 修正2: ただのテキストではなく、読み上げを強制するプロンプトにする
        prompt = f"以下の文章を読み上げてください:\n\n{text}"

        response = client.models.generate_content(
            model='gemini-2.5-flash', # 修正1: 音声出力対応モデルを指定
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction="あなたは指定されたテキストを、お年寄りの女性（おばあちゃん）のように、非常におっとりと優しく、落ち着いた低いトーンで読み上げる音声合成エンジンです。テキストでの返答、情景描写などの文字出力は一切禁止されています。入力された文字を純粋な音声データとしてのみ出力してください。",
                response_modalities=["AUDIO"],
                # 修正3: SpeechConfigを追加し、声質を指定（Aoede, Charon, Fenrir, Kore, Puck）
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name="Aoede" # 落ち着いた女性の声に近いものを選択
                        )
                    )
                )
            )
        )

        audio_bytes = None
        debug_info = []

        if response.candidates:
            for i, candidate in enumerate(response.candidates):
                debug_info.append(f"Candidate[{i}] finish_reason: {candidate.finish_reason}")
                if candidate.content and candidate.content.parts:
                    for j, part in enumerate(candidate.content.parts):
                        if hasattr(part, 'text') and part.text:
                            debug_info.append(f"part[{j}] Text: {part.text[:20]}...")

                        # 音声データの抽出
                        if hasattr(part, 'inline_data') and part.inline_data:
                            if hasattr(part.inline_data, 'data') and part.inline_data.data:
                                audio_bytes = part.inline_data.data
                                debug_info.append(f"part[{j}] Audio found!")
                                break
                            else:
                                debug_info.append(f"part[{j}] inline_data is empty")
                        else:
                            debug_info.append(f"part[{j}] attrs: {dir(part)}")

                    if audio_bytes:
                        break
                else:
                    debug_info.append("No content or parts in candidate")
        else:
            debug_info.append("No candidates in response")

        if not audio_bytes:
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
