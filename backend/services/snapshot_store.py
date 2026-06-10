from pathlib import Path

from backend.config import Config


def _snapshot_path(event_id):
    return Path(Config.SNAPSHOT_DIR) / f"{event_id}.jpg"


def save_event_snapshot(event_id, jpeg_bytes):
    directory = Path(Config.SNAPSHOT_DIR)
    directory.mkdir(parents=True, exist_ok=True)
    path = _snapshot_path(event_id)
    path.write_bytes(jpeg_bytes)
    return str(path)


def load_event_snapshot(event_id):
    path = _snapshot_path(event_id)
    if not path.is_file():
        return None
    return path.read_bytes()
