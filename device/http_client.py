import socket
import time
import ujson


def _read_response(sock):
    chunks = []
    while True:
        data = sock.recv(256)
        if not data:
            break
        chunks.append(data)
        if len(chunks) > 8:
            break
    raw = b"".join(chunks)
    if not raw:
        return 0, ""

    head, _, body = raw.partition(b"\r\n\r\n")
    status_line = head.split(b"\r\n", 1)[0]
    parts = status_line.split()
    status_code = int(parts[1]) if len(parts) >= 2 else 0
    return status_code, body.decode("utf-8", "ignore")


def _send_request(config, method, path, body=b"", content_type=None, extra_headers=None):
    host = config["backend_host"]
    port = int(config.get("backend_port", 5000))
    timeout = int(config.get("connect_timeout_seconds", 10))
    headers = extra_headers or {}

    addr = socket.getaddrinfo(host, port)[0][-1]
    sock = socket.socket()
    sock.settimeout(timeout)

    try:
        sock.connect(addr)
        request = ["{} {} HTTP/1.1".format(method, path)]
        request.append("Host: {}:{}".format(host, port))
        request.append("Connection: close")
        request.append("X-Device-Id: {}".format(config["device_id"]))
        request.append("X-Device-Token: {}".format(config["device_token"]))
        if content_type:
            request.append("Content-Type: {}".format(content_type))
        request.append("Content-Length: {}".format(len(body)))
        for key, value in headers.items():
            request.append("{}: {}".format(key, value))
        request.append("")
        request.append("")
        sock.send("\r\n".join(request).encode())

        if body:
            start = 0
            while start < len(body):
                sent = sock.send(body[start : start + 1024])
                if sent <= 0:
                    raise OSError("Socket send failed")
                start += sent

        return _read_response(sock)
    finally:
        sock.close()


def get_json(config, path):
    status_code, body = _send_request(config, "GET", path)
    if status_code != 200 or not body:
        return None
    return ujson.loads(body)


def post_json(config, path, payload):
    body = ujson.dumps(payload).encode()
    return _send_request(config, "POST", path, body, "application/json")


def post_jpeg(config, path, jpeg_bytes, extra_headers=None):
    return _send_request(config, "POST", path, jpeg_bytes, "image/jpeg", extra_headers)

