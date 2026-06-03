from flask import Blueprint, request

from backend.services.db import get_settings, update_settings
from backend.utils.response import error, ok


settings_api = Blueprint("settings_api", __name__)


@settings_api.get("")
def read_settings():
    return ok({"settings": get_settings()})


@settings_api.put("")
def write_settings():
    payload = request.get_json(silent=True) or {}
    if not payload:
        return error("settings payload is required")
    return ok({"settings": update_settings(payload)})
