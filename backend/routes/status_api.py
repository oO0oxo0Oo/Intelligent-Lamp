from flask import Blueprint, Response, request

from backend.services import snapshot_store, telemetry_service
from backend.utils.response import error, ok


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
    page = request.args.get("page", type=int)
    page_size = request.args.get("page_size", default=6, type=int)

    if page is not None:
        return ok(telemetry_service.get_events_page(page=page, page_size=page_size))

    limit = request.args.get("limit", default=50, type=int)
    items = telemetry_service.get_events(limit=limit)
    return ok(
        {
            "items": items,
            "total": telemetry_service.get_events_total(),
            "page": 1,
            "page_size": limit,
        }
    )


@status_api.get("/events/<int:event_id>/snapshot.jpg")
def event_snapshot(event_id):
    jpeg_bytes = snapshot_store.load_event_snapshot(event_id)
    if not jpeg_bytes:
        return error("Snapshot not found", 404)
    return Response(jpeg_bytes, mimetype="image/jpeg")


@status_api.get("/session/current")
def current_session():
    return ok({"session": telemetry_service.get_current_session()})
