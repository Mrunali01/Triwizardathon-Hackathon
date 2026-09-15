"""Playwright and axe accessibility scanning."""
import os
from pathlib import Path
from playwright.sync_api import sync_playwright, Error as PlaywrightError, TimeoutError as PlaywrightTimeout
from explain import explain, add_ai_summaries

AXE = Path(__file__).resolve().parents[1] / 'Frontend/node_modules/axe-core/axe.min.js'
PROFILE = 'axe-4.10.3-all-rules-desktop-1280x720-score-v1-readiness-v3'

class ScanError(RuntimeError):
    """Actionable scanner errors safe to display without exposing a traceback."""

def wait_for_rendered_content(page):
    """Do not score a blank SPA shell as a nearly accessible website."""
    try:
        page.wait_for_function('''() => {
            const body = document.body;
            if (!body) return false;
            const text = body.innerText.trim();
            const visible = el => el.getClientRects().length && getComputedStyle(el).visibility !== 'hidden';
            return (text.length > 0 && !/^(loading[.\\s]*|please wait[.\\s]*)$/i.test(text)) ||
                [...body.querySelectorAll('img, canvas, input, textarea, select')].some(visible);
        }''', timeout=20000)
    except PlaywrightTimeout as exc:
        raise ScanError('The page did not render usable content. It may still be loading or its scripts may have failed. No accessibility score was generated; try again.') from exc
    return page.evaluate('''() => new Promise(resolve => {
        const start = performance.now();
        let changed = start;
        const observer = new MutationObserver(records => {
            if (records.some(r => [...r.addedNodes, ...r.removedNodes].some(n => n.nodeType === 1))) changed = performance.now();
        });
        observer.observe(document.body, {childList: true, subtree: true});
        const timer = setInterval(() => {
            const now = performance.now();
            const stable = now - start >= 2000 && now - changed >= 1000;
            if (stable || now - start >= 8000) {
                clearInterval(timer); observer.disconnect(); resolve(stable);
            }
        }, 250);
    })''')

def scan_page(url):
    try:
        return _scan_page(url)
    except PlaywrightTimeout as exc:
        raise ScanError('The website timed out before the page was ready. Try again or test another URL.') from exc
    except PlaywrightError as exc:
        message = str(exc)
        if 'Executable doesn' in message:
            detail = 'Chromium is missing. Run python -m playwright install chromium in your active virtual environment.'
        elif 'net::ERR_' in message:
            import re
            code = re.search(r'net::ERR_[A-Z_]+', message).group()
            detail = f'The browser could not reach the website ({code}). Check your connection and whether the URL opens locally.'
        else:
            detail = 'The browser could not complete the accessibility checks. See the backend log for details.'
        raise ScanError(detail) from exc

def _scan_page(url):
    axe_path = Path(os.getenv('AXE_SCRIPT_PATH', str(AXE)))
    if not axe_path.is_file():
        raise ScanError('axe-core is missing. Run npm install in Frontend first.')
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={'width': 1280, 'height': 720}, reduced_motion='reduce')
            response = page.goto(url, wait_until='domcontentloaded', timeout=45000)
            if response and response.status >= 400:
                raise ScanError(f'The website returned HTTP {response.status}. Verify the URL or try a page that permits automated access.')
            warning = ''
            try:
                page.wait_for_load_state('load', timeout=10000)
            except PlaywrightTimeout:
                warning = 'Some page resources did not finish loading. Results describe the currently rendered page; rerun to confirm.'
            if not wait_for_rendered_content(page):
                warning += ' Page content was still changing when scanned; rerun to confirm dynamic content.'
            page.add_script_tag(path=str(axe_path))
            result = page.evaluate('async () => await axe.run(document, { resultTypes: ["violations", "incomplete"] })')
            result['loadWarning'] = warning
            return result
        finally:
            browser.close()

def report_from_scan(raw, index):
    if not isinstance(raw, dict) or not isinstance(raw.get('violations'), list):
        raise ValueError('Invalid accessibility scanner response')
    issues = []
    counts = dict.fromkeys(['critical', 'serious', 'moderate', 'minor'], 0)
    for v in raw['violations']:
        impact = v.get('impact') or 'minor'
        if impact not in counts or not v.get('nodes') or not v.get('id'):
            raise ValueError('Invalid scanner violation')
        count = len(v['nodes'])
        counts[impact] += count
        explanation = explain(v, index).model_dump()
        issues.append(dict(id=v['id'], rule_id=v['id'], type=impact,
            severity={'critical': 'high', 'serious': 'high', 'moderate': 'medium', 'minor': 'low'}[impact],
            title=v['help'], description=v['description'], count=count,
            element='\n'.join(n['html'] for n in v['nodes'][:10]),
            detected_evidence=[{'target': n['target'], 'html': n['html'], 'failureSummary': n.get('failureSummary', ''),
                                'checks': n.get('any', []) + n.get('all', []) + n.get('none', [])} for n in v['nodes']],
            suggestion=explanation['recommendation'], explanation=explanation,
            wcagReference='; '.join(f"WCAG {e['version']} {e['level']} - {e['criterion']}" for e in explanation['evidence'] if e['criterion_match']),
            helpUrl=v.get('helpUrl')))
    critical = counts['critical'] + counts['serious']
    raw_score = 100 - 15 * critical - 7 * counts['moderate'] - 3 * counts['minor']
    return dict(score=max(0, raw_score), scoreBeforeClamp=raw_score, totalIssues=sum(counts.values()),
        totalRules=len(issues), scanSettings={'device': 'Desktop', 'viewport': '1280 x 720', 'axeVersion': raw.get('testEngine', {}).get('version', '4.10.3'), 'scoring': '15/7/3 points per occurrence; includes axe best practices'},
        issues=issues, severityCounts=counts, scanProfile=PROFILE,
        calculationDetails=dict(criticalCount=critical, moderateCount=counts['moderate'], lowCount=counts['minor'], rawScore=raw_score, finalScore=max(0, raw_score)),
        incompleteChecks=len(raw.get('incomplete', [])), aiStatus=add_ai_summaries(issues),
        scanNotice=('Automated checks do not establish WCAG conformance. Incomplete checks and keyboard/screen-reader behavior require manual review. ' + raw.get('loadWarning', '')).strip())
