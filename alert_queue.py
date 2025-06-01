"""
Alert Queue Service
------------------
This service receives alerts for network faults and queues them up for processing by downstream event-driven automation services.

- Endpoint: POST /alert
- Receives: {"content": "..."}
- Appends alert content to a queue file for later processing.
"""
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.responses import JSONResponse
import os
import argparse
import uvicorn
import json

app = FastAPI()

ALERT_QUEUE_FILE = os.path.join(os.path.dirname(__file__), 'workbench', 'alert_queue.txt')

class Alert(BaseModel):
    content: str

@app.post("/alert")
def receive_alert(alert: Alert):
    """
    Receives an alert and appends it to the alert queue file for processing.
    Now writes each alert as a JSON object (JSON Lines format) to support multi-line content.
    """
    os.makedirs(os.path.dirname(ALERT_QUEUE_FILE), exist_ok=True)
    with open(ALERT_QUEUE_FILE, 'a', encoding='utf-8') as f:
        f.write(json.dumps(alert.model_dump(), ensure_ascii=False) + '\n')
    return JSONResponse(content={"status": "success"})

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Alert Queue service.")
    parser.add_argument("--port", type=int, default=8001, help="Port to run the Alert Queue service on (default: 8001)")
    args = parser.parse_args()
    uvicorn.run("alert_queue:app", host="0.0.0.0", port=args.port)
