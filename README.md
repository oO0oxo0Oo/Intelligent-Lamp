# StudyPilot Smart Lamp

This repository contains:

- `device/`: MicroPython code for the ESP32-S3 board
- `backend/`: Flask backend for data ingestion, real-time state processing, and APIs
- `frontend/`: HTML/CSS/JS dashboard served by the backend
- `docs/`: project documentation

## Backend quick start

Use the existing Conda environment:

```powershell
conda activate studypilot
python -m pip install -r backend/requirements.txt
python -m backend.app
```

Open `http://127.0.0.1:5000`.

## ESP32 configuration

1. Copy `device/secrets.example.json` to `device/secrets.json`
2. Fill in your local Wi-Fi and backend IP
3. Upload the required files from `device/` to the ESP32 root filesystem

The real `device/secrets.json` is ignored by Git so Wi-Fi credentials are not committed.
