import subprocess
import os
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS

app = Flask(__name__)
CORS(app, origins=["*"])  # Allow access from any origin

VIDEO_OUTPUT = "streamed_video.mp4"

@app.route('/')
def home():
    return jsonify({"message": "Welcome to the Video Service!"})

@app.route('/start-streaming', methods=['POST'])
def start_streaming():
    data = request.json
    video_url = data.get("video_url")
    cookies = data.get("cookies")  # Get cookies from the frontend if passed

    if not video_url:
        return jsonify({"error": "Missing video_url"}), 400

    try:
        # Check if cookies are provided and pass them to yt-dlp
        yt_dlp_command = [
            "python", "-m", "yt_dlp", "--cookies", cookies, "-o", "-", video_url
        ]
        ffmpeg_command = [
            "ffmpeg", "-i", "-", "-c:v", "libx264", "-preset", "fast", "-movflags", "frag_keyframe+empty_moov",
            "-f", "mp4", VIDEO_OUTPUT
        ]

        yt_dlp_process = subprocess.Popen(yt_dlp_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        ffmpeg_process = subprocess.Popen(ffmpeg_command, stdin=yt_dlp_process.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        yt_dlp_process.stdout.close()
        yt_dlp_stdout, yt_dlp_stderr = yt_dlp_process.communicate()
        ffmpeg_stdout, ffmpeg_stderr = ffmpeg_process.communicate()

        # Log any yt-dlp or ffmpeg errors
        print(f"yt-dlp stdout: {yt_dlp_stdout.decode()}")
        print(f"yt-dlp stderr: {yt_dlp_stderr.decode()}")
        print(f"ffmpeg stdout: {ffmpeg_stdout.decode()}")
        print(f"ffmpeg stderr: {ffmpeg_stderr.decode()}")

        if ffmpeg_process.returncode != 0:
            return jsonify({"error": f"Failed to process video: {ffmpeg_stderr.decode()}"}), 500

        return jsonify({"message": "Video ready for streaming!", "video_url": "/video"}), 200

    except Exception as e:
        return jsonify({"error": f"Failed to process video: {str(e)}"}), 500

@app.route('/video', methods=['GET'])
def video():
    if not os.path.exists(VIDEO_OUTPUT):
        return jsonify({"error": "No video found. Start streaming first."}), 404
    return send_file(VIDEO_OUTPUT, mimetype='video/mp4')

@app.route('/stop-streaming', methods=['POST'])
def stop_streaming():
    if os.path.exists(VIDEO_OUTPUT):
        os.remove(VIDEO_OUTPUT)
        return jsonify({"message": "Streaming stopped and video file deleted."}), 200
    return jsonify({"error": "No video file to delete."}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
