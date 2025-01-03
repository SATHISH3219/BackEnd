from flask import Flask, request, jsonify, send_file, redirect, url_for
from flask_cors import CORS
import subprocess
import os

app = Flask(__name__)
CORS(app, origins=["*"], methods=['OPTIONS', 'GET', 'POST'])

VIDEO_OUTPUT = "streamed_video.mp4"
COOKIES_FILE = os.getenv("COOKIES_FILE", "cookies.txt")

@app.route('/')
def home():
    if os.path.exists(VIDEO_OUTPUT):
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
    data = request.get_json()
    video_url = data.get("video_url")
    if not video_url:
        return jsonify({"error": "Please provide a valid video URL."}), 400

    # Start streaming
    return redirect(url_for('start_streaming', video_url=video_url))


@app.route('/start-streaming', methods=['POST'])
def start_streaming():
    # Retrieve video_url from the request JSON
    data = request.get_json()
    video_url = data.get("video_url")
    
    if not video_url:
        return jsonify({"error": "Missing video_url"}), 400

    if not os.path.exists(COOKIES_FILE):
        return jsonify({"error": f"Cookies file not found at {COOKIES_FILE}"}), 500

    try:
        yt_dlp_command = [
            "python", "-m", "yt_dlp", "--cookies", COOKIES_FILE, "-o", "-", video_url
        ]
        ffmpeg_command = [
            "ffmpeg", "-i", "-", "-c:v", "libx264", "-preset", "fast", "-movflags", "frag_keyframe+empty_moov",
            "-f", "mp4", VIDEO_OUTPUT
        ]

        yt_dlp_process = subprocess.Popen(yt_dlp_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        ffmpeg_process = subprocess.Popen(ffmpeg_command, stdin=yt_dlp_process.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        yt_dlp_process.stdout.close()
        ffmpeg_stdout, ffmpeg_stderr = ffmpeg_process.communicate()

        if yt_dlp_process.returncode != 0:
            yt_dlp_stderr = yt_dlp_process.stderr.read().decode()
            return jsonify({"error": f"yt-dlp error: {yt_dlp_stderr}"}), 500

        if ffmpeg_process.returncode != 0:
            ffmpeg_stderr = ffmpeg_process.stderr.read().decode()
            return jsonify({"error": f"ffmpeg error: {ffmpeg_stderr}"}), 500

        return jsonify({"message": "Video streaming started successfully."}), 200

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
