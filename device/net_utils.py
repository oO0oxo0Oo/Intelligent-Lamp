import network
import time


def ensure_wifi(config):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if wlan.isconnected():
        return wlan.ifconfig()[0]

    print("Connecting to WiFi:", config["wifi_ssid"])
    wlan.connect(config["wifi_ssid"], config["wifi_password"])

    timeout = int(config.get("connect_timeout_seconds", 10))
    start = time.time()
    while not wlan.isconnected():
        if time.time() - start > timeout:
            print("WiFi connection timeout")
            return None
        print(".", end="")
        time.sleep(0.5)

    ip = wlan.ifconfig()[0]
    print("\nWiFi connected. IP:", ip)
    return ip


def wifi_connected():
    wlan = network.WLAN(network.STA_IF)
    return wlan.isconnected()

