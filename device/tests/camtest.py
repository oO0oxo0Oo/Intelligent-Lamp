import network
import time
import socket
import select
from machine import Pin, reset

# 确保 camera 模块存在
try:
    import camera
except ImportError:
    print("FATAL ERROR: 'camera' module is missing. Please flash the custom firmware.")
    raise

# ===========================
# WiFi 配置
# ===========================
SSID = "sotakus_2.4g"  # 填写你的WIFI名 2.4G的
PASSWORD = "e2.71828"  # 填写你的wifi密码

# ===========================
# 引脚定义 (来自 camera_pins.h 中的 ESP32S3_EYE)
# ===========================
CAM_PIN_PWDN = -1
CAM_PIN_RESET = -1
CAM_PIN_XCLK = 15
CAM_PIN_SIOD = 4
CAM_PIN_SIOC = 5

CAM_PIN_D7 = 16  # Y9
CAM_PIN_D6 = 17  # Y8
CAM_PIN_D5 = 18  # Y7
CAM_PIN_D4 = 12  # Y6
CAM_PIN_D3 = 10  # Y5
CAM_PIN_D2 = 8  # Y4
CAM_PIN_D1 = 9  # Y3
CAM_PIN_D0 = 11  # Y2

CAM_PIN_VSYNC = 6
CAM_PIN_HREF = 7
CAM_PIN_PCLK = 13


# ===========================
# WiFi 连接函数 (已验证工作)
# ===========================
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print('正在连接 WiFi...')
        wlan.connect(SSID, PASSWORD)
        timeout = 10
        start = time.time()
        while not wlan.isconnected():
            if time.time() - start > timeout:
                return None
            time.sleep(0.5)
            print(".", end="")
    print('\nWiFi 已连接:', wlan.ifconfig())
    return wlan.ifconfig()[0]


# ===========================
# 摄像头初始化函数 (修正版本)
# ===========================
def init_camera():
    try:
        # 尝试先释放
        try:
            camera.deinit()
        except Exception:
            pass

        # MicroPython 的 camera.init 参数
        # camera.init(0, format=camera.JPEG, framesize=camera.FRAME_SVGA,
        #             xclk_freq=camera.XCLK_20MHz,
        #             d0=CAM_PIN_D0, d1=CAM_PIN_D1, d2=CAM_PIN_D2, d3=CAM_PIN_D3,
        #             d4=CAM_PIN_D4, d5=CAM_PIN_D5, d6=CAM_PIN_D6, d7=CAM_PIN_D7,
        #             vsync=CAM_PIN_VSYNC, href=CAM_PIN_HREF, pclk=CAM_PIN_PCLK,
        #             xclk=CAM_PIN_XCLK, siod=CAM_PIN_SIOD, sioc=CAM_PIN_SIOC,
        #             reset=CAM_PIN_RESET, pwdn=CAM_PIN_PWDN)
        camera.init(0, format=camera.JPEG, framesize=camera.FRAME_VGA,
                    xclk_freq=camera.XCLK_20MHz,
                    d0=CAM_PIN_D0, d1=CAM_PIN_D1, d2=CAM_PIN_D2, d3=CAM_PIN_D3,
                    d4=CAM_PIN_D4, d5=CAM_PIN_D5, d6=CAM_PIN_D6, d7=CAM_PIN_D7,
                    vsync=CAM_PIN_VSYNC, href=CAM_PIN_HREF, pclk=CAM_PIN_PCLK,
                    xclk=CAM_PIN_XCLK, siod=CAM_PIN_SIOD, sioc=CAM_PIN_SIOC,
                    reset=CAM_PIN_RESET, pwdn=CAM_PIN_PWDN)

        # 移除 camera.vflip(1) 语句，改用更兼容的 set_vflip 或 set_saturation/brightness

        # 尝试获取传感器对象并设置翻转/亮度 (兼容性设置)
        try:
            # 某些固件支持 sensor 属性
            s = camera.sensor
            s.set_vflip(s, 1)  # 尝试设置垂直翻转
            s.set_brightness(s, 1)  # 尝试设置亮度
        except Exception:
            # 如果 sensor 属性不存在，则忽略设置
            pass

        print("摄像头初始化成功")
        return True

    except Exception as e:
        print(f"摄像头初始化失败: {e}")
        return False


# ===========================
# Web 服务器和流媒体处理函数
# ===========================
# 简单的 HTML 页面
HTML_PAGE = """<html><head><title>ESP32-S3 Cam</title></head>
                 <body>
                 <h1>ESP32-S3 Camera Stream</h1>
                 <img src="/stream" style="width:100%; max-width:600px;">
                 </body></html>"""


def start_server(ip):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('', 80))
    s.listen(5)
    print(f"服务器已启动: http://{ip}")
    print(f"视频流地址: http://{ip}/stream")

    while True:
        try:
            # 使用 select 监听，避免阻塞
            r, _, _ = select.select([s], [], [], 0.01)
            if r:
                conn, addr = s.accept()
                request = conn.recv(1024)
                request_str = str(request)

                if "GET /stream" in request_str:
                    # 发送 MJPEG 视频流头部
                    conn.sendall(b'HTTP/1.1 200 OK\r\n')
                    conn.sendall(b'Content-Type: multipart/x-mixed-replace; boundary=frame\r\n\r\n')

                    try:
                        while True:
                            # 捕获一帧图像
                            buf = camera.capture()

                            # 发送帧数据
                            conn.sendall(b'--frame\r\n')
                            conn.sendall(b'Content-Type: image/jpeg\r\n')
                            conn.sendall(f'Content-Length: {len(buf)}\r\n\r\n'.encode())
                            conn.sendall(buf)
                            conn.sendall(b'\r\n')
                            # 释放一些资源
                            time.sleep_ms(1)

                    except Exception:
                        # 客户端断开连接，循环结束
                        pass

                else:
                    # 发送 HTML 页面
                    conn.sendall(b'HTTP/1.1 200 OK\r\n')
                    conn.sendall(b'Content-Type: text/html\r\n')
                    conn.sendall(b'Connection: close\r\n\r\n')
                    conn.sendall(HTML_PAGE.encode())

                conn.close()

        except Exception as e:
            # print(f"Socket error: {e}")
            if 'conn' in locals():
                conn.close()


# ===========================
# 主程序
# ===========================
def main():
    # 1. 连接 WiFi
    ip = connect_wifi()

    if ip:
        # 2. 初始化摄像头
        if init_camera():
            # 3. 启动服务器
            start_server(ip)
        else:
            print("因摄像头初始化失败，Web 服务器未启动。")


if __name__ == '__main__':
    main()

