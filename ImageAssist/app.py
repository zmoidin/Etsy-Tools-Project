import os
import shutil
import time
import threading
import webbrowser
from flask import Flask, request, render_template, jsonify
from flask_cors import CORS
import processor

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'WebUploads')
processor.ensure_dir(UPLOAD_FOLDER)

def cleanup_and_get_session_dir():
    session_id = str(int(time.time()))
    session_dir = os.path.join(UPLOAD_FOLDER, session_id)
    processor.ensure_dir(session_dir)
    return session_dir

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/auto-process', methods=['POST'])
def auto_process():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    bg_type = request.form.get('bg_type', 'transparent')
    canvas_color = request.form.get('canvas_color', 'transparent')

    session_dir = cleanup_and_get_session_dir()
    input_path = os.path.join(session_dir, os.path.basename(file.filename))
    file.save(input_path)
    
    try:
        processor.auto_process_sheet(input_path, bg_type=bg_type, canvas_color=canvas_color)
        output_dir = os.path.join(session_dir, "Split")
        if os.path.exists(output_dir):
            os.startfile(output_dir)
        return jsonify({'success': True, 'message': 'Processing complete!'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/mockup-showcase', methods=['POST'])
def mockup_showcase():
    if 'files[]' not in request.files:
        return jsonify({'error': 'No clipart files uploaded'}), 400
        
    files = request.files.getlist('files[]')
    bg_file = request.files.get('background')
    
    session_dir = cleanup_and_get_session_dir()
    clipart_dir = os.path.join(session_dir, 'Clipart')
    processor.ensure_dir(clipart_dir)
    
    for f in files:
        if f.filename:
            f.save(os.path.join(clipart_dir, os.path.basename(f.filename)))
            
    bg_path = None
    if bg_file and bg_file.filename:
        bg_path = os.path.join(session_dir, os.path.basename(bg_file.filename))
        bg_file.save(bg_path)
        
    try:
        processor.create_showcase_mockup(clipart_dir, bg_path)
        os.startfile(clipart_dir)
        return jsonify({'success': True, 'message': 'Mockup created!'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/format-clipart', methods=['POST'])
def format_clipart():
    if 'files[]' not in request.files:
        return jsonify({'error': 'No files uploaded'}), 400
        
    files = request.files.getlist('files[]')
    session_dir = cleanup_and_get_session_dir()
    
    for f in files:
        if f.filename:
            f.save(os.path.join(session_dir, os.path.basename(f.filename)))
            
    try:
        processor.format_clipart_batch(session_dir)
        results_dir = os.path.join(session_dir, "Results")
        if os.path.exists(results_dir):
            os.startfile(results_dir)
        return jsonify({'success': True, 'message': 'Formatting complete!'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("\n" + "="*60)
    print("✨ ImageAssist Web Server Started Successfully!")
    print("🌐 Automatically opening your web browser...")
    print("👉 If it doesn't open automatically, click this link:")
    print("   http://127.0.0.1:5000")
    print("="*60 + "\n")
    
    threading.Timer(1.25, lambda: webbrowser.open("http://127.0.0.1:5000")).start()
    app.run(debug=True, use_reloader=True)
