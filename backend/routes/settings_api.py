from flask import Blueprint, request

from backend.services.db import get_settings, get_threshold_settings, update_settings
from backend.utils.response import error, ok


settings_api = Blueprint("settings_api", __name__)


def _threshold_payload(payload):
    settings = get_settings()
    allowed = set(get_threshold_settings(settings).keys())
    return {key: value for key, value in payload.items() if key in allowed}


@settings_api.get("")
def read_settings():
    return ok({"settings": get_threshold_settings()})


@settings_api.put("")
def write_settings():
    payload = request.get_json(silent=True) or {}
    filtered = _threshold_payload(payload)
    if not filtered:
        return error("settings payload is required")
    update_settings(filtered)
    return ok({"settings": get_threshold_settings()})
