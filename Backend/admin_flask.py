import tempfile
from flask import Flask, request, jsonify
import os
from flask_cors import CORS
from werkzeug.utils import secure_filename
from admin_upload import process_pdf
app = Flask(__name__)
CORS(app)
# Set up allowed extensions
ALLOWED_EXTENSIONS = {'pdf'}
OUTPUT_FOLDER = 'data'

# Utility function to check allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload', methods=['POST'])
def upload_pdf():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        
        # Create a temporary directory to store the uploaded file
        with tempfile.TemporaryDirectory() as tempdir:
            file_path = os.path.join(tempdir, filename)
            file.save(file_path)  # Save the uploaded file in the temporary directory

            # Process the uploaded PDF (you can call your processing function here)
            output_file = process_pdf(file_path, OUTPUT_FOLDER)
        
        # After the 'with' block, the temporary directory and its contents are automatically deleted
        return jsonify({"message": "File processed successfully", "output_file": output_file}), 200
    else:
        return jsonify({"error": "Invalid file format. Only PDFs are allowed."}), 400

if __name__ == '__main__':
    app.run(host="0.0.0.0",port=5000,debug=True)
