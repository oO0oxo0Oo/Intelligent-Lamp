import time

from http_client import post_jpeg, post_json
from net_utils import ensure_wifi, wifi_connected

try:
    import camera
except ImportError:
    camera = None


CAM_PIN_PWDN = -1
CAM_PIN_RESET = -1
CAM_PIN_XCLK = 15
CAM_PIN_SIOD = 4
CAM_PIN_SIOC = 5

CAM_PIN_D7 = 16
CAM_PIN_D6 = 17
CAM_PIN_D5 = 18
CAM_PIN_D4 = 12
CAM_PIN_D3 = 10
CAM_PIN_D2 = 8
CAM_PIN_D1 = 9
CAM_PIN_D0 = 11

CAM_PIN_VSYNC = 6
CAM_PIN_HREF = 7
CAM_PIN_PCLK = 13


def _camera_framesize(config):
    if camera is None:
        return None

    size_name = str(config.get("camera_framesize", "QVGA")).upper()
    mapping = {
        "QVGA": getattr(camera, "FRAME_QVGA", getattr(camera, "FRAME_VGA", None)),
        "VGA": getattr(camera, "FRAME_VGA", None),
        "SVGA": getattr(camera, "FRAME_SVGA", getattr(camera, "FRAME_VGA", None)),
    }
    return mapping.get(size_name, mapping["QVGA"])


def init_camera(config):
    if camera is None:
        print("camera module is missing, skip camera streamer")
        return False

    try:
        try:
            camera.deinit()
        except Exception:
            pass

        camera.init(
            0,
            format=camera.JPEG,
            framesize=_camera_framesize(config),
            xclk_freq=camera.XCLK_20MHz,
            d0=CAM_PIN_D0,
            d1=CAM_PIN_D1,
            d2=CAM_PIN_D2,
            d3=CAM_PIN_D3,
            d4=CAM_PIN_D4,
            d5=CAM_PIN_D5,
            d6=CAM_PIN_D6,
            d7=CAM_PIN_D7,
            vsync=CAM_PIN_VSYNC,
            href=CAM_PIN_HREF,
            pclk=CAM_PIN_PCLK,
            xclk=CAM_PIN_XCLK,
            siod=CAM_PIN_SIOD,
            sioc=CAM_PIN_SIOC,
            reset=CAM_PIN_RESET,
            pwdn=CAM_PIN_PWDN,
        )
        print("Camera initialized")
        return True
    except Exception as exc:
        print("Camera init failed:", exc)
        return False


def run(config):
    if not config.get("camera_enabled", True):
        print("Camera streamer disabled in config")
        return

    if not init_camera(config):
        try:
            post_json(
                config,
                "/api/device/events",
                {
                    "event_type": "camera_init_failed",
                    "level": "error",
                    "message": "Camera initialization failed",
                    "timestamp": int(time.time()),
                },
            )
        except Exception:
            pass
        return

    frame_interval_ms = int(config.get("camera_frame_interval_ms", 200))
    while True:
        try:
            if not wifi_connected():
                ensure_wifi(config)

            frame = camera.capture()
            timestamp = int(time.time())
            status, _ = post_jpeg(
                config,
                "/api/device/camera/frame?timestamp={}".format(timestamp),
                frame,
                {"X-Frame-Timestamp": str(timestamp)},
            )
            if status not in (200, 201, 204):
                print("Camera frame upload failed:", status)
            time.sleep_ms(frame_interval_ms)
        except Exception as exc:
            print("Camera loop error:", exc)
            time.sleep_ms(500)

