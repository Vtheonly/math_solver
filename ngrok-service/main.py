"""
Ngrok Service — Automated HTTP Tunnel and AMQP Bridge

Creates an HTTP tunnel pointing to itself, and acts as a bridge 
for the Colab GPU worker to pull/push from RabbitMQ.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pyngrok import ngrok, conf
import consul
import os
import threading
import time
import pika
import json

app = FastAPI(title="Ngrok Service", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
ngrok_url = "⏳ Waiting for Ngrok tunnel..."
ngrok_status = "starting"
RABBITMQ_HOST = "rabbitmq"

def get_rabbitmq_connection():
    for attempt in range(10):
        try:
            return pika.BlockingConnection(
                pika.ConnectionParameters(host=RABBITMQ_HOST, heartbeat=600)
            )
        except:
            time.sleep(3)
    raise Exception("Could not connect to RabbitMQ")


def setup_ngrok_and_consul():
    global ngrok_url, ngrok_status
    time.sleep(10)  # Wait for RabbitMQ

    auth_token = os.getenv("NGROK_AUTHTOKEN", "")
    if auth_token and auth_token != "your_ngrok_auth_token_here":
        try:
            ngrok.set_auth_token(auth_token)
            # Expose the local FastAPI server port (8003) via HTTP!
            tunnel = ngrok.connect(8003, "http")
            ngrok_url = tunnel.public_url
            ngrok_status = "connected"
            print(f"✅ Ngrok Tunnel Established: {ngrok_url}")
        except Exception as e:
            ngrok_url = f"ERROR: Ngrok failed — {str(e)}"
            ngrok_status = "error"
            print(f"❌ Ngrok error: {e}")
    else:
        ngrok_url = "⚠️ Set NGROK_AUTHTOKEN in .env"
        ngrok_status = "missing_token"

    # Register to Consul
    for attempt in range(10):
        try:
            c = consul.Consul(host='consul', port=8500)
            c.agent.service.register(
                name='ngrok-service',
                service_id='ngrok-service-1',
                address='ngrok-service',
                port=8003,
                tags=[
                    "traefik.enable=true",
                    "traefik.http.routers.ngrok.rule=PathPrefix(`/api/ngrok`)",
                    "traefik.http.routers.ngrok.entrypoints=web",
                    "traefik.http.services.ngrok-service.loadbalancer.server.port=8003",
                ]
            )
            print("✅ Ngrok-Service registered in Consul")
            return
        except Exception as e:
            time.sleep(3)

threading.Thread(target=setup_ngrok_and_consul, daemon=True).start()


@app.get("/api/ngrok/url")
def get_url():
    return {"url": ngrok_url, "status": ngrok_status}


@app.get("/api/ngrok/health")
def health():
    return {"status": "healthy", "service": "ngrok-service", "tunnel_status": ngrok_status}

# ── Worker Bridge Endpoints ────────────────────────────────────

class ResultPayload(BaseModel):
    task_id: str
    latex: str

@app.get("/worker/task")
def get_task():
    """Pulls a single message from 'ocr_tasks'."""
    try:
        connection = get_rabbitmq_connection()
        channel = connection.channel()
        channel.queue_declare(queue='ocr_tasks', durable=True)
        
        method_frame, header_frame, body = channel.basic_get(queue='ocr_tasks', auto_ack=True)
        if method_frame:
            data = json.loads(body)
            connection.close()
            return data
        else:
            connection.close()
            raise HTTPException(status_code=404, detail="No tasks in queue")
    except Exception as e:
        if isinstance(e, HTTPException): raise e
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/worker/result")
def post_result(payload: ResultPayload):
    """Pushes a completed OCR result to 'ocr_results'."""
    try:
        connection = get_rabbitmq_connection()
        channel = connection.channel()
        channel.queue_declare(queue='ocr_results', durable=True)
        
        channel.basic_publish(
            exchange='',
            routing_key='ocr_results',
            body=json.dumps(payload.dict()),
            properties=pika.BasicProperties(delivery_mode=2)
        )
        connection.close()
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
