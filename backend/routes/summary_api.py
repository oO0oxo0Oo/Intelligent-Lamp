from flask import Blueprint

from backend.services import telemetry_service
from backend.utils.response import ok


summary_api = Blueprint("summary_api", __name__)


@summary_api.get("/latest")
def latest_summary():
    return ok({"summary": telemetry_service.get_latest_summary()})


@summary_api.get("/today")
def today_summary():
    return ok(telemetry_service.get_today_summary())
