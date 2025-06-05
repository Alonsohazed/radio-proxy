import os
import logging
from flask import Flask, Response, render_template, request
from flask_cors import CORS
import requests
# Configure logging for debugging
logging.basicConfig(level=logging.DEBUG)
# Create the Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "radio-proxy-secret-key")
# Enable CORS for cross-origin requests
CORS(app)
# Radio stream URL
RADIO_STREAM_URL = 'http://192.99.41.102:6902/stream?type=http'
@app.route('/')
def index():
    """Main page with radio player interface"""
    return render_template('index.html')
@app.route('/test')
def test():
    """Test page for audio streaming"""
    return render_template('test.html')
@app.route('/stream')
def stream():
    """Proxy endpoint for radio stream"""
    try:
        app.logger.info(f"Starting stream from: {RADIO_STREAM_URL}")
        
        def generate():
            try:
                # Request the radio stream with streaming enabled
                with requests.get(RADIO_STREAM_URL, stream=True, timeout=30) as response:
                    response.raise_for_status()
                    app.logger.info(f"Connected to radio stream. Status: {response.status_code}")
                    
                    # Stream the audio data in chunks
                    for chunk in response.iter_content(chunk_size=1024):
                        if chunk:
                            yield chunk
                            
            except requests.exceptions.RequestException as e:
                app.logger.error(f"Stream error: {str(e)}")
                yield b''
            except Exception as e:
                app.logger.error(f"Unexpected error: {str(e)}")
                yield b''
        
        return Response(
            generate(),
            content_type='audio/mpeg',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'Transfer-Encoding': 'chunked',  # <- clave para streaming real
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET',
                'Access-Control-Allow-Headers': 'Content-Type'
    }
)
        
    except Exception as e:
        app.logger.error(f"Failed to start stream: {str(e)}")
        return Response(
            "Stream temporarily unavailable",
            status=503,
            content_type='text/plain'
        )
@app.route('/health')
def health():
    """Health check endpoint"""
    try:
        response = requests.head(RADIO_STREAM_URL, timeout=5)
        if response.status_code == 200:
            return {"status": "healthy", "stream": "available"}, 200
        else:
            return {"status": "degraded", "stream": "unavailable"}, 503
    except Exception as e:
        app.logger.error(f"Health check failed: {str(e)}")
        return {"status": "unhealthy", "error": str(e)}, 503
@app.errorhandler(404)
def not_found(error):
    return render_template('index.html'), 404
@app.errorhandler(500)
def internal_error(error):
    app.logger.error(f"Internal server error: {str(error)}")
    return "Internal server error", 500
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
