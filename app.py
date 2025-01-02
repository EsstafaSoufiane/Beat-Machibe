from flask import Flask, render_template, request, jsonify, send_file, after_this_request
import os
from werkzeug.utils import secure_filename
from beatmachine import Beats
import tempfile
from pydub import AudioSegment

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
    if 'file' not in request.files:
        return 'No file uploaded', 400
    
    file = request.files['file']
    if not file.filename:
        return 'No file selected', 400
    
    filename = secure_filename(file.filename)
    input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    try:
        file.save(input_path)
        
        # Process the audio
        beats = Beats.from_song(input_path)
        pattern = request.form.get('pattern', '1234')
        output_path = remix_audio(beats, pattern, input_path)
        
        # Clean up input file after processing
        try:
            os.remove(input_path)
        except:
            pass
            
        # Send file and clean up
        @after_this_request
        def cleanup(response):
            try:
                os.remove(output_path)
            except:
                pass
            return response
            
        return send_file(output_path, as_attachment=True, download_name=f'remixed_{filename}')
        
    except Exception as e:
        # Clean up in case of error
        try:
            os.remove(input_path)
        except:
            pass
        return str(e), 500

def remix_audio(beats, pattern, input_path):
    speed = float(request.form.get('speed', 1.0))
    
    # Create effects based on pattern and speed
    effects = []
    
    # Create a mapping array that preserves the pattern
    # For example, if pattern is [1, 0, 1, 0], we want to keep beats 0 and 2
    # To do this with RemapBeats, we create a mapping that repeats beat 0 when we want a beat
    # and repeats the last silent beat when we want silence
    if any(val == '1' for val in pattern):  # Only apply if we have any beats to keep
        from beatmachine.effects import RemapBeats
        # Find first beat position (will be used for all beats)
        beat_pos = pattern.index('1')
        # Find last silent position (will be used for all silences)
        silence_pos = (len(pattern) - 1) - pattern[::-1].index('0') if '0' in pattern else 0
        
        # Create mapping array
        mapping = []
        for i, val in enumerate(pattern):
            if val == '1':
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
    beats.save(output_path)
    
    return output_path

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
