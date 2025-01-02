from flask import Flask, render_template, request, send_file, Response, stream_with_context
import os
from werkzeug.utils import secure_filename
from beatmachine import Beats
import tempfile
import logging
import gc
import numpy as np
from pathlib import Path
import shutil

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CHUNK_SIZE = 1024 * 1024  # 1MB chunks
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB max file size
UPLOAD_FOLDER = Path('uploads')
TEMP_FOLDER = Path('temp')

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# Create necessary directories
UPLOAD_FOLDER.mkdir(exist_ok=True)
TEMP_FOLDER.mkdir(exist_ok=True)

def cleanup_temp_files():
    """Clean up temporary files older than 1 hour"""
    try:
        for folder in [UPLOAD_FOLDER, TEMP_FOLDER]:
            for file in folder.glob('*'):
                if file.is_file():
                    try:
                        file.unlink()
                    except:
                        pass
    except Exception as e:
        logger.error(f"Error cleaning up temp files: {e}")

@app.route('/')
def index():
    cleanup_temp_files()
    return render_template('index.html')

def process_audio_chunk(beats, chunk_size=1000):
    """Process audio in chunks to manage memory"""
    total_beats = len(beats)
    for i in range(0, total_beats, chunk_size):
        chunk = beats[i:min(i + chunk_size, total_beats)]
        yield chunk
        gc.collect()

@app.route('/remix', methods=['POST'])
def remix_audio():
    if 'file' not in request.files:
        return 'No file uploaded', 400
    
    file = request.files['file']
    if not file.filename:
        return 'No file selected', 400
    
    if not file.filename.lower().endswith(('.mp3', '.wav')):
        return 'Invalid file type. Please upload MP3 or WAV files only.', 400

    try:
        # Save uploaded file
        filename = secure_filename(file.filename)
        input_path = UPLOAD_FOLDER / filename
        file.save(input_path)

        # Create temporary output file
        output_file = TEMP_FOLDER / f"remixed_{filename}"
        
        try:
            # Process audio in chunks
            beats = Beats.from_song(str(input_path))
            pattern = request.form.get('pattern', '1234')
            
            # Simple pattern processing
            from beatmachine.effects import RemapBeats
            mapping = [int(pattern[i % len(pattern)]) for i in range(len(beats))]
            effect = RemapBeats(mapping)
            
            # Process in chunks
            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
                for chunk in process_audio_chunk(beats):
                    processed_chunk = effect.apply(chunk)
                    processed_chunk.save(temp_file.name, append=True)
                    del processed_chunk
                    gc.collect()
                
                # Move the completed file to output location
                shutil.move(temp_file.name, output_file)
            
            # Stream the file back to client
            def generate():
                with open(output_file, 'rb') as f:
                    while True:
                        chunk = f.read(CHUNK_SIZE)
                        if not chunk:
                            break
                        yield chunk
                
                # Cleanup after streaming
                try:
                    input_path.unlink()
                    output_file.unlink()
                except:
                    pass

            response = Response(stream_with_context(generate()), 
                              mimetype='audio/wav')
            response.headers['Content-Disposition'] = f'attachment; filename=remixed_{filename}'
            return response

        except Exception as e:
            logger.error(f"Processing error: {str(e)}")
            return f'Error processing audio: {str(e)}', 500
            
    except Exception as e:
        logger.error(f"Server error: {str(e)}")
        return f'Server error: {str(e)}', 500
    finally:
        # Cleanup
        try:
            input_path.unlink(missing_ok=True)
            output_file.unlink(missing_ok=True)
        except:
            pass
        gc.collect()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
