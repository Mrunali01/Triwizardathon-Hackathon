"""Refresh the checked-in W3C corpus. Runtime scanning requires no W3C network access."""
import json
import re
from pathlib import Path
import requests
from bs4 import BeautifulSoup

TARGET = Path(__file__).parent / 'data' / 'wcag.json'

def ingest():
    documents = []
    for version in ('2.1', '2.2'):
        source = f'https://www.w3.org/TR/WCAG{version.replace(".", "")}/'
        response = requests.get(source, timeout=45)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        for section in soup.select('section'):
            heading = section.find(['h4'], recursive=False) or section.select_one(':scope > .header-wrapper > h4')
            level = section.select_one(':scope > .conformance-level')
            if not heading or not level:
                continue
            title = heading.get_text(' ', strip=True)
            match = re.search(r'\d+\.\d+\.\d+', title)
            if not match:
                continue
            criterion = match.group()
            if version == '2.2' and criterion == '4.1.1':
                continue  # Removed from WCAG 2.2.
            for links in section.select('.doclinks, .header-wrapper'):
                links.decompose()
            documents.append(dict(standard='WCAG', version=version, criterion=criterion,
                level=re.search(r'AAA|AA|A', level.get_text()).group(),
                category=section['id'], title=title, source=source + '#' + section['id'],
                text=section.get_text(' ', strip=True), kind='success-criterion'))
    for technique, criterion in [('H44', '1.3.1'), ('H37', '1.1.1'), ('ARIA14', '4.1.2')]:
        technology = 'aria' if technique.startswith('ARIA') else 'html'
        source = f'https://www.w3.org/WAI/WCAG22/Techniques/{technology}/{technique}'
        response = requests.get(source, timeout=45)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        main = soup.select_one('main')
        documents.append(dict(standard='WCAG', version='2.2', criterion=criterion, level='A',
            category=technology, title=technique, source=source,
            text=main.get_text(' ', strip=True), kind='technique'))
    if len(documents) < 150:
        raise ValueError('Incomplete WCAG download; existing corpus was not changed')
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(json.dumps(documents, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Ingested {len(documents)} W3C documents into {TARGET}')

if __name__ == '__main__':
    ingest()
