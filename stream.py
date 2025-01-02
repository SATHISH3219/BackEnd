from flask import Flask, request, jsonify, send_file, render_template_string, redirect, url_for
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
        video_embed_html = f"""
        <!DOCTYPE html>
        <html>
        <head><title>Video Streaming</title></head>
        <body>
            <h1>Video is Ready for Streaming</h1>
            <video width="640" height="360" controls>
                <source src="/video" type="video/mp4">
                Your browser does not support the video tag.
            </video>
            <p><a href="/stream">Developer: Stream Another Video</a></p>
        </body>
        </html>
        """
        return render_template_string(video_embed_html)
    return jsonify({"message": "Welcome to the Video Service! No video is currently available for streaming."})


@app.route('/stream', methods=['GET', 'POST'])
def developer_stream():
    if request.method == 'POST':
        video_url = request.form.get("video_url")
        if not video_url:
            return render_template_string("""
            <!DOCTYPE html>
            <html>
            <head><title>Developer Stream</title></head>
            <body>
                <h1>Stream a Video</h1>
                <form method="post" action="/stream">
                    <label for="video_url">Video URL:</label>
                    <input type="text" id="video_url" name="video_url" required>
                    <button type="submit">Start Streaming</button>
                </form>
                <p style="color:red;">Please provide a valid video URL.</p>
            </body>
            </html>
            """)
        # Start streaming
        return redirect(url_for('start_streaming', video_url=video_url))

    # Render developer page
    developer_page_html = """
    <!DOCTYPE html>
    <html>
    <head><title>Developer Stream</title></head>
    <body>
        <h1>Stream a Video</h1>
        <form method="post" action="/stream">
            <label for="video_url">Video URL:</label>
            <input type="text" id="video_url" name="video_url" required>
            <button type="submit">Start Streaming</button>
        </form>
    </body>
    </html>
    """
    return render_template_string(developer_page_html)


@app.route('/start-streaming', methods=['POST'])
def start_streaming():
    data = request.json or {}
    video_url = data.get("video_url") or request.args.get("video_url")

    if not video_url:
        return jsonify({"error": "Missing video_url"}), 400

    if not os.path.exists(COOKIES_FILE):
        return jsonify({"error": f"Cookies file not found at {COOKIES_FILE}"}), 500

    try:
        # Download and convert video using yt-dlp and ffmpeg
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
    app.run(host='0.0.0.0', port=5000, debug=True)
