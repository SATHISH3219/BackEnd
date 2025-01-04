from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import subprocess
import os

app = Flask(__name__)
CORS(app, origins=["*"])

VIDEO_OUTPUT = "streamed_video.mp4"
COOKIES_FILE = "cookies.txt"  # Path to the cookies file
yt_dlp_process = None
ffmpeg_process = None


@app.route('/')
def home():
    return jsonify({"message": "Welcome to the Video Service!"})


@app.route('/start-streaming', methods=['POST'])
def start_streaming():
    global yt_dlp_process, ffmpeg_process

    data = request.json
    video_url = data.get("video_url")

    if not video_url:
        return jsonify({"error": "Missing video_url"}), 400

    try:
        # Ensure the cookies file exists
        if not os.path.exists(COOKIES_FILE):
            return jsonify({"error": "Cookies file not found. Please provide a valid cookies file."}), 400

        # Check if the video is live or pre-recorded
        is_live_check_command = [
            "python", "-m", "yt_dlp", "--cookies", COOKIES_FILE, "--get-url", video_url
        ]
        result = subprocess.run(is_live_check_command, capture_output=True, text=True)
        if result.returncode != 0:
            return jsonify({"error": "Failed to fetch video details. Check the video URL or cookies."}), 400

        is_live = "live" in result.stdout.lower()

        yt_dlp_command = [
            "python", "-m", "yt_dlp", "--cookies", COOKIES_FILE, "-o", "-", video_url
        ]

        # FFmpeg command to stream video to MP4
        ffmpeg_command = [
            "ffmpeg", "-re" if is_live else "", "-i", "-", "-c:v", "libx264", "-preset", "fast",
            "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-movflags", "frag_keyframe+empty_moov",
            "-f", "mp4", VIDEO_OUTPUT
        ]
        ffmpeg_command = [arg for arg in ffmpeg_command if arg]  # Remove empty arguments

        # Start yt-dlp and FFmpeg processes
        yt_dlp_process = subprocess.Popen(yt_dlp_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        ffmpeg_process = subprocess.Popen(ffmpeg_command, stdin=yt_dlp_process.stdout, stderr=subprocess.PIPE)
        yt_dlp_process.stdout.close()

        return jsonify({
            "message": "Streaming started!",
            "stream_url": "/video",
            "type": "live" if is_live else "recorded"
        }), 200

    except Exception as e:
        return jsonify({"error": f"Failed to start streaming: {str(e)}"}), 500


@app.route('/video', methods=['GET'])
def video():
    if not os.path.exists(VIDEO_OUTPUT):
        return jsonify({"error": "No video found. Start streaming first."}), 404
    try:
        return send_file(VIDEO_OUTPUT, mimetype='video/mp4')
    except Exception as e:
        return jsonify({"error": f"Failed to retrieve video: {str(e)}"}), 500


@app.route('/stop-streaming', methods=['POST'])
def stop_streaming():
    global yt_dlp_process, ffmpeg_process

    try:
        # Terminate yt-dlp and FFmpeg processes
        if ffmpeg_process:
            ffmpeg_process.terminate()
            ffmpeg_process.wait()
            ffmpeg_process = None

        if yt_dlp_process:
            yt_dlp_process.terminate()
            yt_dlp_process.wait()
            yt_dlp_process = None

        # Delete the output video file
        if os.path.exists(VIDEO_OUTPUT):
            os.remove(VIDEO_OUTPUT)

        return jsonify({"message": "Streaming stopped and video file deleted."}), 200

    except Exception as e:
        return jsonify({"error": f"Failed to stop streaming: {str(e)}"}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
