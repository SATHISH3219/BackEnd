// frontend/script.js
async function startStream() {
    const videoUrl = document.getElementById('videoUrl').value;
    const response = await fetch('https://your-backend-url.onrender.com/start-stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: videoUrl })
    });
    
    const result = await response.json();
    document.getElementById('status').innerText = result.message || result.error;
}
