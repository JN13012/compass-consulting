FROM python:3.12-slim
WORKDIR /poc
RUN pip install --no-cache-dir "fastapi>=0.115" "uvicorn>=0.32" "litellm>=1.55"
COPY . .
EXPOSE 8100
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8100"]
