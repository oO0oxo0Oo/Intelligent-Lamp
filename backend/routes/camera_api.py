import time

from flask import Blueprint, Response, current_app, jsonify, make_response

from backend.services.camera_store import get_latest_frame


camera_api = Blueprint("camera_api", __name__)


@camera_api.get("/latest")
def latest_frame_meta():
    frame, timestamp, device_id = get_latest_frame()
    return jsonify(
        {
            "ok": True,
            "has_frame": frame is not None,
            "timestamp": timestamp,
            "device_id": device_id,
        }
    )


@camera_api.get("/live")
def live_stream():
    def generate():
        while True:
            frame, timestamp, _ = get_latest_frame()
            if frame is None:
                time.sleep(current_app.config["CAMERA_STREAM_INTERVAL"])
                continue
            yield b"--frame\r\n"
            yield b"Content-Type: image/jpeg\r\n"
            yield b"Cache-Control: no-cache\r\n"
            yield b"Pragma: no-cache\r\n"
            yield f"X-Frame-Timestamp: {timestamp}\r\n\r\n".encode("utf-8")
            yield frame
            yield b"\r\n"
            time.sleep(current_app.config["CAMERA_STREAM_INTERVAL"])

    response = Response(
        generate(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@camera_api.get("/latest.jpg")
def latest_frame_image():
    frame, timestamp, _ = get_latest_frame()
    if frame is None:
        return jsonify({"ok": False, "message": "No camera frame yet"}), 404
    response = make_response(frame)
    response.headers["Content-Type"] = "image/jpeg"
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    response.headers["X-Frame-Timestamp"] = str(timestamp)
    return response
