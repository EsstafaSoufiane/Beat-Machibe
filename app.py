from flask import Flask, render_template, request, send_file, Response
import os
from werkzeug.utils import secure_filename
from beatmachine import Beats
import tempfile
import logging
import gc
import numpy as np
from pathlib import Path
import shutil
import threading
from queue import Queue, Empty
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
MAX_FILE_SIZE = 8 * 1024 * 1024  # 8MB max file size
CHUNK_SIZE = 512 * 1024  # 512KB chunks
UPLOAD_FOLDER = Path('uploads')
TEMP_FOLDER = Path('temp')

# Create directories
UPLOAD_FOLDER.mkdir(exist_ok=True)
TEMP_FOLDER.mkdir(exist_ok=True)

# Global processing queue
processing_queue = Queue(maxsize=2)
current_jobs = {}

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

def cleanup_old_files():
    """Clean up files older than 5 minutes"""
    try:
        for folder in [UPLOAD_FOLDER, TEMP_FOLDER]:
            for file in folder.glob('*'):
                if file.is_file() and (time.time() - file.stat().st_mtime > 300):
                    try:
                        file.unlink()
                    except:
                        pass
    except Exception as e:
        logger.error(f"Cleanup error: {e}")

def process_beats(input_path, output_path, pattern):
    """Process beats in small chunks"""
    try:
        beats = Beats.from_song(str(input_path))
        from beatmachine.effects import RemapBeats
        
        # Create simple mapping
        mapping = [i % len(pattern) for i in range(len(beats))]
        effect = RemapBeats(mapping)
        
        # Process in small chunks
        chunk_size = 500  # Process 500 beats at a time
        total_beats = len(beats)
        
        # Create temporary file for processing
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
            temp_path = Path(temp_file.name)
            
            for i in range(0, total_beats, chunk_size):
                chunk = beats[i:min(i + chunk_size, total_beats)]
                processed_chunk = effect.apply(chunk)
                processed_chunk.save(str(temp_path), append=(i > 0))
                del processed_chunk
                del chunk
                gc.collect()
            
            # Move completed file to output location
            shutil.move(str(temp_path), output_path)
        
        return True
    except Exception as e:
        logger.error(f"Processing error: {e}")
        return False
    finally:
        gc.collect()

def worker():
    while True:
        try:
            input_path, output_path, pattern = processing_queue.get(timeout=1)
        except Empty:
            continue
        
        success = process_beats(input_path, output_path, pattern)
        
        if not success:
            logger.error("Error processing audio")
        
        processing_queue.task_done()

# Start worker thread
thread = threading.Thread(target=worker)
thread.daemon = True
thread.start()

@app.route('/')
def index():
    cleanup_old_files()
    return render_template('index.html')

@app.route('/remix', methods=['POST'])
def remix_audio():
    cleanup_old_files()
    
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
        output_path = TEMP_FOLDER / f"remixed_{filename}"
        
        # Save file
        file.save(input_path)
        
        # Get pattern
        pattern = request.form.get('pattern', '1234')
        
        # Add to processing queue
        processing_queue.put((input_path, output_path, pattern))
        
        # Wait for processing to complete
        processing_queue.join()
        
        # Stream processed file
        def generate():
            try:
                with open(output_path, 'rb') as f:
                    while True:
                        chunk = f.read(CHUNK_SIZE)
                        if not chunk:
                            break
                        yield chunk
            finally:
                # Cleanup after streaming
                try:
                    input_path.unlink(missing_ok=True)
                    output_path.unlink(missing_ok=True)
                except:
                    pass
        
        response = Response(
            generate(),
            mimetype='audio/wav',
            headers={'Content-Disposition': f'attachment; filename=remixed_{filename}'}
        )
        return response
        
    except Exception as e:
        logger.error(f"Error: {e}")
        # Cleanup on error
        try:
            input_path.unlink(missing_ok=True)
            output_path.unlink(missing_ok=True)
        except:
            pass
        return f'Server error: {str(e)}', 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
