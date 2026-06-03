# This file is executed on every boot (including wake-boot from deepsleep).
try:
    import esp

    esp.osdebug(None)
except Exception:
    pass
