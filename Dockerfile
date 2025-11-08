FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY gliner_model.pkl /app/src/gliner_model.pkl
COPY . .
ENV PORT=8080
ENV PYTHONPATH=/app
# Set the port number of workers (adjust this number as needed)
ENV Gunicorn_workers=3
CMD ["gunicorn", "--bind", ":8080", "--workers", "3", "--threads", "8", "--timeout", "0", "app:app"]
