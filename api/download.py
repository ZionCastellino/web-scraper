import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import csv
import io
from flask import Flask, request, jsonify, send_file

app = Flask(__name__)

@app.route("/", methods=["POST"])
@app.route("/api/download", methods=["POST"])
def download_endpoint():
    req_data = request.json
    data = req_data.get("data", [])
    fmt = req_data.get("format", "json")

    if not data:
        return jsonify({"error": "No data provided"}), 400

    file_bytes = io.BytesIO()
    
    if fmt == "json":
        json_str = json.dumps(data, indent=2)
        file_bytes.write(json_str.encode("utf-8"))
        mimetype = "application/json"
        filename = "scraped_data.json"
    
    elif fmt == "csv":
        output = io.StringIO()
        keys = set()
        for item in data:
            if isinstance(item, dict):
                keys.update(item.keys())
        keys = list(keys)
        
        writer = csv.DictWriter(output, fieldnames=keys)
        writer.writeheader()
        for item in data:
            if isinstance(item, dict):
                row = {k: item.get(k, "") for k in keys}
                writer.writerow(row)
        file_bytes.write(output.getvalue().encode("utf-8"))
        mimetype = "text/csv"
        filename = "scraped_data.csv"
        
    elif fmt == "md":
        md_str = "# Scraped Data\n\n"
        for i, item in enumerate(data):
            md_str += f"## Item {i+1}\n"
            if isinstance(item, dict):
                for k, v in item.items():
                    md_str += f"- **{k}**: {v}\n"
            md_str += "\n"
        file_bytes.write(md_str.encode("utf-8"))
        mimetype = "text/markdown"
        filename = "scraped_data.md"
        
    elif fmt == "txt":
        txt_str = "Scraped Data\n============\n\n"
        for i, item in enumerate(data):
            txt_str += f"[Item {i+1}]\n"
            if isinstance(item, dict):
                for k, v in item.items():
                    txt_str += f"{k}: {v}\n"
            txt_str += "\n"
        file_bytes.write(txt_str.encode("utf-8"))
        mimetype = "text/plain"
        filename = "scraped_data.txt"
    else:
        return jsonify({"error": "Invalid format"}), 400

    file_bytes.seek(0)
    return send_file(file_bytes, as_attachment=True, download_name=filename, mimetype=mimetype)
