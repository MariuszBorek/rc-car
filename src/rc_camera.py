import io
import socket
import threading
import time

from flask import Flask, Response, render_template_string
from picamera2 import Picamera2
import requests
import cv2

# ===== KONFIG =====
PORT = 5000
PUSHOVER_USER_KEY = "KEY"
PUSHOVER_APP_TOKEN = "TOKEN"
PUSHOVER_RETRIES = 10
PUSHOVER_DELAY = 5  # sekundy między próbami

# ===== INIT =====
app = Flask(__name__)
camera = None
frame_lock = threading.Lock()
current_frame = None


# ===== POBRANIE IP =====
def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


# ===== PUSHOVER Z RETRY =====
def send_pushover(message, retries=PUSHOVER_RETRIES, delay=PUSHOVER_DELAY):
    for _ in range(retries):
        try:
            requests.post(
                "https://api.pushover.net/1/messages.json",
                data={
                    "token": PUSHOVER_APP_TOKEN,
                    "user": PUSHOVER_USER_KEY,
                    "message": message,
                },
                timeout=5
            )
            print("Pushover sent")
            return
        except Exception as e:
            print("Pushover error, retrying in {}s: {}".format(delay, e))
            time.sleep(delay)
    print("Failed to send Pushover after retries")


# ===== CAMERA THREAD =====
def camera_worker():
    global current_frame
    while True:
        try:
            frame = camera.capture_array()
            with frame_lock:
                current_frame = frame
        except Exception as e:
            print("Camera error:", e)
            time.sleep(1)


# ===== MJPEG STREAM =====
def generate_mjpeg():
    while True:
        with frame_lock:
            if current_frame is None:
                continue
            frame = current_frame.copy()

        ret, jpeg = cv2.imencode(".jpg", frame)
        if not ret:
            continue

        yield (b"--frame\r\n"
               b"Content-Type: image/jpeg\r\n\r\n" +
               jpeg.tobytes() +
               b"\r\n")


# ===== ROUTES =====
@app.route("/")
def index():
    return render_template_string("""
        <html>
        <head><title>Raspberry Pi Camera</title></head>
        <body>
            <h1>Live Stream</h1>
            <img src="/video" width="640"/>
        </body>
        </html>
    """)


@app.route("/video")
def video():
    return Response(generate_mjpeg(),
                    mimetype="multipart/x-mixed-replace; boundary=frame")


# ===== START CAMERA =====
def start_camera():
    global camera
    try:
        camera = Picamera2()
        config = camera.create_preview_configuration(main={"size": (640, 480)})
        camera.configure(config)
        camera.start()

        thread = threading.Thread(target=camera_worker, daemon=True)
        thread.start()

    except Exception as e:
        print("Failed to start camera:", e)
        exit(1)


# ===== MAIN =====
if __name__ == "__main__":
    start_camera()

    # odczekaj chwilę, żeby sieć mogła wystartować
    time.sleep(5)

    ip = get_local_ip()
    url = f"http://{ip}:{PORT}"

    print("Server running at:", url)

    # Wyślij push
    send_pushover(f"Camera stream available at {url}")

    # Start Flask
    app.run(host="0.0.0.0", port=PORT, threaded=True)