import os
import json
import re
import csv
import io
# pyrefly: ignore [missing-import]
from flask import Flask, request, jsonify, render_template, send_file
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
DEFAULT_MODEL = "meta-llama/llama-3.3-70b-instruct:free"
REQUEST_TIMEOUT = 15

def fetch_and_clean_html(url: str) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }
    if not url.startswith("http"):
        url = "https://" + url
    
    resp = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "lxml")
    for tag in soup(["script", "style", "noscript", "meta", "link", "header", "footer", "nav", "svg", "button", "iframe"]):
        tag.decompose()
    return soup.get_text(separator="\n", strip=True)

def extract_data_with_ai(text: str, user_request: str) -> dict:
    api_key = os.getenv("OPENROUTER_API_KEY", OPENROUTER_API_KEY)
    client = OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")

    # Limit to 150,000 characters to comfortably fit inside Llama 3.3 70B's 65k context limit
    max_chars = 150000 
    if len(text) > max_chars:
        text = text[:max_chars] + "... [truncated]"

    system_prompt = "You are a precise data extraction AI. Extract structured data from web content as JSON.\nRULES:\n1. Return ONLY a valid JSON array of objects.\n2. Each object must have consistent keys.\n3. Return full string values; do not abbreviate names or nationalities unless requested.\n4. Avoid raw markdown fences around your output."
    prompt = f"Extract data based on this request: {user_request}\n\nCONTENT:\n{text}\n\nReturn ONLY a JSON array."

    fallback_models = [
        "meta-llama/llama-3.3-70b-instruct:free",
        "qwen/qwen3-coder:free",
        "google/gemma-3-27b-it:free",
        "openrouter/free"
    ]
    
    raw = None
    last_error = None
    for model in fallback_models:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                temperature=0,
            )
            raw = response.choices[0].message.content.strip()
            break  # successful
        except Exception as e:
            last_error = e
            continue
            
    if not raw:
        return {"success": False, "error": f"All AI providers failed or rate-limited. Last error: {str(last_error)}", "raw": ""}

    raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
    raw = re.sub(r"```\s*$", "", raw, flags=re.MULTILINE)

    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            data = [data]
        return {"success": True, "data": data}
    except json.JSONDecodeError as e:
        # Attempt to fix truncated JSON by finding the last complete object
        last_brace = raw.rfind("}")
        if last_brace != -1:
            try:
                # Cut at the last object and cap the array
                fixed_raw = raw[:last_brace+1].strip()
                if not fixed_raw.startswith("["):
                    fixed_raw = "[" + fixed_raw
                if not fixed_raw.endswith("]"):
                    fixed_raw = fixed_raw + "]"
                
                # We also need to make sure there are no trailing commas
                fixed_raw = re.sub(r',\s*\]', ']', fixed_raw)
                
                data = json.loads(fixed_raw)
                if isinstance(data, dict):
                    data = [data]
                return {"success": True, "data": data}
            except:
                pass
                
        # Try raw bracket match as final fallback
        match = re.search(r'\[.*\]', raw, re.DOTALL)
        if match:
            try:
                return {"success": True, "data": json.loads(match.group())}
            except:
                pass
                
        return {"success": False, "error": "AI response was too large and got cut off. Try asking for fewer items (e.g. 'Top 10...'). " + str(e), "raw": raw[:500]}



@app.route("/api/scrape", methods=["POST"])
def api_scrape():
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

@app.route("/api/download", methods=["POST"])
def api_download():
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

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
