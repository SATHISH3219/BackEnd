# backend/app.py
from flask import Flask, request, jsonify
import subprocess
import os

app = Flask(__name__)

# Configuration for RTMP Server (YouTube as an example)
RTMP_URL = "rtmp://a.rtmp.youtube.com/live2"
STREAM_KEY = "your-youtube-stream-key"  # Replace with your actual YouTube stream key

@app.route('/start-stream', methods=['POST'])
def start_stream():
    # Get video URL and optional stream key
    data = request.json
    video_url = data.get('url')
    stream_key = data.get('stream_key', STREAM_KEY)
    
    if not video_url:
        return jsonify({"error": "Video URL is required"}), 400
    
    # RTMP URL where the video will be streamed
    rtmp_url = f"{RTMP_URL}/{stream_key}"
    
    # FFmpeg command to stream the video
    command = [
        'ffmpeg', '-re', '-i', video_url,
        '-c:v', 'libx264', '-preset', 'fast',
        '-c:a', 'aac', '-b:a', '128k', '-ar', '44100',
        '-f', 'flv', rtmp_url
    ]
    
    try:
        subprocess.Popen(command)
        return jsonify({"message": "Stream started successfully", "rtmp_url": rtmp_url}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
