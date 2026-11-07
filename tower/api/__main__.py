import argparse

import uvicorn

ap = argparse.ArgumentParser()
ap.add_argument("--port", type=int, default=8765)
a = ap.parse_args()
uvicorn.run("tower.api.server:app", host="127.0.0.1", port=a.port, log_level="warning")
