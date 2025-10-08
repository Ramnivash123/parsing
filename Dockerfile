FROM python:3.10-slim

RUN apt-get update && apt-get install -y portaudio19-dev ffmpeg
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "app.py"]