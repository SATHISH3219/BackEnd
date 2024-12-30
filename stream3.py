from flask import Flask, request, jsonify
import subprocess
import threading
import os

app = Flask(__name__)

# Store the streaming process globally
streaming_process = None


def log_output(process, label):
    """Logs the output and errors from a subprocess."""
    def read_stream(stream, log_type):
        for line in iter(stream.readline, b''):
            print(f"[{label} {log_type}]: {line.decode().strip()}")

    threading.Thread(target=read_stream, args=(process.stdout, "stdout"), daemon=True).start()
    threading.Thread(target=read_stream, args=(process.stderr, "stderr"), daemon=True).start()


@app.route('/start-streaming', methods=['POST'])
def start_streaming():
    global streaming_process

    data = request.json
    video_url = data.get("video_url")
    output_url = data.get("output_url", "rtmp://127.0.0.1:1935/live/test")

    if not video_url:
        return jsonify({"error": "Missing video_url"}), 400

    if streaming_process and streaming_process.poll() is None:
        return jsonify({"error": "Streaming is already running."}), 400

    try:
        # Build and execute the command for yt-dlp and ffmpeg
        yt_dlp_command = [
            "python", "-m", "yt_dlp", "-o", "-", video_url
        ]
        ffmpeg_command = [
            "ffmpeg", "-re", "-i", "-", "-c:v", "copy", "-f", "flv", output_url
        ]

        print(f"Starting yt-dlp: {' '.join(yt_dlp_command)}")
        print(f"Starting ffmpeg: {' '.join(ffmpeg_command)}")

        # Start yt-dlp process
        yt_dlp_process = subprocess.Popen(
            yt_dlp_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

        # Start ffmpeg process with the yt-dlp output piped to it
        streaming_process = subprocess.Popen(
            ffmpeg_command, stdin=yt_dlp_process.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        yt_dlp_process.stdout.close()  # Allow yt-dlp to receive a SIGPIPE if ffmpeg closes

        # Log outputs from both processes
        log_output(yt_dlp_process, "yt-dlp")
        log_output(streaming_process, "ffmpeg")

        return jsonify({"message": "Streaming started successfully!", "output_url": output_url}), 200

    except Exception as e:
        return jsonify({"error": f"Failed to start streaming: {str(e)}"}), 500


@app.route('/stop-streaming', methods=['POST'])
def stop_streaming():
    global streaming_process

    if not streaming_process or streaming_process.poll() is not None:
        return jsonify({"error": "No active streaming process found."}), 400

    try:
        # Terminate the streaming process and its children
        print("Stopping streaming process...")
        streaming_process.terminate()  # Terminate the process
        streaming_process.wait()  # Ensure that we wait for the process to end
        streaming_process = None
        return jsonify({"message": "Streaming stopped successfully!"}), 200

    except Exception as e:
        return jsonify({"error": f"Failed to stop streaming: {str(e)}"}), 500


@app.route('/health-check', methods=['GET'])
def health_check():
    return jsonify({"status": "Server is running"}), 200


if __name__ == '__main__':
    # Use the port from the environment variable (for Render deployment)
    port = int(os.environ.get("PORT", 5000))
    # Run the app on all available IPs (0.0.0.0) for cloud deployments
    app.run(host='0.0.0.0', port=port)
