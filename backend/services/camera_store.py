import threading
import time


_lock = threading.Lock()
_latest_frame = None
_latest_timestamp = 0
_latest_device_id = None


def update_frame(device_id, frame_bytes, timestamp=None):
    global _latest_frame, _latest_timestamp, _latest_device_id
    with _lock:
        _latest_frame = frame_bytes
        _latest_timestamp = int(timestamp or time.time())
        _latest_device_id = device_id


def get_latest_frame():
    with _lock:
        return _latest_frame, _latest_timestamp, _latest_device_id

