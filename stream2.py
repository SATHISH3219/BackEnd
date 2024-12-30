import os

def start_streaming(video_url, rtmp_server_url):
    """
    Starts streaming using yt-dlp and ffmpeg.

    Parameters:
        video_url (str): The URL of the video to stream.
        rtmp_server_url (str): The RTMP server URL to stream to.
    """
    # Command to use yt-dlp to fetch video and pipe it to ffmpeg for RTMP streaming
    command = f"yt-dlp -o - \"{video_url}\" | ffmpeg -re -i - -c:v copy -f flv \"{rtmp_server_url}\""

    print(f"Executing command: {command}")

    # Execute the command
    result = os.system(command)

    if result != 0:
        print("Error occurred during streaming. Ensure the video URL is supported and your RTMP server is running.")
    else:
        print("Streaming started successfully!")

def main():
    # Get the video URL from the user
    video_url = input("Enter the video URL to stream (YouTube, Twitch, etc.): ")

    # Get the RTMP server URL from the user
    rtmp_server_url = input("Enter the RTMP server URL (e.g., rtmp://localhost/live/stream_key): ")

    # Start streaming
    start_streaming(video_url, rtmp_server_url)

if __name__ == "__main__":
    main()
