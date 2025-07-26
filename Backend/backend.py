import os
import sys
import json
import time
import traceback
import requests
from bs4 import BeautifulSoup
from typing import TypedDict
from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from langgraph.graph import StateGraph
from langchain_core.runnables import RunnableLambda
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage
from image_checker import find_uncaptioned_images
from blip_captioner import generate_caption
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Windows event loop policy (if needed)
if sys.platform == "win32":
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# Load .env variables
load_dotenv()
os.environ["GROQ_API_KEY"] = os.getenv("API_KEY")

# Define state type
class GraphState(TypedDict):
    url: str
    content: str
    report: str

# FastAPI model
class URLRequest(BaseModel):
    url: str
    
class URLInput(BaseModel):
    url:str

# FastAPI app
api = FastAPI()

api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# STEP 1: Scrape content using requests
def scrape_site(url: str) -> str:
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers, timeout=10)
    soup = BeautifulSoup(response.content, "html.parser")
    text = soup.get_text(separator="\n", strip=True)
    return text[:5000]  # Limit characters for LLM input

# STEP 2: LangGraph scrape node
def scrape_node(state: dict) -> dict:
    url = state["url"]
    html = scrape_site(url)
    return {"url": url, "content": html}

# STEP 3: LangGraph analyze node using Groq
def analyze_node(state: dict) -> dict:
    model = ChatGroq(
        model="llama3-70b-8192",
        api_key=os.getenv("API_KEY")
    )

    prompt = f"""
You are a strict and detail-oriented web accessibility auditor.

Analyze the given web page and return **only** a valid, parsable JSON object (no markdown, no prose, no extra text) strictly in the following format:

{{
  "score": integer (0 to 100),
  "totalIssues": integer,
  "scanTime": string (e.g., "2.3s"),
  "issues": [
    {{
      "id": integer (unique per issue),
      "type": one of ["critical", "moderate", "low"],
      "severity": one of ["high", "medium", "low"],
      "title": string (short, specific summary of the issue),
      "description": string (clear explanation of the issue including the exact line number in the HTML source where it occurs),
      "element": string (HTML tag, selector, or code fragment involved),
      "suggestion": string (a precise and practical fix, ideally WCAG-aligned),
      "count": integer (number of occurrences of this issue)
    }}
  ]
}}

For each issue, include the most relevant WCAG 2.1 reference in the "wcagReference" field using this format:
"WCAG 2.1 AA - [Success Criterion Number] [Success Criterion Name]"

Examples:
- Missing alt attribute on image → "WCAG 2.1 AA - 1.1.1 Non-text Content"
- Insufficient contrast → "WCAG 2.1 AA - 1.4.3 Contrast (Minimum)"
- Missing form label → "WCAG 2.1 AA - 1.3.1 Info and Relationships"
- Non-keyboard accessible element → "WCAG 2.1 AA - 2.1.1 Keyboard"

Only include **one most relevant** reference per issue.
Do not invent or hallucinate WCAG references, line numbers, or issues that are not present.

**Strict rules**
- Output **must** be valid JSON. Do not include markdown, prose, comments, or code outside the JSON structure.
- For each issue, the `"element"` field must **explicitly show** the problematic or insufficient part of the HTML code or selector (e.g., `<img src='...' />` missing alt, or `div[role="button"]` with no keyboard handler).
- Suggestions must be **clear and directly actionable** — not generic advice.
- When mentioning line numbers in the description, provide the approximate line number as per the HTML source. If exact line number is not clear, specify as “approximate line X”.
- For missing alt text issues on `<img>` tags, **only report images with common raster formats:** jpg, jpeg, png, gif, bmp, webp.
- For missing alt text, if it is a logo, mention it in the title
- Do **not** report missing alt text issues for images with uncommon or vector formats such as svg, xml, ico, or data URIs.
- Do **not** fabricate issues. Only report genuine accessibility problems found in the provided HTML.
- Group identical issues by type and element. Use count to indicate total occurrences. Do not list duplicates as separate entries.

**Severity classification rules:**
- **High severity**: Issues that cause major barriers to users with disabilities. Examples include missing alt text on meaningful images, missing labels on form inputs, keyboard inaccessibility, or content that cannot be perceived or operated by assistive technologies.
- **Medium severity**: Issues that impact usability but have possible workarounds or are less critical. Examples include insufficient color contrast that affects some users, unclear link text, or missing landmarks that complicate navigation but do not prevent it.
- **Low severity**: Minor issues or best practice improvements that have minimal impact on accessibility. Examples include missing page titles, redundant ARIA attributes, or minor semantic markup errors that don't affect usability significantly.

**Scoring Instructions**
- The score is an integer between 0 and 100, representing overall accessibility compliance.
- Critical issues reduce the score the most, moderate issues reduce it moderately, and low issues reduce it slightly.
- Start with a base score of 100.
- For each issue occurrence, subtract points as follows:
    - critical: subtract 15 points per occurrence,
    - moderate: subtract 7 points per occurrence,
    - low: subtract 3 points per occurrence.
- Calculate the score before clamping in "scoreBeforeClamp".
- Final score = max(0, scoreBeforeClamp), rounded to nearest integer.
- Report counts of each severity in "calculationDetails".
- Include a "calculationDetails" object in the output JSON with:
  {{
    "criticalCount": int,
    "moderateCount": int,
    "lowCount": int,
    "rawScore": int,
    "finalScore": int
  }}
- finalScore in "calculationDetails" must be equal to the "score" field.
- If no issues, score = 100.

Start your analysis now.

Content:
{state['content']}
    """

    start = time.time()
    response = model.invoke([HumanMessage(content=prompt)])
    duration = round(time.time() - start, 1)

    try:
        report = json.loads(response.content)
        report["url"] = state["url"]
        report["scanTime"] = f"{duration}s"
        return {
        **state,
        "report": report
    }
    except Exception as e:
        return {
            "url": state["url"],
            "report": response.content,
            "error": str(e)
        }
    

# STEP 4: Build LangGraph
graph = StateGraph(GraphState)
graph.add_node("scrape", RunnableLambda(scrape_node))
graph.add_node("analyze", RunnableLambda(analyze_node))
graph.set_entry_point("scrape")
graph.add_edge("scrape", "analyze")
graph.set_finish_point("analyze")
app = graph.compile()

# STEP 5: FastAPI endpoint
@api.post("/check-accessibility")
async def check_accessibility(request: URLRequest):
    try:
        url = request.url
        print(f"🔗 Scanning URL: {url}")
        state = await app.ainvoke({"url": url})
        print("📦 Full LangGraph Output:", state)
        if "report" in state:
            return state["report"]
        else:
            return {"error": "No report generated", "debug": state}
    except Exception as e:
        print("❌ Backend Error:")
        traceback.print_exc()
        return {
            "error": str(e),
            "trace": traceback.format_exc()
        }
        
@api.post("/generate-alt-text")

def generate_alt_text(data:URLInput):
    url=data.url.strip()

    try:
        images= find_uncaptioned_images(url)
    except Exception as e:
        return{"error":f"Failed to crawl the site:{str(e)}"}
    
    if not images:
        return{"message":"All images on this page have alt text."}
    
    result=[]

    for img_url in images:
        try:
            caption=generate_caption(img_url)
            result.append({"img_url":img_url, "caption":caption})
        except Exception as e:
            result.append({"img_url":img_url, "caption":f"Failed:{str(e)}"})
    return {"uncaptioned_images":result}