from flask import jsonify


def ok(data=None, status=200):
    payload = {"ok": True}
    if data:
        payload.update(data)
    return jsonify(payload), status


def error(message, status=400):
    return jsonify({"ok": False, "message": message}), status

