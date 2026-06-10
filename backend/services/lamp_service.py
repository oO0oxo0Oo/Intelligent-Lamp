from backend.services.db import get_settings, update_settings

DEFAULT_LAMP_CONTROL = {
    "brightness": 68,
    "color_temperature": 4100,
    "scene_mode": "eye_care",
}

SCENE_MODES = frozenset({"eye_care", "reading", "focus", "night"})


def get_lamp_control():
    settings = get_settings()
    stored = settings.get("lamp_control") or {}
    control = {**DEFAULT_LAMP_CONTROL, **stored}
    if control["scene_mode"] not in SCENE_MODES:
        control["scene_mode"] = DEFAULT_LAMP_CONTROL["scene_mode"]
    return control


def update_lamp_control(payload):
    if not payload:
        raise ValueError("control payload is required")

    current = get_lamp_control()
    next_control = {**current}

    if "brightness" in payload:
        brightness = int(payload["brightness"])
        if brightness < 0 or brightness > 100:
            raise ValueError("brightness must be between 0 and 100")
        next_control["brightness"] = brightness

    if "color_temperature" in payload:
        color_temperature = int(payload["color_temperature"])
        if color_temperature < 2700 or color_temperature > 6500:
            raise ValueError("color_temperature must be between 2700 and 6500")
        next_control["color_temperature"] = color_temperature

    if "scene_mode" in payload:
        scene_mode = payload["scene_mode"]
        if scene_mode not in SCENE_MODES:
            raise ValueError("scene_mode is invalid")
        next_control["scene_mode"] = scene_mode

    update_settings({"lamp_control": next_control})
    return next_control
