from flask import Flask, render_template, request, jsonify, send_file
import os
from werkzeug.utils import secure_filename
from beatmachine import Beats
import tempfile
from pydub import AudioSegment
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max file size
app.config['TEMPLATES_AUTO_RELOAD'] = True
extra_files = [
    os.path.join(os.path.dirname(__file__), 'templates'),
    __file__
]

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

ALLOWED_EXTENSIONS = {'mp3', 'wav'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        return jsonify({'filename': filename}), 200
    
    return jsonify({'error': 'Invalid file type'}), 400

@app.route('/remix', methods=['POST'])
def remix_audio():
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No JSON data received'}), 400
            
        filename = data.get('filename')
        if not filename:
            return jsonify({'error': 'No filename provided'}), 400
            
        pattern = data.get('pattern', [1, 0, 1, 0])  # Default pattern
        speed = float(data.get('speed', 1.0))
        
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if not os.path.exists(input_path):
            return jsonify({'error': 'Input file not found'}), 404
        
        # Create a Beats object from the song
        beats = Beats.from_song(input_path)
        
        # Create effects based on pattern and speed
        effects = []
        
        # Create a mapping array that preserves the pattern
        if any(val == 1 for val in pattern):  # Only apply if we have any beats to keep
            from beatmachine.effects import RemapBeats
            # Find first beat position (will be used for all beats)
            beat_pos = pattern.index(1)
            # Find last silent position (will be used for all silences)
            silence_pos = (len(pattern) - 1) - pattern[::-1].index(0) if 0 in pattern else 0
            
            # Create mapping array
            mapping = []
            for i, val in enumerate(pattern):
                if val == 1:
                    mapping.append(beat_pos)  # Use the first beat position
                else:
                    mapping.append(silence_pos)  # Use the silent position
                    
            effects.append(RemapBeats(mapping=mapping))
        
        # Apply all effects
        if effects:
            beats = beats.apply_all(*effects)
        
        # Export to temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
        output_path = temp_file.name
        temp_file.close()  # Close the file before writing to it
        
        try:
            beats.save(output_path)
            response = send_file(output_path, as_attachment=True, download_name=f'remixed_{filename}')
            return response
        finally:
            # Clean up the temporary file after sending
            if os.path.exists(output_path):
                try:
                    os.unlink(output_path)
                except:
                    pass  # Ignore cleanup errors
                    
    except Exception as e:
        app.logger.error(f"Error in remix_audio: {str(e)}")
        return jsonify({'error': f'Remix failed: {str(e)}'}), 500

if __name__ == '__main__':
    # Use environment variable for port, defaulting to 5000
    port = int(os.environ.get('PORT', 5000))
    # In production, disable debug mode and bind to all interfaces
    app.run(host='0.0.0.0', port=port, debug=False)
