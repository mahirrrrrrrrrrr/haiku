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

# Initialize the client with the API key from environment variables
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
        # STRICT RULE: Pass ONLY the raw text to be spoken.
        # Do not include any instructions like "Read this like an old lady".
        prompt = text

        response = client.models.generate_content(
            model='gemini-2.5-flash', # Or gemini-3.8-flash if strictly required by your project
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name="Aoede"  # Aoede is a calm, female voice
                        )
                    )
                )
            )
        )

        audio_bytes = None
        debug_info = []

        if response.candidates:
            for i, candidate in enumerate(response.candidates):
                if candidate.content and candidate.content.parts:
                    for j, part in enumerate(candidate.content.parts):
                        # Explicitly check for inline_data which holds the audio
                        if hasattr(part, 'inline_data') and part.inline_data:
                            if hasattr(part.inline_data, 'data') and part.inline_data.data:
                                audio_bytes = part.inline_data.data
                                break
                    if audio_bytes:
                        break

        if not audio_bytes:
            # If it STILL returns text, capture it for debugging
            if response.text:
                debug_info.append(f"Model returned text instead of audio: {response.text[:50]}...")
            return f"音声データが見つかりません。APIの応答内容: {' | '.join(debug_info)}", 500

        # Decode if base64 string
        if isinstance(audio_bytes, str):
            audio_bytes = base64.b64decode(audio_bytes)

        # Ensure WAV format for browser playback
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
