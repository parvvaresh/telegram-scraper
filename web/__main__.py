"""Run the control panel:  python3 -m web   (from the repository root)."""
import os

import uvicorn

if __name__ == "__main__":
    host = os.environ.get("WEB_HOST", "127.0.0.1")
    port = int(os.environ.get("WEB_PORT", "8000"))
    if host not in ("127.0.0.1", "localhost") and not os.environ.get("WEB_PASSWORD"):
        print("⚠️  Panel is exposed on", host, "without WEB_PASSWORD — anyone who can reach it can edit config and start runs.")
    print(f"🌐 Panel: http://{'localhost' if host in ('0.0.0.0', '127.0.0.1') else host}:{port}")
    uvicorn.run("web.app:app", host=host, port=port, log_level="warning")
