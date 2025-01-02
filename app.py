from flask import Flask, render_template, request, send_file
import os
from werkzeug.utils import secure_filename
from beatmachine import Beats
import tempfile
import logging
from logging.handlers import RotatingFileHandler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Limit to 16MB

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/remix', methods=['POST'])
def remix_audio():
    try:
        if 'file' not in request.files:
            return 'No file uploaded', 400
        
        file = request.files['file']
        if not file.filename:
            return 'No file selected', 400
        
        if not file.filename.lower().endswith(('.mp3', '.wav')):
            return 'Invalid file type. Please upload MP3 or WAV files only.', 400
        
        filename = secure_filename(file.filename)
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        try:
            file.save(input_path)
            beats = Beats.from_song(input_path)
            pattern = request.form.get('pattern', '1234')
            
            # Simple pattern processing
            from beatmachine.effects import RemapBeats
            mapping = [i % len(pattern) for i in range(len(beats))]
            effect = RemapBeats(mapping)
            beats = effect.apply(beats)
            
            # Save to output file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
            output_path = temp_file.name
            beats.save(output_path)
            
            # Clean up input file
            try:
                os.remove(input_path)
            except:
                pass
            
            return send_file(output_path, as_attachment=True, download_name=f'remixed_{filename}')
            
        except Exception as e:
            logger.error(f'Processing error: {str(e)}')
            try:
                os.remove(input_path)
            except:
                pass
            return f'Error processing audio: {str(e)}', 500
            
    except Exception as e:
        logger.error(f'Server error: {str(e)}')
        return f'Server error: {str(e)}', 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
