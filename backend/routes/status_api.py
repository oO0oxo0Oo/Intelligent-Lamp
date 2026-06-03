from flask import Blueprint, request

from backend.services import telemetry_service
from backend.utils.response import ok


status_api = Blueprint("status_api", __name__)


@status_api.get("/current")
def current_status():
    return ok(telemetry_service.get_current_status())


@status_api.get("/history")
def telemetry_history():
    limit = request.args.get("limit", default=120, type=int)
    return ok({"items": telemetry_service.get_telemetry_history(limit=limit)})


@status_api.get("/events")
def events():
    limit = request.args.get("limit", default=50, type=int)
    return ok({"items": telemetry_service.get_events(limit=limit)})


@status_api.get("/session/current")
def current_session():
    return ok({"session": telemetry_service.get_current_session()})
