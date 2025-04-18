from flask import Flask, request, jsonify, send_from_directory
import os
import fitz  # PyMuPDF
from pdfminer.high_level import extract_text
import subprocess
import tempfile
import logging
from werkzeug.utils import secure_filename

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = 'uploads'
PROCESSED_FOLDER = 'processed'
ALLOWED_EXTENSIONS = {'pdf'}
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size

# Create necessary directories
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Function to extract text using PyMuPDF (fitz)
def extract_text_pymupdf(input_pdf_path):
    """Extracts text from a PDF using PyMuPDF."""
    text = ""
    try:
        doc = fitz.open(input_pdf_path)
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            extracted_text = page.get_text("text")
            if extracted_text:
                text += extracted_text + "\n"
        logger.info(f"Text extracted from: {input_pdf_path}")
    except Exception as e:
        logger.error(f"Failed to extract text from {input_pdf_path}: {e}")
    return text

# Function to extract text using pdfminer
def extract_text_pdfminer(input_pdf_path):
    """Extracts text from a PDF using pdfminer."""
    try:
        text = extract_text(input_pdf_path)
        logger.info(f"Text extracted using pdfminer from: {input_pdf_path}")
        return text
    except Exception as e:
        logger.error(f"Failed to extract text using pdfminer from {input_pdf_path}: {e}")
        return ""

# Function to remove watermarks (if needed)
def remove_watermarks(input_pdf_path, output_pdf_path):
    """Removes watermarks and metadata from the PDF."""
    try:
        pdf = fitz.open(input_pdf_path)
        pdf.save(output_pdf_path)
        logger.info(f"Watermarks removed from: {input_pdf_path}")
    except Exception as e:
        logger.error(f"Failed to remove watermarks from {input_pdf_path}: {e}")

# Function to apply OCR to the PDF if text extraction fails (via OCRmyPDF)
def apply_ocr(input_pdf_path, output_pdf_path):
    """Applies OCR to the PDF using OCRmyPDF."""
    try:
        subprocess.run([
            "ocrmypdf", 
            input_pdf_path, 
            output_pdf_path, 
            "--force-ocr", 
            "--output-type", "pdf"
        ], check=True)
        logger.info(f"OCR applied to: {input_pdf_path}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to apply OCR to {input_pdf_path}: {e}")

# Main processing function
def process_pdf(input_pdf, output_folder):
    """Process the uploaded PDF to remove watermarks, extract, clean text, and apply OCR if needed."""
    
    # Step 1: Create a temporary directory for cleaned PDFs
    with tempfile.TemporaryDirectory() as temp_dir:
        # Generate the path for the cleaned PDF in the temporary directory
        cleaned_pdf = os.path.join(temp_dir, f"cleaned_{os.path.basename(input_pdf)}")
        
        # Step 2: Remove Watermarks
        remove_watermarks(input_pdf, cleaned_pdf)

        # Step 3: Extract and Clean Text using PyMuPDF
        final_text = extract_text_pymupdf(cleaned_pdf)
        if len(final_text.strip()) < 1000:  # If extraction fails or has insufficient text
            logger.info(f"Low content detected in {input_pdf}, applying OCR...")
            ocr_output_pdf = os.path.join(temp_dir, f"ocr_{os.path.basename(input_pdf)}")
            apply_ocr(cleaned_pdf, ocr_output_pdf)
            final_text = extract_text_pymupdf(ocr_output_pdf)

        # Step 4: Use pdfminer for additional extraction if needed
        pdfminer_text = extract_text_pdfminer(cleaned_pdf)
        final_text += "\n" + pdfminer_text

        # Save Cleaned Text
        cleaned_text_file = os.path.join(output_folder, f"{os.path.basename(input_pdf)}.txt")
        with open(cleaned_text_file, "w", encoding="utf-8") as f:
            f.write(final_text)
        logger.info(f"Cleaned text saved to: {cleaned_text_file}")

    # Cleaned PDF is automatically discarded after processing due to the temporary directory

    return cleaned_text_file

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload and processing."""
    logger.info("Upload request received")
    
    try:
        # Check if the post request has the file part
        if 'file' not in request.files:
            logger.error("No file part in the request")
            return jsonify({"error": "No file part"}), 400
        
        file = request.files['file']
        
        # If user does not select file, browser also
        # submit an empty part without filename
        if file.filename == '':
            logger.error("No selected file")
            return jsonify({"error": "No selected file"}), 400
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(file_path)
            
            logger.info(f"File saved to {file_path}, now processing...")
            
            # Process the PDF
            result_file = process_pdf(file_path, PROCESSED_FOLDER)
            
            # Return success response
            return jsonify({
                "success": True,
                "message": f"File processed successfully",
                "filename": filename,
                "processed_file": os.path.basename(result_file)
            })
        else:
            logger.error("File type not allowed")
            return jsonify({"error": "Only PDF files are allowed"}), 400
    
    except Exception as e:
        logger.error(f"Error processing upload: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/files/<filename>', methods=['GET'])
def get_file(filename):
    """Serve processed files."""
    return send_from_directory(PROCESSED_FOLDER, filename)

@app.route('/textbooks', methods=['GET'])
def list_textbooks():
    """List all available textbooks."""
    try:
        files = os.listdir(UPLOAD_FOLDER)
        pdfs = [f for f in files if f.lower().endswith('.pdf')]
        return jsonify({"textbooks": pdfs})
    except Exception as e:
        logger.error(f"Error listing textbooks: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Important: Set CORS headers to allow requests from your frontend
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
    return response

if __name__ == '__main__':
    logger.info("Starting server on port 5000")
    app.run(host='0.0.0.0', port=5000, debug=True)