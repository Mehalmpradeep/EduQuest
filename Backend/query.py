import argparse
import fitz  # PyMuPDF
import ocrmypdf
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from get_embedding_function import get_embedding_function
import re

# Load environment variables
load_dotenv()

# Constants
CHROMA_PATH = "chroma"
PROMPT_TEMPLATE = """
Answer the question based only on the following context:

{context}

---

Answer the question based on the above context: {question}
"""

def main():
    parser = argparse.ArgumentParser(description="Extract questions from a PDF and query the RAG system.")
    parser.add_argument("pdf_path", type=str, help="Path to the PDF file.")
    args = parser.parse_args()

    # Perform OCR if necessary and extract questions
    pdf_path = args.pdf_path
    questions = extract_questions_from_pdf(pdf_path)

    if not questions:
        print("No questions found in the PDF.")
        return

    print(f"Total Questions Found: {len(questions)}")

    # Process each question
    results = []
    for i, question in enumerate(questions[:20], 1):  # Limit to first 20 questions
        print(f"\nProcessing Question {i}: {question}")
        response_text = query_rag(question)
        results.append((question, response_text))

    # Print all results
    print("\n--- Final Results ---")
    for i, (question, answer) in enumerate(results, 1):
        print(f"\nQuestion {i}: {question}\nAnswer: {answer}")

def extract_questions_from_pdf(pdf_path):
    print(f"DEBUG: Entering extract_questions_from_pdf with pdf_path: {pdf_path}")
    # Perform OCR if needed
    ocr_output_path = "ocr_output.pdf"
    ocrmypdf.ocr(pdf_path, ocr_output_path, force_ocr=True, output_type="pdf", optimize=3)

    # Extract text using PyMuPDF (fitz)
    doc = fitz.open(ocr_output_path)

    all_text = []
    for i, page in enumerate(doc):
        page_text = page.get_text("text")
        if page_text.strip():
            all_text.append(page_text)
        else:
            print(f"Warning: No text extracted from page {i+1}")

    doc.close()

    if not all_text:
        print("No text extracted from any pages.")
        return []

    print(f"Total Pages Processed: {len(all_text)}")

    # Combine text from all pages
    text = "\n".join(all_text)

    # Improved question extraction using regex for multiline questions
    question_pattern = re.compile(r'(?<=\n)(.*?\?)', re.DOTALL)
    questions = question_pattern.findall(text)

    print(f"DEBUG: Extracted questions: {questions}")
    return questions

def query_rag(query_text: str):
    print(f"DEBUG: Entering query_rag with query: '{query_text}'")
    try:
        embedding_function = get_embedding_function()
        db = Chroma(persist_directory=CHROMA_PATH, embedding_function=embedding_function)

        results = db.similarity_search_with_score(query_text, k=5)

        print(f"DEBUG: ChromaDB results: {results}")

        if not results:
            print("No relevant context found for the query.")
            return "No relevant context found."

        context_text = "\n\n---\n\n".join([doc.page_content for doc, _score in results])

        # Prepare prompt
        prompt_template = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)
        prompt = prompt_template.format(context=context_text, question=query_text)

        # Initialize Groq LLM
        llm = ChatGroq(
            model_name="llama3-70b-8192",
            temperature=0,
            streaming=False
        )

        # Generate response
        response = llm.invoke(prompt)
        response_text = response.content if hasattr(response, 'content') else str(response)

        print(f"DEBUG: Groq LLM response: {response_text}")
        return response_text

    except Exception as e:
        print(f"DEBUG: Error in query_rag: {e}")
        return str(e)

#Test ChromaDB
if __name__ == "__main__":
    embedding_function = get_embedding_function()
    db = Chroma(persist_directory=CHROMA_PATH, embedding_function=embedding_function)
    print(f"DEBUG: ChromaDB count: {db._collection.count()}")