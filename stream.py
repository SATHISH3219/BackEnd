from flask import Flask, request, jsonify, send_from_directory
import os
import subprocess
import tempfile

app = Flask(__name__)

# Global variable to store the HLS streaming process
streaming_process = None
temp_dir = tempfile.mkdtemp()  # Temporary directory to store HLS files

@app.route('/start-streaming', methods=['POST'])
def start_streaming():
    global streaming_process
    data = request.json
    video_url = data.get("video_url")

    if not video_url:
        return jsonify({"error": "Missing video_url"}), 400

    try:
        # Run the ffmpeg command to convert video to HLS
        command = f"yt-dlp -o - \"{video_url}\" | ffmpeg -i - -c:v libx264 -hls_time 10 -hls_list_size 0 -f hls {temp_dir}/output.m3u8"
        print(f"Executing command: {command}")

        # Start the streaming process
        streaming_process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return jsonify({"message": "HLS streaming started successfully!"})

    except Exception as e:
        return jsonify({"error": f"Error occurred during streaming: {str(e)}"}), 500

@app.route('/stop-streaming', methods=['POST'])
def stop_streaming():
    global streaming_process

    if streaming_process is None:
        return jsonify({"error": "No active streaming process found"}), 400

    try:
        # Attempt to terminate or kill the process
        streaming_process.terminate()  # Try gracefully terminating
        streaming_process.wait()  # Wait for process to terminate

        if streaming_process.returncode != 0:
            # If the process hasn't ended successfully, force kill it
            print(f"Process didn't terminate gracefully, killing it.")
            streaming_process.kill()

        # Reset the streaming process reference
        streaming_process = None
        return jsonify({"message": "Streaming stopped successfully!"})

    except Exception as e:
        return jsonify({"error": f"Error occurred while stopping the stream: {str(e)}"}), 500

@app.route('/hls/<path:filename>')
def serve_hls(filename):
    # Serve HLS playlist and video segments
    hls_path = os.path.join(temp_dir, filename)
    if os.path.exists(hls_path):
        return send_from_directory(temp_dir, filename)
    return jsonify({"error": "File not found"}), 404

port = int(os.environ.get("PORT", 9000))
app.run(host="0.0.0.0", port=port)
