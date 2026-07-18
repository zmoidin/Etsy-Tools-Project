import os
import shutil
import time
import threading
import webbrowser
from flask import Flask, request, render_template, jsonify, send_file
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

@app.route('/api/image-resizer', methods=['POST'])
def image_resizer():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
        
    widths_raw = request.form.getlist('widths[]')
    heights_raw = request.form.getlist('heights[]')
    
    if not widths_raw or not heights_raw or len(widths_raw) != len(heights_raw):
        return jsonify({'error': 'Invalid dimensions specified'}), 400
        
    try:
        sizes = []
        for w, h in zip(widths_raw, heights_raw):
            sizes.append((int(w), int(h)))
    except ValueError:
        return jsonify({'error': 'Dimensions must be integers'}), 400
        
    session_dir = cleanup_and_get_session_dir()
    input_path = os.path.join(session_dir, os.path.basename(file.filename))
    file.save(input_path)
    
    base_name = os.path.splitext(os.path.basename(file.filename))[0]
    zip_filename = f"{base_name}_resized.zip"
    zip_path = os.path.join(session_dir, zip_filename)
    
    try:
        processor.resize_image_multiple_sizes(input_path, sizes, zip_path)
        
        # Open directory for local users
        if os.path.exists(session_dir):
            os.startfile(session_dir)
            
        return send_file(zip_path, as_attachment=True, download_name=zip_filename)
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

@app.route('/api/bulk-renamer', methods=['POST'])
def bulk_renamer():
    data = request.get_json() or request.form
    folder_path = data.get('folder_path')
    base_text = data.get('base_text')
    
    if not folder_path or not base_text:
        return jsonify({'error': 'Folder path and base text are both required.'}), 400
        
    folder_path = os.path.abspath(folder_path.strip())
    base_text = base_text.strip()
    
    try:
        count = processor.bulk_rename_files(folder_path, base_text)
        if os.path.exists(folder_path):
            os.startfile(folder_path)
        return jsonify({'success': True, 'message': f'Successfully renamed {count} files!'})
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
