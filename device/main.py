try:
    import _thread
except ImportError:
    _thread = None

from camera_streamer import run as run_camera_streamer
from config_loader import load_config
from net_utils import ensure_wifi
from sensor_collector import run as run_sensor_collector


def main():
    config = load_config()
    ip = ensure_wifi(config)
    if ip is None:
        print("Initial WiFi connection failed, main halted")
        return

    if config.get("camera_enabled", True) and _thread is not None:
        _thread.start_new_thread(run_camera_streamer, (config,))
    elif config.get("camera_enabled", True):
        print("Warning: _thread is unavailable, camera streamer will not start")

    run_sensor_collector(config)


if __name__ == "__main__":
    main()
