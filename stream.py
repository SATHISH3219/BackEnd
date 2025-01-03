from flask import Flask, request, jsonify, send_file, redirect, url_for
from flask_cors import CORS
import subprocess
import os

app = Flask(__name__)
CORS(app, origins=["*"])  # Allow access from any origin

VIDEO_OUTPUT = "streamed_video.mp4"
COOKIES_FILE = os.getenv("COOKIES_FILE", "cookies.txt")  # Environment variable for cookies file

@app.route('/')
def home():
    if os.path.exists(VIDEO_OUTPUT):
        # Extract video duration using ffprobe
        try:
            result = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", VIDEO_OUTPUT],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            video_duration = float(result.stdout.strip())
        except Exception as e:
            video_duration = 0  # Default to 0 if extraction fails

        return jsonify({
            "message": "Video is ready for streaming.",
            "video_url": "/video",
            "duration_seconds": video_duration
        }), 200
    return jsonify({"message": "No video is currently available for streaming."}), 404


@app.route('/stream', methods=['POST'])
def developer_stream():
    video_url = request.form.get("video_url")
    if not video_url:
        return jsonify({"error": "Please provide a valid video URL."}), 400

    # Start streaming
    return redirect(url_for('start_streaming', video_url=video_url))


@app.route('/start-streaming', methods=['GET', 'POST'])
def start_streaming():
    # Retrieve video_url from either form data (for POST) or query params (for GET)
    video_url = request.form.get("video_url") or request.args.get("video_url")

    if not video_url:
        return jsonify({"error": "Missing video_url"}), 400

    if not os.path.exists(COOKIES_FILE):
        return jsonify({"error": f"Cookies file not found at {COOKIES_FILE}"}), 500

    try:
        # Download and stream live video (Twitch, YouTube, etc.) using yt-dlp
        yt_dlp_command = [
            "python", "-m", "yt_dlp", "--cookies", COOKIES_FILE, "-o", "-", video_url
        ]
        ffmpeg_command = [
            "ffmpeg", "-i", "-", "-c:v", "libx264", "-preset", "fast", "-movflags", "frag_keyframe+empty_moov",
            "-f", "mp4", VIDEO_OUTPUT
        ]

        yt_dlp_process = subprocess.Popen(yt_dlp_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        ffmpeg_process = subprocess.Popen(ffmpeg_command, stdin=yt_dlp_process.stdout, stderr=subprocess.PIPE)
        yt_dlp_process.stdout.close()
        ffmpeg_process.communicate()

        if not os.path.exists(VIDEO_OUTPUT):
            return jsonify({"error": "Failed to process video"}), 500

        # Extract video duration
        try:
            result = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", VIDEO_OUTPUT],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            video_duration = float(result.stdout.strip())
        except Exception:
            video_duration = 0  # Default to 0 if extraction fails

        return jsonify({
            "message": "Video ready for streaming!",
            "video_url": "/video",
            "duration_seconds": video_duration
        }), 200

    except subprocess.CalledProcessError as e:
        return jsonify({"error": f"Video processing failed: {e.stderr}"}), 500
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
    app.run(host='0.0.0.0', port=5000, debug=True)
