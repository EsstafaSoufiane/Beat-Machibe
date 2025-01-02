from flask import Flask, render_template, request, jsonify, send_file
import os
from werkzeug.utils import secure_filename
from beatmachine import Beats
import tempfile
from pydub import AudioSegment
import logging
import sys
import gc
import resource
import numpy as np
from pydub.utils import make_chunks

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

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'mp3', 'wav'}

def process_audio_in_chunks(input_path, pattern):
    """Process audio file in chunks to reduce memory usage."""
    try:
        app.logger.info("Loading audio file in chunks")
        audio = AudioSegment.from_file(input_path)
        
        # Create temporary files for processing
        temp_input = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
        temp_output = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
        temp_files = [temp_input.name, temp_output.name]
        
        try:
            # Export to WAV for processing
            audio.export(temp_input.name, format='wav')
            del audio
            gc.collect()
            
            app.logger.info("Creating Beats object")
            beats = Beats.from_song(temp_input.name)
            
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
                beats = beats.apply_all(RemapBeats(mapping=mapping))
            
            app.logger.info("Saving processed audio")
            beats.save(temp_output.name)
            
            return temp_output.name, temp_files
            
        except Exception as e:
            # Clean up temporary files in case of error
            for temp_file in temp_files:
                if os.path.exists(temp_file):
                    try:
                        os.unlink(temp_file)
                    except:
                        pass
            raise e
            
    except Exception as e:
        app.logger.error(f"Error processing audio: {str(e)}")
        raise e

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
    temp_files = []
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
            
        pattern = data.get('pattern', [1, 0, 1, 0])
        speed = float(data.get('speed', 1.0))
        
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        app.logger.info(f"Input file path: {input_path}")
        
        if not os.path.exists(input_path):
            app.logger.error(f"Input file not found: {input_path}")
            return jsonify({'error': 'Input file not found'}), 404

        # Process audio in chunks
        output_path, temp_files = process_audio_in_chunks(input_path, pattern)
        
        app.logger.info("Sending response")
        return send_file(output_path, as_attachment=True, download_name=f'remixed_{filename}')
        
    except MemoryError:
        app.logger.error("Memory limit exceeded during processing")
        return jsonify({'error': 'Memory limit exceeded during processing'}), 507
        
    except Exception as e:
        app.logger.error(f"Error in remix_audio: {str(e)}")
        return jsonify({'error': f'Remix failed: {str(e)}'}), 500
        
    finally:
        # Clean up temporary files
        for temp_file in temp_files:
            if os.path.exists(temp_file):
                try:
                    os.unlink(temp_file)
                    app.logger.info(f"Cleaned up temporary file: {temp_file}")
                except Exception as e:
                    app.logger.warning(f"Failed to clean up temporary file {temp_file}: {str(e)}")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    from gunicorn.app.base import BaseApplication

    class StandaloneApplication(BaseApplication):
        def __init__(self, app, options=None):
            self.options = options or {}
            self.application = app
            super().__init__()

        def load_config(self):
            for key, value in self.options.items():
                self.cfg.set(key, value)

        def load(self):
            return self.application

    options = {
        'bind': f'0.0.0.0:{port}',
        'workers': 1,
        'timeout': 300,
        'worker_class': 'sync',
        'max_requests': 1,
        'max_requests_jitter': 0,
        'preload_app': False,
    }

    StandaloneApplication(app, options).run()
else:
    application = app
