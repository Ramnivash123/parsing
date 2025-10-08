from flask import Flask, render_template, request, redirect, url_for, jsonify
import os, threading
import parser  # your parser.py
from flask import send_file


app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = "uploads"

exam_thread = None
exam_running = False
uploaded_docx = None


def run_exam(input_docx):
    global exam_running
    exam_running = True
    try:
        parser.INPUT_DOC = input_docx
        parser.qa_progress.clear()   # reset before new run
        parser.main()
    finally:
        exam_running = False


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload():
    global uploaded_docx
    if "file" not in request.files:
        return "No file uploaded", 400
    file = request.files["file"]
    if file.filename == "":
        return "No file selected", 400
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    file.save(filepath)
    uploaded_docx = filepath
    return redirect(url_for("exam"))


@app.route("/exam")
def exam():
    return render_template("exam.html")


@app.route("/start_exam", methods=["POST"])
def start_exam():
    global exam_thread
    if uploaded_docx and not exam_running:
        exam_thread = threading.Thread(target=run_exam, args=(uploaded_docx,))
        exam_thread.start()
        return jsonify({"status": "started"})
    return jsonify({"status": "already running"})


@app.route("/progress")
def progress():
    """Return live Q&A items."""
    return jsonify({
        "running": exam_running,
        "items": parser.qa_progress
    })

@app.route("/download_answers")
def download_answers():
    """Allow user to download the answers.docx file."""
    path = "answers.docx"
    try:
        return send_file(path, as_attachment=True)
    except FileNotFoundError:
        return jsonify({"error": "File not found"}), 404


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
