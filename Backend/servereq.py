import os
import uuid
import json
import time
from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS
from query import query_rag, extract_questions_from_pdf

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

UPLOAD_FOLDER = os.path.join(os.getcwd(), "upload")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
history = {}


@app.route('/query', methods=['POST'])
def handle_query():
    print("handle_query function called.")
    print(f"Headers: {request.headers}")
    print(f"Request Form: {request.form}")
    print(f"Request Files: {request.files}")

    try:
        if 'file' in request.files:
            # Handle file upload
            file = request.files['file']
            if file.filename == '':
                return jsonify({"error": "Empty file uploaded"}), 400

            if not file.filename.lower().endswith('.pdf'):
                return jsonify({"error": "Only PDF files are allowed"}), 400

            unique_filename = f"{uuid.uuid4().hex}.pdf"
            temp_pdf_path = os.path.join(UPLOAD_FOLDER, unique_filename)
            file.save(temp_pdf_path)

            try:
                questions = extract_questions_from_pdf(temp_pdf_path)
                if not questions:
                    return jsonify({"error": "No questions found in the PDF"}), 400

                # Format each question and answer as a pair
                results = [{"question": q, "answer": query_rag(q)} for q in questions[:20]]
                return jsonify({"status": "success", "responses": results})

            finally:
                os.remove(temp_pdf_path)

        elif 'question' in request.form:
            # Handle text query from form data
            query_text = request.form['question'].strip()
            if not query_text:
                return jsonify({"error": "Invalid or missing 'question' in request body"}), 400

            print(f"Calling query_rag with text: '{query_text}'")
            try:
                response_text = query_rag(query_text)
                print(f"query_rag response: '{response_text}'")
                # Return as a single question-answer pair
                return jsonify({
                    "status": "success", 
                    "responses": [{"question": query_text, "answer": response_text}]
                })
            except Exception as e:
                print(f"Error in query_rag: {e}")
                return jsonify({"error": "Error processing question."}), 500

        else:
            return jsonify({"error": "No file or question provided"}), 400

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/query_stream', methods=['GET', 'POST'])
def handle_query_stream():
    print("handle_query_stream function called.")
    print(f"Headers: {request.headers}")
    
    try:
        # Get the question from either GET parameters or POST form data
        if request.method == 'GET':
            query_text = request.args.get('question', '').strip()
            print(f"GET Request Args: {request.args}")
        else:  # POST
            query_text = request.form.get('question', '').strip()
            print(f"POST Request Form: {request.form}")
        
        if not query_text:
            return jsonify({"error": "Invalid or missing 'question' in request"}), 400
        
        def generate():
            # Send initial processing message
            yield f"data: {json.dumps({'status': 'processing', 'partial': 'Thinking about your question...'})}\n\n"
            time.sleep(0.5)  # Small delay to show initial message
            
            # Progress update
            yield f"data: {json.dumps({'status': 'processing', 'partial': 'Analyzing relevant information...'})}\n\n"
            time.sleep(0.5)
            
            # Another progress update
            yield f"data: {json.dumps({'status': 'processing', 'partial': 'Finalizing the best answer...'})}\n\n"
            
            try:
                # Get the actual answer
                print(f"Calling query_rag with text: '{query_text}'")
                response_text = query_rag(query_text)
                print(f"query_rag response: '{response_text}'")
                
                # Send final result
                yield f"data: {json.dumps({'status': 'success', 'response': response_text})}\n\n"
            except Exception as e:
                print(f"Error in query_rag: {e}")
                yield f"data: {json.dumps({'status': 'error', 'error': str(e)})}\n\n"
        
        return Response(stream_with_context(generate()), 
                       mimetype="text/event-stream",
                       headers={
                           'Cache-Control': 'no-cache',
                           'X-Accel-Buffering': 'no'  # Important for Nginx
                       })
            
    except Exception as e:
        print(f"Exception in handle_query_stream: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)