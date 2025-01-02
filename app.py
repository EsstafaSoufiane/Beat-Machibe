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

# Ensure upload directory exists and is writable
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max file size
app.config['TEMPLATES_AUTO_RELOAD'] = True
extra_files = [
    os.path.join(os.path.dirname(__file__), 'templates'),
    __file__
]

ALLOWED_EXTENSIONS = {'mp3', 'wav'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        app.logger.info("Starting file upload")
        if 'file' not in request.files:
            app.logger.error("No file part in request")
            return jsonify({'error': 'No file part'}), 400
        
        file = request.files['file']
        if file.filename == '':
            app.logger.error("No selected file")
            return jsonify({'error': 'No selected file'}), 400
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            app.logger.info(f"Saving file to {filepath}")
            file.save(filepath)
            app.logger.info(f"File saved successfully: {filename}")
            return jsonify({'filename': filename}), 200
        
        app.logger.error(f"Invalid file type: {file.filename}")
        return jsonify({'error': 'Invalid file type'}), 400
    except Exception as e:
        app.logger.error(f"Error in upload_file: {str(e)}")
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500

@app.route('/remix', methods=['POST'])
def remix_audio():
    try:
        app.logger.info("Starting remix process")
        data = request.json
        if not data:
            app.logger.error("No JSON data received")
            return jsonify({'error': 'No JSON data received'}), 400
            
        filename = data.get('filename')
        if not filename:
            app.logger.error("No filename provided")
            return jsonify({'error': 'No filename provided'}), 400
            
        pattern = data.get('pattern', [1, 0, 1, 0])  # Default pattern
        speed = float(data.get('speed', 1.0))
        
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        app.logger.info(f"Input file path: {input_path}")
        
        if not os.path.exists(input_path):
            app.logger.error(f"Input file not found: {input_path}")
            return jsonify({'error': 'Input file not found'}), 404
        
        app.logger.info("Creating Beats object")
        beats = Beats.from_song(input_path)
        
        effects = []
        if any(val == 1 for val in pattern):
            app.logger.info(f"Creating RemapBeats effect with pattern: {pattern}")
            from beatmachine.effects import RemapBeats
            beat_pos = pattern.index(1)
            silence_pos = (len(pattern) - 1) - pattern[::-1].index(0) if 0 in pattern else 0
            
            mapping = []
            for i, val in enumerate(pattern):
                if val == 1:
                    mapping.append(beat_pos)
                else:
                    mapping.append(silence_pos)
            
            app.logger.info(f"Created mapping: {mapping}")
            effects.append(RemapBeats(mapping=mapping))
        
        if effects:
            app.logger.info("Applying effects")
            beats = beats.apply_all(*effects)
        
        app.logger.info("Creating temporary file for output")
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
        output_path = temp_file.name
        temp_file.close()
        
        try:
            app.logger.info(f"Saving remixed audio to {output_path}")
            beats.save(output_path)
            app.logger.info("Audio saved successfully")
            response = send_file(output_path, as_attachment=True, download_name=f'remixed_{filename}')
            app.logger.info("Sending response")
            return response
        finally:
            if os.path.exists(output_path):
                try:
                    os.unlink(output_path)
                    app.logger.info("Temporary file cleaned up")
                except Exception as e:
                    app.logger.warning(f"Failed to clean up temporary file: {str(e)}")
                    
    except Exception as e:
        app.logger.error(f"Error in remix_audio: {str(e)}")
        return jsonify({'error': f'Remix failed: {str(e)}'}), 500

if __name__ == '__main__':
    # Use environment variable for port, defaulting to 5000
    port = int(os.environ.get('PORT', 5000))
    # In production, disable debug mode and bind to all interfaces
    app.run(host='0.0.0.0', port=port, debug=False)
