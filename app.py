from flask import Flask, request, jsonify
from backend.auth import auth_bp
from backend.prescription import pres_bp
#import schedule
import threading
import os
from werkzeug.serving import WSGIRequestHandler
app = Flask(__name__)
app.config['SECRET_KEY'] = 'ramuka123'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024   # 100 MB
# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(pres_bp)
from backend.manual_prescription import manual_bp
app.register_blueprint(manual_bp)
from backend.prescription import pres_bp   # or wherever the route lives

from backend.auth import auth_bp

# ---- File Upload Route ----
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# @app.route("/api/upload", methods=["POST"])
# def upload_file():
#     if 'file' not in request.files:
#         return jsonify({"error": "No file part in request"}), 400
    
#     file = request.files['file']
#     if file.filename == '':
#         return jsonify({"error": "No file selected"}), 400

#     file_path = os.path.join(UPLOAD_FOLDER, file.filename)
#     file.save(file_path)

#     return jsonify({"message": "File uploaded successfully", "path": file_path}), 200

# ---- Example endpoints ----
@app.route("/api/hello", methods=["GET"])
def hello():
    return jsonify({"message": "Hello from Flask!"})

@app.route("/api/data", methods=["POST"])
def data():
    content = request.json
    return jsonify({"received": content})

# ---- Scheduler thread ----
# def _scheduler():
#     while True:
#         schedule.run_pending()
#         threading.Event().wait(60)

# threading.Thread(target=_scheduler, daemon=True).start()

print("=== URL MAP ===")
print(app.url_map)
print("===============")

if __name__ == "__main__":
        WSGIRequestHandler.timeout = 60 
        app.run(host="0.0.0.0", port=8080, debug=True)
