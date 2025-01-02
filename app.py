from flask import Flask, render_template, request, jsonify, send_file, after_this_request
import os
from werkzeug.utils import secure_filename
from beatmachine import Beats
import tempfile
import logging
from logging.handlers import RotatingFileHandler
from pydub import AudioSegment

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
handler = RotatingFileHandler('app.log', maxBytes=10000, backupCount=1)
handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s '
    '[in %(pathname)s:%(lineno)d]'
))
logger.addHandler(handler)

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
    logger.info('Received remix request')
    try:
        if 'file' not in request.files:
            logger.error('No file in request')
            return 'No file uploaded', 400
        
        file = request.files['file']
        if not file.filename:
            logger.error('No filename in request')
            return 'No file selected', 400
        
        filename = secure_filename(file.filename)
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        try:
            logger.info(f'Saving file: {filename}')
            file.save(input_path)
            
            # Process the audio
            logger.info('Processing audio file')
            beats = Beats.from_song(input_path)
            pattern = request.form.get('pattern', '1234')
            logger.info(f'Using pattern: {pattern}')
            output_path = remix_audio(beats, pattern, input_path)
            
            # Clean up input file after processing
            try:
                os.remove(input_path)
            except Exception as e:
                logger.warning(f'Failed to remove input file: {e}')
                
            # Send file and clean up
            @after_this_request
            def cleanup(response):
                try:
                    os.remove(output_path)
                except Exception as e:
                    logger.warning(f'Failed to remove output file: {e}')
                return response
                
            logger.info('Sending remixed file')
            return send_file(output_path, as_attachment=True, download_name=f'remixed_{filename}')
            
        except Exception as e:
            logger.error(f'Error processing audio: {e}')
            # Clean up in case of error
            try:
                os.remove(input_path)
            except:
                pass
            return str(e), 500
    except Exception as e:
        logger.error(f'Unexpected error: {e}')
        return str(e), 500

def remix_audio(beats, pattern, input_path):
    try:
        speed = float(request.form.get('speed', 1.0))
        logger.info(f'Remixing with speed: {speed}')
        
        # Create effects based on pattern and speed
        effects = []
        
        if any(val == '1' for val in pattern):
            from beatmachine.effects import RemapBeats
            beat_pos = pattern.index('1')
            silence_pos = (len(pattern) - 1) - pattern[::-1].index('0') if '0' in pattern else 0
            
            mapping = []
            for val in pattern:
                if val == '1':
                    mapping.append(beat_pos)
                else:
                    mapping.append(silence_pos)
            
            effects.append(RemapBeats(mapping))
        
        # Apply effects
        for effect in effects:
            beats = effect.apply(beats)
        
        # Save to temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
        output_path = temp_file.name
        beats.save(output_path)
        
        return output_path
    except Exception as e:
        logger.error(f'Error in remix_audio: {e}')
        raise

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
