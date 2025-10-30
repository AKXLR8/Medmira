FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PORT=8080
# Set the port number of workers (adjust this number as needed)
ENV Gunicorn_workers=3
CMD exec gunicorn --bind :$PORT --workers $Gunicorn_workers --threads 8 --timeout 0 app:app