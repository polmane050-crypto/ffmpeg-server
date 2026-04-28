from flask import Flask, request, jsonify
import subprocess
import os
import uuid
import requests
import base64

app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"})

@app.route('/create-video', methods=['POST'])
def create_video():
    data = request.json
    image_urls = data.get('images', [])
    audio_url = data.get('audio', '')
    duration_per_image = data.get('duration', 3)
    
    job_id = str(uuid.uuid4())
    os.makedirs(f'/tmp/{job_id}', exist_ok=True)
    
    image_files = []
    for i, url in enumerate(image_urls):
        img_path = f'/tmp/{job_id}/img_{i}.jpg'
        r = requests.get(url)
        with open(img_path, 'wb') as f:
            f.write(r.content)
        image_files.append(img_path)
    
    audio_path = f'/tmp/{job_id}/audio.mp3'
    r = requests.get(audio_url)
    with open(audio_path, 'wb') as f:
        f.write(r.content)
    
    concat_file = f'/tmp/{job_id}/concat.txt'
    with open(concat_file, 'w') as f:
        for img in image_files:
            f.write(f"file '{img}'\n")
            f.write(f"duration {duration_per_image}\n")
    
    output_path = f'/tmp/{job_id}/output.mp4'
    subprocess.run([
        'ffmpeg', '-f', 'concat', '-safe', '0',
        '-i', concat_file,
        '-i', audio_path,
        '-c:v', 'libx264', '-c:a', 'aac',
        '-shortest', '-y', output_path
    ])
    
    with open(output_path, 'rb') as f:
        video_b64 = base64.b64encode(f.read()).decode()
    
    return jsonify({"video": video_b64, "job_id": job_id})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
