from flask import Flask, request, jsonify
import subprocess
import os
import uuid
import requests
import base64
import asyncio
import edge_tts

app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"})

@app.route('/tts', methods=['POST'])
def text_to_speech():
    data = request.json
    text = data.get('text', '')
    voice = data.get('voice', 'es-ES-AlvaroNeural')
    
    job_id = str(uuid.uuid4())
    os.makedirs(f'/tmp/{job_id}', exist_ok=True)
    output_path = f'/tmp/{job_id}/audio.mp3'
    
    async def generate():
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_path)
    
    asyncio.run(generate())
    
    with open(output_path, 'rb') as f:
        audio_b64 = base64.b64encode(f.read()).decode()
    
    subprocess.run(['rm', '-rf', f'/tmp/{job_id}'])
    
    return jsonify({"audio": audio_b64})

@app.route('/create-video', methods=['POST'])
def create_video():
    data = request.json
    image_urls = data.get('images', [])
    audio_base64 = data.get('audio_base64', '')
    duration_per_image = data.get('duration', 5)
    
    job_id = str(uuid.uuid4())
    os.makedirs(f'/tmp/{job_id}', exist_ok=True)
    
    image_files = []
    for i, url in enumerate(image_urls):
        img_path = f'/tmp/{job_id}/img_{i}.jpg'
        try:
            r = requests.get(url, timeout=30)
            with open(img_path, 'wb') as f:
                f.write(r.content)
            image_files.append(img_path)
        except:
            pass
    
    if not image_files:
        return jsonify({"error": "No images downloaded"}), 400
    
    audio_path = f'/tmp/{job_id}/audio.mp3'
    if audio_base64:
        with open(audio_path, 'wb') as f:
            f.write(base64.b64decode(audio_base64))
    
    concat_file = f'/tmp/{job_id}/concat.txt'
    with open(concat_file, 'w') as f:
        for img in image_files:
            f.write(f"file '{img}'\n")
            f.write(f"duration {duration_per_image}\n")
        if image_files:
            f.write(f"file '{image_files[-1]}'\n")
    
    output_path = f'/tmp/{job_id}/output.mp4'
    
    subprocess.run([
        'ffmpeg', '-f', 'concat', '-safe', '0',
        '-i', concat_file,
        '-i', audio_path,
        '-c:v', 'libx264', '-c:a', 'aac',
        '-pix_fmt', 'yuv420p',
        '-vf', 'scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2',
        '-shortest', '-y', output_path
    ])
    
    if not os.path.exists(output_path):
        return jsonify({"error": "Video creation failed"}), 500
    
    with open(output_path, 'rb') as f:
        video_b64 = base64.b64encode(f.read()).decode()
    
    subprocess.run(['rm', '-rf', f'/tmp/{job_id}'])
    
    return jsonify({"video": video_b64, "job_id": job_id})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
