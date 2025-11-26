import os
import json
import requests
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, ConfigDict
from playwright.sync_api import sync_playwright
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ---------------------------------------------------------------------------
# ENVIRONMENT VARIABLES
# ---------------------------------------------------------------------------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
STUDENT_EMAIL = os.getenv("STUDENT_EMAIL")
STUDENT_SECRET = os.getenv("STUDENT_SECRET")

# Check which environment variables are missing
missing_vars = []
if not GEMINI_API_KEY:
    missing_vars.append("GEMINI_API_KEY")
if not STUDENT_EMAIL:
    missing_vars.append("STUDENT_EMAIL")
if not STUDENT_SECRET:
    missing_vars.append("STUDENT_SECRET")

if missing_vars:
    error_msg = f"Missing environment variables: {', '.join(missing_vars)}\n"
    error_msg += "Please create a .env file in the project root with these variables.\n"
    error_msg += "See .env.example for the required format."
    raise RuntimeError(error_msg)

genai.configure(api_key=GEMINI_API_KEY)
llm = genai.GenerativeModel("gemini-pro")

# ---------------------------------------------------------------------------
# FASTAPI APP
# ---------------------------------------------------------------------------
app = FastAPI()

class QuizRequest(BaseModel):
    email: str
    secret: str
    url: str
    model_config = ConfigDict(extra="ignore")

# ---------------------------------------------------------------------------
# FETCH HTML (JS RENDERED)
# ---------------------------------------------------------------------------
def fetch_html(url: str) -> str:
    """
    Fetch HTML content from a URL using Playwright to handle JavaScript-rendered content.
    
    Args:
        url: The URL to fetch
        
    Returns:
        The HTML content of the page
        
    Raises:
        RuntimeError: If the page fails to load or fetch
    """
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                # Navigate to the URL with timeout
                page.goto(url, timeout=30000, wait_until="networkidle")
                # Wait for content to be loaded
                page.wait_for_load_state("domcontentloaded")
                # Get the HTML content
                html = page.content()
                return html
            finally:
                browser.close()
    except Exception as e:
        raise RuntimeError(f"Failed to fetch HTML from {url}: {str(e)}")

# ---------------------------------------------------------------------------
# PARSE QUIZ (LLM)
# ---------------------------------------------------------------------------
def parse_quiz(html: str):
    prompt = f"""
Extract and return ONLY valid JSON:

1. question text
2. submit_url
3. any required data

Format:
{{
  "question":"...",
  "submit_url":"...",
  "data_sources":[]
}}
"""

    response = llm.generate_content(prompt + html)
    text = response.text

    try:
        return json.loads(text[text.index("{"): text.rindex("}")+1])
    except:
        raise RuntimeError("Failed to parse quiz metadata")

# ---------------------------------------------------------------------------
# SOLVE QUIZ (basic)
# ---------------------------------------------------------------------------
def solve_question(question: str):
    response = llm.generate_content(
        f"Answer this clearly and correctly: {question}"
    )
    return response.text.strip()

# ---------------------------------------------------------------------------
# SUBMIT ANSWER
# ---------------------------------------------------------------------------
def submit_answer(submit_url, original_url, answer):
    payload = {
        "email": STUDENT_EMAIL,
        "secret": STUDENT_SECRET,
        "url": original_url,
        "answer": answer
    }

    resp = requests.post(submit_url, json=payload)

    try:
        return resp.json()
    except:
        return {"correct": False, "reason": "Invalid server response"}

# ---------------------------------------------------------------------------
# API ENDPOINT — MUST RETURN FINAL ANSWER
# ---------------------------------------------------------------------------
@app.post("/")
async def root(task: QuizRequest):

    if task.secret != STUDENT_SECRET:
        raise HTTPException(status_code=403, detail="Invalid secret")

    html = fetch_html(task.url)
    parsed = parse_quiz(html)

    question = parsed["question"]
    submit_url = parsed["submit_url"]

    answer = solve_question(question)

    result = submit_answer(submit_url, task.url, answer)

    return result  # ✅ full final answer returned immediately

# ---------------------------------------------------------------------------
@app.get("/")
def home():
    return {"status": "running"}

# ---------------------------------------------------------------------------
# RUN SERVER
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
