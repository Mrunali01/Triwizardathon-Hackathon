"""Local sparse TF-IDF embeddings, SQLite vector storage and metadata-aware retrieval."""
from contextlib import closing
import hashlib
import json
import math
import re
import sqlite3
from collections import Counter
from pathlib import Path

DATA = Path(__file__).parent / 'data'
RULE_CRITERIA = {
    'color-contrast': ['1.4.3'], 'color-contrast-enhanced': ['1.4.6'],
    'label': ['1.3.1', '4.1.2'], 'image-alt': ['1.1.1'],
    'button-name': ['4.1.2'], 'link-name': ['2.4.4'],
    'document-title': ['2.4.2'], 'html-has-lang': ['3.1.1'],
    'html-lang-valid': ['3.1.1'], 'select-name': ['4.1.2'],
}

def tokens(text):
    return re.findall(r'[a-z0-9]+', text.lower())

def chunks(document, size=180, overlap=30):
    words = document['text'].split()
    if size <= overlap or overlap < 0:
        raise ValueError('Invalid chunk size/overlap')
    for i in range(0, len(words), size - overlap):
        yield {**document, 'text': ' '.join(words[i:i + size]), 'chunk': i // (size - overlap)}
        if i + size >= len(words):
            break

class WCAGIndex:
    def __init__(self, corpus=DATA / 'wcag.json', database=DATA / 'wcag.sqlite'):
        raw = Path(corpus).read_bytes()
        self.documents = [c for d in json.loads(raw) for c in chunks(d)]
        frequency = Counter(t for d in self.documents for t in set(tokens(d['title'] + ' ' + d['text'])))
        self.idf = {t: math.log((1 + len(self.documents)) / (1 + n)) + 1 for t, n in frequency.items()}
        Path(database).parent.mkdir(parents=True, exist_ok=True)
        fingerprint = hashlib.sha256(b'tfidf-v1-180-30' + raw).hexdigest()
        with closing(sqlite3.connect(database)) as db, db:
            db.execute('CREATE TABLE IF NOT EXISTS vectors (id INTEGER PRIMARY KEY, document TEXT, embedding TEXT)')
            db.execute('CREATE TABLE IF NOT EXISTS metadata (fingerprint TEXT)')
            if db.execute('SELECT fingerprint FROM metadata').fetchone() != (fingerprint,):
                db.execute('DELETE FROM vectors')
                db.execute('DELETE FROM metadata')
                db.executemany('INSERT INTO vectors VALUES (?, ?, ?)', [
                    (i, json.dumps(d), json.dumps(self.embed(d['title'] + ' ' + d['text'])))
                    for i, d in enumerate(self.documents)])
                db.execute('INSERT INTO metadata VALUES (?)', (fingerprint,))
            self.vectors = [(json.loads(d), json.loads(v)) for d, v in db.execute('SELECT document, embedding FROM vectors ORDER BY id')]

    def embed(self, text):
        counts = Counter(tokens(text))
        vector = {t: (1 + math.log(n)) * self.idf[t] for t, n in counts.items() if t in self.idf}
        norm = math.sqrt(sum(v * v for v in vector.values())) or 1
        return {t: v / norm for t, v in vector.items()}

    def retrieve(self, query, rule_id='', tags=(), limit=3):
        criteria = set(RULE_CRITERIA.get(rule_id, []))
        for tag in tags:
            match = re.fullmatch(r'wcag(\d)(\d)(\d{1,2})', tag)
            if match:
                criteria.add('.'.join(match.groups()))
        vector = self.embed(query.replace('-', ' '))
        ranked = []
        for doc, embedding in self.vectors:
            if doc['version'] != '2.2':
                continue
            similarity = sum(v * embedding.get(t, 0) for t, v in vector.items())
            matched = doc['criterion'] in criteria
            if criteria and not matched:
                continue
            if not matched and similarity < 0.32:
                continue
            ranked.append({**doc, 'similarity': round(similarity, 4), 'criterion_match': matched,
                           'rule_match': doc['criterion'] in RULE_CRITERIA.get(rule_id, [])})
        ranked.sort(key=lambda d: (d['criterion_match'], d['similarity']), reverse=True)
        return ranked[:limit]
