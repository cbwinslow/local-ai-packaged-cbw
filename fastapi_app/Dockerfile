FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --retries=5 CMD python -c "import requests,sys,urllib3; urllib3.disable_warnings(); sys.exit(0 if requests.get('http://localhost:8000/healthz',timeout=5).status_code==200 else 1)"
CMD ["uvicorn","main:app","--host","0.0.0.0","--port","8000"]
