FROM python:3.10-slim
WORKDIR /app
COPY math-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Copy the engine and config from the project root
COPY engine/ ./engine/
COPY config.py .
# Copy the service entry point
COPY math-service/main.py .
EXPOSE 8002
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]
