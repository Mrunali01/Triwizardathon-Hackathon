"""Real Chromium/axe -> FastAPI -> React two-scan smoke test. No OpenAI key needed.

Run from repository root: python Backend/tests/live_workflow.py
Starts isolated local servers and terminates its own processes on exit.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import requests
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
FIXED = False

class Fixture(BaseHTTPRequestHandler):
    def do_GET(self):
        body = '''<!doctype html><html lang="en"><head><title>Accessibility fixture</title></head><body><main>
        <h1>Contact us</h1><button></button>'''
        if FIXED:
            body += '<label for="name">Name</label><input id="name"><p style="color:#111;background:#fff">Readable text</p><a href="/target"></a>'
        else:
            body += '<input id="name"><p style="color:#aaa;background:#fff">Low contrast text</p>'
        body += '</main></body></html>'
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(body.encode())

    def log_message(self, *args):
        pass

def ready(url):
    for _ in range(120):
        try:
            if requests.get(url, timeout=1).ok:
                return
        except requests.RequestException:
            pass
        time.sleep(0.25)
    raise RuntimeError(f'Server did not start: {url}')

def run():
    global FIXED
    server = ThreadingHTTPServer(('127.0.0.1', 8766), Fixture)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    processes = []
    try:
        with tempfile.TemporaryDirectory() as temp:
            env = {**os.environ, 'ENABLE_LLM': 'false', 'SCAN_DB_PATH': str(Path(temp) / 'scans.sqlite'), 'VITE_API_BASE_URL': 'http://127.0.0.1:8011', 'CORS_ORIGINS': 'http://127.0.0.1:5175'}
            log = open(Path(temp) / 'servers.log', 'w', encoding='utf-8')
            try:
                processes.append(subprocess.Popen([sys.executable, '-m', 'uvicorn', 'backend:api', '--app-dir', 'Backend', '--host', '127.0.0.1', '--port', '8011'], cwd=ROOT, env=env, stdout=log, stderr=log))
                processes.append(subprocess.Popen(['node', 'node_modules/vite/bin/vite.js', '--host', '127.0.0.1', '--port', '5175', '--strictPort'], cwd=ROOT / 'Frontend', env=env, stdout=log, stderr=log))
                ready('http://127.0.0.1:8011/docs')
                ready('http://127.0.0.1:5175')
                with sync_playwright() as p:
                    browser = p.chromium.launch()
                    page = browser.new_page(viewport={'width': 1440, 'height': 1000})
                    errors = []
                    page.on('pageerror', lambda error: errors.append(str(error)))
                    page.goto('http://127.0.0.1:5175')
                    page.get_by_role('textbox', name='Website URL').fill('http://127.0.0.1:8766/')
                    with page.expect_response(lambda r: '/check-accessibility' in r.url and r.request.method == 'POST', timeout=90000) as response:
                        page.get_by_role('button', name='Start AI Scan').click()
                    first = response.value.json()
                    assert response.value.status == 200, first
                    assert first['comparison'] is None
                    contrast = next(i for i in first['issues'] if i['rule_id'] == 'color-contrast')
                    assert contrast['explanation']['wcag_criteria'] == ['1.4.3']
                    assert contrast['explanation']['confidence'] == 'High'
                    page.get_by_text('Why is this an issue?', exact=True).first.click()
                    page.get_by_text('Why it matters', exact=True).wait_for()
                    FIXED = True
                    page.reload()  # Baseline survives a page reload.
                    page.get_by_role('textbox', name='Website URL').fill('http://127.0.0.1:8766/')
                    with page.expect_response(lambda r: '/check-accessibility' in r.url and r.request.method == 'POST', timeout=90000) as response:
                        page.get_by_role('button', name='Start AI Scan').click()
                    second = response.value.json()
                    assert response.value.status == 200, second
                    comparison = second['comparison']
                    assert comparison['scoreChange'] > 0, comparison
                    assert {'label', 'color-contrast'} <= {i['rule_id'] for i in comparison['resolved']}
                    assert 'button-name' in {i['rule_id'] for i in comparison['remaining']}
                    assert 'link-name' in {i['rule_id'] for i in comparison['new']}
                    page.get_by_role('heading', name='Before / After Accessibility').wait_for()
                    for kind in ['CSV', 'PDF']:
                        with page.expect_download() as download:
                            page.get_by_role('button', name=f'Download {kind}').click()
                        target = Path(temp) / f'report.{kind.lower()}'
                        download.value.save_as(target)
                        data = target.read_bytes()
                        assert len(data) > 100
                        if kind == 'PDF':
                            assert data.startswith(b'%PDF')
                        else:
                            assert b'Before score' in data and b'WCAG' in data
                    page.get_by_text('All images on this page have alt text.').wait_for(timeout=15000)
                    screenshot = ROOT / 'Backend/data/screenshots/validation.png'
                    screenshot.parent.mkdir(parents=True, exist_ok=True)
                    page.screenshot(path=str(screenshot), full_page=True)
                    page.set_viewport_size({'width': 390, 'height': 844})
                    page.get_by_role('heading', name='Before / After Accessibility').scroll_into_view_if_needed()
                    page.evaluate('() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))')
                    page.screenshot(path=str(screenshot.with_name('validation-mobile.png')))
                    overflow = page.evaluate('[...document.querySelectorAll("body *")].filter(e => e.getBoundingClientRect().right > innerWidth + 1).map(e => e.tagName + "." + e.className).slice(0, 10)')
                    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), f'Mobile horizontal overflow: {overflow}'
                    assert not errors, errors
                    browser.close()
                    print(json.dumps({'beforeScore': first['score'], 'afterScore': second['score'], 'comparison': comparison, 'exports': ['PDF', 'CSV'], 'browserErrors': errors}, indent=2))
            finally:
                for proc in processes:
                    proc.terminate()
                    proc.wait(timeout=15)
                log.close()
    finally:
        server.shutdown()
        server.server_close()

if __name__ == '__main__':
    run()
