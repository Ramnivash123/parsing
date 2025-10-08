from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file
import os, threading, tempfile, wave, json
from vosk import Model, KaldiRecognizer
import parser  # your modified parser.py for exam logic with Vosk

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'

exam_thread = None
exam_running = False
uploaded_docx = None

# Load Vosk model once (adjust path if needed)
vosk_model = Model("vosk-model-en-us-0.22")  # Download this and place in project root or proper path


def transcribe_vosk_audio(file_path):
    wf = wave.open(file_path, "rb")
    if wf.getframerate() != 16000 or wf.getnchannels() != 1 or wf.getsampwidth() != 2:
        return {"error": "Audio file must be WAV mono 16kHz 16bit PCM"}

    recognizer = KaldiRecognizer(vosk_model, 16000)
    results = []
    while True:
        data = wf.readframes(4000)
        if len(data) == 0:
            break
        if recognizer.AcceptWaveform(data):
            res = json.loads(recognizer.Result())
            results.append(res.get("text", ""))
    final_res = json.loads(recognizer.FinalResult())
    results.append(final_res.get("text", ""))
    return {"text": " ".join(results).strip()}


def run_exam(input_docx):
    global exam_running
    exam_running = True
    try:
        parser.INPUT_DOC = input_docx
        parser.qa_progress.clear()
        parser.main()
    finally:
        exam_running = False


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload():
    global uploaded_docx
    if 'file' not in request.files:
        return "No file uploaded", 400
    file = request.files['file']
    if file.filename == '':
        return "No file selected", 400
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(path)
    uploaded_docx = path
    return redirect(url_for('exam'))


@app.route('/exam')
def exam():
    return render_template('exam.html')


@app.route('/start_exam', methods=['POST'])
def start_exam():
    global exam_thread
    if uploaded_docx and not exam_running:
        exam_thread = threading.Thread(target=run_exam, args=(uploaded_docx,))
        exam_thread.start()
        return jsonify({'status': 'started'})
    return jsonify({'status': 'already running'})


@app.route('/progress')
def progress():
    return jsonify({
        'running': exam_running,
        'items': parser.qa_progress
    })


@app.route('/download_answers')
def download_answers():
    path = 'answers.docx'
    try:
        return send_file(path, as_attachment=True)
    except FileNotFoundError:
        return jsonify({"error": "File not found"}), 404


@app.route('/transcribe_audio', methods=['POST'])
def transcribe_audio():
    if 'file' not in request.files:
        return jsonify({"error": "No audio file provided"}), 400

    audio_file = request.files['file']
    if audio_file.filename == '':
        return jsonify({"error": "Empty filename"}), 400

    # Save to temp file
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tf:
        audio_file.save(tf.name)
        temp_path = tf.name

    result = transcribe_vosk_audio(temp_path)
    os.remove(temp_path)
    return jsonify(result)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

