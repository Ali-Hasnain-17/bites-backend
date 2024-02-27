from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from werkzeug.utils import secure_filename

import fitz
from openai import OpenAI
import openai
import nltk
from nltk.tokenize import sent_tokenize
from io import StringIO
import json

nltk.download('punkt')
nltk.download('wordnet')
nltk.download('omw-1.4')

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def read_pdf(filename):
    context = ""
    with fitz.open(filename) as pdf_file:
        num_pages = pdf_file.page_count
        for page_num in range(num_pages):
            page = pdf_file[page_num]
            page_text = page.get_text()
            context += page_text
    print(len(context))
    return context

def split_text(text, chunk_size=500):
    """
    Splits the given text into chunks of approximately the specified chunk size.

    Args:
    text (str): The text to split.

    chunk_size (int): The desired size of each chunk (in words).

    Returns:
    List[str]: A list of chunks, each of approximately the specified chunk size.
    """

    chunks = []
    def splitter(n, s):
        pieces = s.split()
        return (" ".join(pieces[i:i+n]) for i in range(0, len(pieces), n))

    for piece in splitter(chunk_size, text):
        chunks.append(piece)
    return chunks
    
def summrize(document):
    chunks = split_text(document)
    summaries = []
    sys_prompt = "يرجى تحويل النص إلى مجموعة متنوعة من الأسئلة والإجابات الخاصة بها بحيث يتم تغطية النص بالكامل بالأسئلة والأجوبة. وينبغي أن يكون الناتج سؤالاً يتبعه إجابة وهكذا. حاول تكوين أكبر عدد ممكن من أزواج الأسئلة والأجوبة"
    for chunk in chunks:
        usr_prompt = chunk
        client = OpenAI()
        completion = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": usr_prompt}
            ]
        )
        summary = completion.choices[0].message.content
        summaries.append(summary)
        
    return ''.join(summaries)

def getQuestionsAndAnswers(file):
    text = read_pdf(file)
    output = summrize(text)
    list_of_qa = output.split("\n\n")
    print("list of qa")
    print(list_of_qa)
    qa = []
    for element in list_of_qa:
        print(element)
        arr = element.split("\n")
        question = arr[0]
        answer = arr[1]
        qa.append({ "question": question, "answer": answer })

    return qa



@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    print(request)
    file = request.files['file']
    print(file)
    library = request.form["libraryId"]

    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    print("app upload folder")
    print(app.config['UPLOAD_FOLDER'])
    directory_path = os.path.join(app.config['UPLOAD_FOLDER'], library)

    if file and allowed_file(file.filename):
        os.makedirs(directory_path)
        filename = os.path.join(directory_path, secure_filename(file.filename))
        file.save(filename)

        qa = getQuestionsAndAnswers(filename)

        # You can perform additional processing or return the file path
        return jsonify(qa)
    else:
        return jsonify({'error': 'Invalid file format. Please upload a PDF file.'}), 400

if __name__ == '__main__':
    app.run(debug=True)