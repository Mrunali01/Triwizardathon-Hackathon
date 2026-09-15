"""Retain reports and compare rule IDs using the existing report, without duplicate scan models."""
from contextlib import closing
import json
import sqlite3
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

def normalize_url(url):
    parts = urlsplit(url)
    if parts.scheme not in ('http', 'https') or not parts.hostname or parts.username or parts.password:
        raise ValueError('Use an HTTP(S) URL without credentials')
    port = parts.port
    host = parts.hostname.lower()
    if ':' in host:
        host = f'[{host}]'
    if port and (parts.scheme, port) not in [('http', 80), ('https', 443)]:
        host += f':{port}'
    return urlunsplit((parts.scheme, host, parts.path or '/', parts.query, ''))

def compare(before, after):
    if normalize_url(before['url']) != normalize_url(after['url']) or before['scanProfile'] != after['scanProfile']:
        raise ValueError('Scans must use the same URL and scanner profile')
    for report in (before, after):
        if not isinstance(report['score'], int) or not 0 <= report['score'] <= 100 or not isinstance(report['issues'], list):
            raise ValueError('Invalid scan data')
    old = {i['rule_id']: i['title'] for i in before['issues']}
    new = {i['rule_id']: i['title'] for i in after['issues']}
    delta = after['score'] - before['score']
    return dict(beforeScanId=before['scanId'], afterScanId=after['scanId'], beforeDate=before['scannedAt'], afterDate=after['scannedAt'],
        beforeScore=before['score'], afterScore=after['score'], scoreChange=delta,
        beforeTotal=before['totalIssues'], afterTotal=after['totalIssues'], violationChange=after['totalIssues'] - before['totalIssues'],
        severities={s: {'before': before['severityCounts'][s], 'after': after['severityCounts'][s]} for s in ['critical', 'serious', 'moderate', 'minor']},
        resolved=[{'rule_id': r, 'title': old[r]} for r in sorted(old.keys() - new.keys())],
        remaining=[{'rule_id': r, 'title': new[r]} for r in sorted(old.keys() & new.keys())],
        new=[{'rule_id': r, 'title': new[r]} for r in sorted(new.keys() - old.keys())],
        summary=f"Score changed from {before['score']} to {after['score']} ({delta:+d} points). {len(old.keys() - new.keys())} rules resolved, {len(old.keys() & new.keys())} remaining, {len(new.keys() - old.keys())} newly detected.")

class ScanHistory:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self.connect()) as db, db:
            db.execute('CREATE TABLE IF NOT EXISTS scans (id TEXT PRIMARY KEY, url TEXT, profile TEXT, report TEXT)')

    def connect(self):
        return sqlite3.connect(self.path, timeout=15)

    def get(self, scan_id):
        with closing(self.connect()) as db, db:
            row = db.execute('SELECT report FROM scans WHERE id=?', (scan_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def save(self, report, previous_id=None):
        comparison = None
        notice = 'First scan retained. Scan this URL again after making fixes to compare results.'
        with closing(self.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            if previous_id:
                row = db.execute('SELECT report FROM scans WHERE id=?', (previous_id,)).fetchone()
                if row:
                    comparison = compare(json.loads(row[0]), report)
                else:
                    notice = 'Previous scan is unavailable. This scan has been retained as a new baseline.'
            # Browser-owned baseline IDs avoid comparing against another user's scan.
            db.execute('INSERT INTO scans VALUES (?, ?, ?, ?)', (report['scanId'], normalize_url(report['url']), report['scanProfile'], json.dumps(report)))
        return comparison, notice if not comparison else 'Compared by rule ID; occurrence counts may change within a remaining rule.'
