import os
import time
import logging
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from typing import TypedDict
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl, Field
from langgraph.graph import StateGraph
from langchain_core.runnables import RunnableLambda
from image_checker import find_uncaptioned_images
from rag import WCAGIndex, DATA
from scanner import scan_page, report_from_scan, ScanError
from explain import Explanation
from scan_history import ScanHistory, normalize_url

load_dotenv(Path(__file__).parent / '.env')
logger = logging.getLogger(__name__)

class URLRequest(BaseModel):
    url: HttpUrl
    previous_scan_id: str | None = Field(default=None, max_length=100)

class URLInput(BaseModel):
    url: HttpUrl

class Issue(BaseModel):
    id: str
    rule_id: str
    type: str
    severity: str
    title: str
    description: str
    count: int = Field(ge=1)
    element: str
    detected_evidence: list[dict]
    suggestion: str
    explanation: Explanation
    wcagReference: str
    helpUrl: str | None = None

class ScanReport(BaseModel):
    model_config = {'extra': 'allow'}
    url: str
    scanId: str
    scannedAt: str
    scanProfile: str
    score: int = Field(ge=0, le=100)
    totalIssues: int = Field(ge=0)
    scanTime: str
    issues: list[Issue]
    severityCounts: dict[str, int]
    comparison: dict | None = None

class GraphState(TypedDict):
    url: str
    content: dict
    report: dict

api = FastAPI()
api.add_middleware(CORSMiddleware, allow_origins=os.getenv('CORS_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173').split(','),
                   allow_methods=['GET', 'POST'], allow_headers=['*'])

def scrape_node(state):
    return {'url': state['url'], 'content': scan_page(state['url'])}

def analyze_node(state):
    try:
        index = WCAGIndex(database=Path(os.getenv('WCAG_DB_PATH', str(DATA / 'wcag.sqlite'))))
    except Exception:
        logger.exception('WCAG index unavailable; preserving scanner results')
        index = None
    return {**state, 'report': report_from_scan(state['content'], index)}

graph = StateGraph(GraphState)
graph.add_node('scrape', RunnableLambda(scrape_node))
graph.add_node('analyze', RunnableLambda(analyze_node))
graph.set_entry_point('scrape')
graph.add_edge('scrape', 'analyze')
graph.set_finish_point('analyze')
app = graph.compile()

def history():
    return ScanHistory(os.getenv('SCAN_DB_PATH', str(DATA / 'scans.sqlite')))

@api.post('/check-accessibility', response_model=ScanReport)
def check_accessibility(request: URLRequest):
    # A sync FastAPI endpoint runs in a worker thread, including Playwright on Windows.
    try:
        url = normalize_url(str(request.url))
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    previous = None
    try:
        store = history()
        previous = store.get(request.previous_scan_id) if request.previous_scan_id else None
    except Exception:
        store = None
    if previous and normalize_url(previous['url']) != url:
        raise HTTPException(422, 'The baseline must have the same URL')
    start = time.monotonic()
    try:
        state = app.invoke({'url': url})
        report = state['report']
    except ScanError as exc:
        logger.exception('Accessibility scan failed')
        raise HTTPException(502, str(exc)) from exc
    except Exception as exc:
        logger.exception('Accessibility scan failed')
        raise HTTPException(502, 'Accessibility scan failed. Verify the URL, Chromium installation and local axe-core dependency.') from exc
    report.update(url=url, scanId=str(uuid4()), scannedAt=datetime.now(timezone.utc).isoformat(), scanTime=f'{time.monotonic() - start:.1f}s')
    try:
        if store is None:
            raise RuntimeError('History unavailable')
        report['comparison'], report['comparisonNotice'] = store.save(report, request.previous_scan_id)
    except ValueError:
        # A different scanner profile is not a valid comparison, but the scan still succeeds.
        report['comparison'], report['comparisonNotice'] = store.save(report)
        report['comparisonNotice'] = 'Baseline scanner profile differs. Current scan retained as a new baseline.'
    except Exception:
        logger.exception('Scan history unavailable')
        report.update(comparison=None, comparisonNotice='Scan history unavailable; this result could not be saved.')
    return report

@api.get('/scans/{scan_id}', response_model=ScanReport)
def get_scan(scan_id: str):
    try:
        report = history().get(scan_id)
    except Exception as exc:
        raise HTTPException(503, 'Scan history unavailable') from exc
    if report is None:
        raise HTTPException(404, 'Scan not found')
    return report

@api.post("/generate-alt-text")

def generate_alt_text(data:URLInput):
    url=str(data.url).strip()

    try:
        images= find_uncaptioned_images(url)
    except Exception as e:
        return{"error":f"Failed to crawl the site:{str(e)}"}

    if not images:
        return{"message":"All images on this page have alt text."}

    try:
        from blip_captioner import generate_caption
    except Exception:
        return {'error': 'Image caption model unavailable. Accessibility scan results remain available.'}

    result=[]

    for img_url in images:
        try:
            caption=generate_caption(img_url)
            result.append({"img_url":img_url, "caption":caption})
        except Exception as e:
            result.append({"img_url":img_url, "caption":f"Failed:{str(e)}"})
    return {"uncaptioned_images":result}
