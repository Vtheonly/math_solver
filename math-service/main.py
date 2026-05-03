"""
Math Service — Core Engine + RabbitMQ Integration

This is the heart of the system. It:
1. Exposes REST endpoints for equation solving (synchronous)
2. Accepts image uploads and pushes them to RabbitMQ (asynchronous)
3. Consumes OCR results from Colab via RabbitMQ background thread
4. Runs the SolverPipeline on extracted LaTeX and stores results
5. Self-registers in Consul for Traefik discovery
"""

from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import jwt
import consul
import pika
import json
import uuid
import threading
import time
import traceback

# Import YOUR existing engine — no changes needed
from engine.pipeline.solver_pipeline import SolverPipeline

app = FastAPI(title="Math Service", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Configuration ──────────────────────────────────────────────
SECRET_KEY = "math_solver_academic_secret_key_2026"
ALGORITHM = "HS256"
RABBITMQ_HOST = "rabbitmq"
RABBITMQ_RETRY_DELAY = 5
RABBITMQ_MAX_RETRIES = 20

# In-memory task store (production would use Redis/DB)
tasks_db = {}


# ── Consul Registration ───────────────────────────────────────
def register_to_consul():
    """Register this service in Consul with Traefik routing tags."""
    max_retries = 10
    for attempt in range(max_retries):
        try:
            c = consul.Consul(host='consul', port=8500)
            c.agent.service.register(
                name='math-service',
                service_id='math-service-1',
                address='math-service',
                port=8002,
                tags=[
                    "traefik.enable=true",
                    "traefik.http.routers.math.rule=PathPrefix(`/api/math`)",
                    "traefik.http.routers.math.entrypoints=web",
                    "traefik.http.services.math-service.loadbalancer.server.port=8002",
                ]
            )
            print("✅ Math-Service registered in Consul")
            return
        except Exception as e:
            print(f"⏳ Consul not ready (attempt {attempt + 1}/{max_retries}): {e}")
            time.sleep(3)
    print("❌ Failed to register in Consul after all retries")


threading.Thread(target=register_to_consul, daemon=True).start()


# ── RabbitMQ Connection Helper ─────────────────────────────────
def get_rabbitmq_connection():
    """Create a RabbitMQ connection with retry logic."""
    for attempt in range(RABBITMQ_MAX_RETRIES):
        try:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=RABBITMQ_HOST,
                    heartbeat=600,
                    blocked_connection_timeout=300,
                )
            )
            return connection
        except pika.exceptions.AMQPConnectionError as e:
            print(f"⏳ RabbitMQ not ready (attempt {attempt + 1}/{RABBITMQ_MAX_RETRIES}): {e}")
            time.sleep(RABBITMQ_RETRY_DELAY)
    raise Exception("❌ Could not connect to RabbitMQ after all retries")


# ── RabbitMQ Consumer (Background Thread) ──────────────────────
def consume_ocr_results():
    """
    Background thread that listens to 'ocr_results' queue.
    When Colab sends back extracted LaTeX, this thread:
    1. Receives the LaTeX string
    2. Runs SolverPipeline.solve() on it
    3. Stores the complete result in tasks_db
    """
    time.sleep(15)  # Wait for RabbitMQ to be fully ready
    print("🔄 Starting OCR results consumer...")

    while True:
        try:
            connection = get_rabbitmq_connection()
            channel = connection.channel()
            channel.queue_declare(queue='ocr_results', durable=True)

            def callback(ch, method, properties, body):
                try:
                    data = json.loads(body)
                    task_id = data.get('task_id')
                    latex_equation = data.get('latex', '')

                    print(f"📥 Received LaTeX from Colab for task {task_id}: {latex_equation}")

                    # Retrieve the saved mode for this task
                    task_info = tasks_db.get(task_id, {})
                    mode = task_info.get("mode", "solver")
                    image_base64 = task_info.get("image", "")

                    # Run the math engine on the extracted equation
                    pipeline = SolverPipeline()
                    result = pipeline.solve(latex_equation, mode=mode)

                    # Update task status with completed result
                    tasks_db[task_id] = {
                        "status": "completed",
                        "equation": latex_equation,
                        "result": result.to_dict(),
                        "image": image_base64
                    }
                    print(f"✅ Task {task_id} completed — {len(result.solutions)} solutions found")

                    ch.basic_ack(delivery_tag=method.delivery_tag)

                except Exception as e:
                    print(f"❌ Error processing OCR result: {e}")
                    traceback.print_exc()
                    # Store error state so UI can show it
                    task_id = json.loads(body).get('task_id', 'unknown')
                    tasks_db[task_id] = {
                        "status": "error",
                        "error": str(e)
                    }
                    ch.basic_ack(delivery_tag=method.delivery_tag)

            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(queue='ocr_results', on_message_callback=callback)
            print("✅ OCR results consumer started — waiting for Colab results...")
            channel.start_consuming()

        except Exception as e:
            print(f"❌ Consumer connection lost: {e}. Reconnecting in 5s...")
            time.sleep(5)


threading.Thread(target=consume_ocr_results, daemon=True).start()


# ── JWT Verification Middleware ────────────────────────────────
def verify_jwt(authorization: str = Header(None)):
    """Validate the JWT token from the Authorization header."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid Authorization header. Use: Bearer <token>"
        )
    try:
        token = authorization.split(" ")[1]
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired. Please login again.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token.")


# ── Request/Response Models ────────────────────────────────────
class TextSolveRequest(BaseModel):
    equation: str
    mode: str = "solver"


class ImageSolveRequest(BaseModel):
    image_base64: str
    mode: str = "solver"


class TaskResponse(BaseModel):
    task_id: str
    status: str = "processing"


# ── API Endpoints ──────────────────────────────────────────────

@app.post("/api/math/solve")
def solve_equation(req: TextSolveRequest, user: dict = Depends(verify_jwt)):
    """
    Synchronous equation solving.
    Receives a text equation, runs the SolverPipeline, returns step-by-step result.
    """
    try:
        pipeline = SolverPipeline()
        result = pipeline.solve(req.equation, mode=req.mode)
        return result.to_dict()
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Solving error: {str(e)}")


@app.post("/api/math/solve-image", response_model=TaskResponse)
def solve_image(req: ImageSolveRequest, user: dict = Depends(verify_jwt)):
    """
    Asynchronous image solving via RabbitMQ.
    1. Stores task as 'processing'
    2. Publishes image to 'ocr_tasks' queue for Colab worker
    3. Returns task_id for polling
    """
    task_id = str(uuid.uuid4())
    tasks_db[task_id] = {"status": "processing", "mode": req.mode, "image": req.image_base64}

    try:
        connection = get_rabbitmq_connection()
        channel = connection.channel()
        channel.queue_declare(queue='ocr_tasks', durable=True)

        payload = {
            "task_id": task_id,
            "image_base64": req.image_base64
        }
        channel.basic_publish(
            exchange='',
            routing_key='ocr_tasks',
            body=json.dumps(payload),
            properties=pika.BasicProperties(delivery_mode=2)  # persistent
        )
        connection.close()

        print(f"📤 Task {task_id} published to ocr_tasks queue")
        return TaskResponse(task_id=task_id)

    except Exception as e:
        tasks_db[task_id] = {"status": "error", "error": str(e)}
        raise HTTPException(status_code=500, detail=f"RabbitMQ error: {str(e)}")


@app.get("/api/math/task/{task_id}")
def get_task_status(task_id: str, user: dict = Depends(verify_jwt)):
    """
    Poll task status.
    Returns 'processing', 'completed' (with result), or 'error'.
    """
    if task_id not in tasks_db:
        raise HTTPException(status_code=404, detail="Task not found")
    return tasks_db[task_id]


@app.get("/api/math/health")
def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "math-service",
        "active_tasks": len(tasks_db),
    }
