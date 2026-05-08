import os
import json
import re
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

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

    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "noscript", "meta", "link", "header", "footer", "nav", "svg", "button", "iframe"]):
        tag.decompose()
    return soup.get_text(separator="\n", strip=True)

def extract_data_with_ai(text: str, user_request: str) -> dict:
    api_key = os.getenv("OPENROUTER_API_KEY", OPENROUTER_API_KEY)
    client = OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")

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
            break
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
        last_brace = raw.rfind("}")
        if last_brace != -1:
            try:
                fixed_raw = raw[:last_brace+1].strip()
                if not fixed_raw.startswith("["):
                    fixed_raw = "[" + fixed_raw
                if not fixed_raw.endswith("]"):
                    fixed_raw = fixed_raw + "]"
                fixed_raw = re.sub(r',\s*\]', ']', fixed_raw)
                data = json.loads(fixed_raw)
                if isinstance(data, dict):
                    data = [data]
                return {"success": True, "data": data}
            except:
                pass
        match = re.search(r'\[.*\]', raw, re.DOTALL)
        if match:
            try:
                return {"success": True, "data": json.loads(match.group())}
            except:
                pass
        return {"success": False, "error": "AI response was too large and got cut off. Try asking for fewer items (e.g. 'Top 10...'). " + str(e), "raw": raw[:500]}
