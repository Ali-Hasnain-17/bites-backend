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

def split_text(text, chunk_size=5000):
    """
    Splits the given text into chunks of approximately the specified chunk size.

    Args:
    text (str): The text to split.

    chunk_size (int): The desired size of each chunk (in characters).

    Returns:
    List[str]: A list of chunks, each of approximately the specified chunk size.
    """

    chunks = []
    current_chunk = StringIO()
    current_size = 0
    sentences = sent_tokenize(text)
    for sentence in sentences:
        sentence_size = len(sentence)
        if sentence_size > chunk_size:
            while sentence_size > chunk_size:
                chunk = sentence[:chunk_size]
                chunks.append(chunk)
                sentence = sentence[chunk_size:]
                sentence_size -= chunk_size
                current_chunk = StringIO()
                current_size = 0
        if current_size + sentence_size < chunk_size:
            current_chunk.write(sentence)
            current_size += sentence_size
        else:
            chunks.append(current_chunk.getvalue())
            current_chunk = StringIO()
            current_chunk.write(sentence)
            current_size = sentence_size
        if current_chunk:
            chunks.append(current_chunk.getvalue())
        return chunks
    
    
def gpt3_completion(prompt, engine='gpt-3.5-turbo', temp=0.5, top_p=0.3, tokens=1000):

    prompt = prompt.encode(encoding='ASCII',errors='ignore').decode()
    try:
        response = openai.Completion.create(
            engine=engine,
            prompt=prompt,
            temperature=temp,
            top_p=top_p,
            max_tokens=tokens
        )
        return response.choices[0].text.strip()
    except Exception as oops:
        return "GPT-3 error: %s" % oops
    
    
    
def summrize(document):
    chunks = split_text(document)
    summaries = []
    for chunk in chunks:
        sys_prompt = "Please convert the text into variety of questions and their respective answers such that it summarizes the text. The output should be a question followed by an answer and so on...: \n"
        usr_prompt = chunk
        client = OpenAI()
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
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
    text_file = open("output.txt", "w")
    n = text_file.write(output)
    text_file.close()
    list_of_qa = output.split("\n\n")

    qa = []
    for element in list_of_qa:
        arr = element.split(":")
        question = arr[1].split("?")[0] + "?"
        answer = arr[2]
        qa.append({ "question": question, "answer": answer })

    return qa



@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    library = request.form["library"]

    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
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