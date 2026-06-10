from flask import Blueprint, request

from backend.services import lamp_service
from backend.utils.response import error, ok


lamp_api = Blueprint("lamp_api", __name__)


@lamp_api.put("/control")
def update_control():
    payload = request.get_json(silent=True) or {}
    try:
        control = lamp_service.update_lamp_control(payload)
    except ValueError as exc:
        return error(str(exc))
    return ok({"lamp_control": control})
