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

    # Ensure the request is in JSON format
    if not request.is_json:
        return jsonify({"error": "Invalid JSON format"}), 400

    data = request.json
    video_url = data.get("video_url")

    # Validate that video_url is present
    if not video_url:
        return jsonify({"error": "Missing video_url"}), 400

    try:
        # Check if cookies file exists
        if not os.path.exists(COOKIES_FILE):
            return jsonify({"error": "Cookies file not found. Please provide a valid cookies file."}), 400

        # Check if the video URL is accessible and get if it's live or recorded
        is_live_check_command = [
            "python", "-m", "yt_dlp", "--cookies", COOKIES_FILE, "--get-url", video_url
        ]
        result = subprocess.run(is_live_check_command, capture_output=True, text=True)
        
        # Check for errors in the output
        if result.returncode != 0:
            return jsonify({"error": f"Failed to access video: {result.stderr}"}), 500

        is_live = "live" in result.stdout.lower()

        yt_dlp_command = [
            "python", "-m", "yt_dlp", "--cookies", COOKIES_FILE, "-o", "-", video_url
        ]

        # ffmpeg command to stream to MP4
        ffmpeg_command = [
            "ffmpeg", "-re" if is_live else "", "-i", "-", "-c:v", "libx264", "-preset", "fast",
            "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-movflags", "frag_keyframe+empty_moov",
            "-f", "mp4", VIDEO_OUTPUT
        ]
        ffmpeg_command = [arg for arg in ffmpeg_command if arg]  # Remove empty arguments

        # Start yt-dlp and ffmpeg processes
        yt_dlp_process = subprocess.Popen(yt_dlp_command, stdout=subprocess.PIPE)
        ffmpeg_process = subprocess.Popen(ffmpeg_command, stdin=yt_dlp_process.stdout)
        yt_dlp_process.stdout.close()

        return jsonify({
            "message": "Streaming started!",
            "stream_url": "/video",
            "type": "live" if is_live else "recorded"
        }), 200

    except subprocess.CalledProcessError as e:
        return jsonify({"error": f"Failed to execute subprocess: {e}"}), 500

    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500


@app.route('/video', methods=['GET'])
def video():
    # Check if video output exists before attempting to send it
    if not os.path.exists(VIDEO_OUTPUT):
        return jsonify({"error": "No video found. Start streaming first."}), 404
    return send_file(VIDEO_OUTPUT, mimetype='video/mp4')


@app.route('/stop-streaming', methods=['POST'])
def stop_streaming():
    global yt_dlp_process, ffmpeg_process

    try:
        # Stop yt-dlp and ffmpeg processes if running
        if ffmpeg_process:
            ffmpeg_process.terminate()
            ffmpeg_process.wait()
            ffmpeg_process = None

        if yt_dlp_process:
            yt_dlp_process.terminate()
            yt_dlp_process.wait()
            yt_dlp_process = None

        # Delete the output video file if exists
        if os.path.exists(VIDEO_OUTPUT):
            os.remove(VIDEO_OUTPUT)

        return jsonify({"message": "Streaming stopped and video file deleted."}), 200

    except Exception as e:
        return jsonify({"error": f"Failed to stop streaming: {str(e)}"}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
