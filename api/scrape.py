import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, request, jsonify
from shared.utils import fetch_and_clean_html, extract_data_with_ai

app = Flask(__name__)

@app.route("/", methods=["POST"])
@app.route("/api/scrape", methods=["POST"])
def scrape_endpoint():
    req_data = request.json
    url = req_data.get("url")
    user_prompt = req_data.get("prompt", "Extract all meaningful data as structured JSON")

    if not url:
        return jsonify({"success": False, "error": "URL is required"}), 400

    try:
        text = fetch_and_clean_html(url)
    except Exception as e:
        return jsonify({"success": False, "error": f"Failed to fetch site: {str(e)}"}), 400

    result = extract_data_with_ai(text, user_prompt)
    if not result["success"]:
        return jsonify({"success": False, "error": result.get("error", "AI Extraction failed")}), 500

    return jsonify({"success": True, "data": result["data"]})

# Vercel requires the app variable to be exposed
