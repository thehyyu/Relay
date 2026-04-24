FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Build 時預載 ONNX embedding model，避免 Pod 每次啟動都重新下載（79MB）
# K8s livenessProbe 不等下載，必須把依賴打進 image（ADR-006）
RUN python -c "from chromadb.utils.embedding_functions.onnx_mini_lm_l6_v2 import ONNXMiniLM_L6_V2; ONNXMiniLM_L6_V2()"
COPY main.py .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
