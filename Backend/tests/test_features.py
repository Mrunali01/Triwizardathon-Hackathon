import copy
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rag import WCAGIndex, chunks, DATA
from explain import explain, confidence, add_ai_summaries
from scanner import report_from_scan, PROFILE
from scan_history import ScanHistory, compare, normalize_url

def violation(rule='color-contrast', impact='serious'):
    return dict(id=rule, impact=impact, help=rule, description='Text has insufficient color contrast', tags=['wcag143'] if rule == 'color-contrast' else [],
                nodes=[dict(html='<p>Text</p>', target=['p'], failureSummary='Contrast ratio 2.1:1; expected 4.5:1', any=[{'id': rule, 'data': {'contrastRatio': 2.1}}])])

def report(scan_id, violations, index=None):
    with patch.dict(os.environ, {'ENABLE_LLM': 'false'}):
        result = report_from_scan({'violations': violations}, index)
    return dict(result, url='https://example.com/', scanId=scan_id, scannedAt='2026-09-14T00:00:00Z', scanTime='0.1s')

class RAGTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.index = WCAGIndex(database=Path(cls.temp.name) / 'vectors.sqlite')

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_ingested_versions_levels_and_metadata(self):
        docs = json.loads((DATA / 'wcag.json').read_text(encoding='utf-8'))
        self.assertEqual({d['version'] for d in docs}, {'2.1', '2.2'})
        self.assertEqual({d['level'] for d in docs}, {'A', 'AA', 'AAA'})
        self.assertGreater(len(docs), 150)
        self.assertTrue(all(d['source'].startswith('https://www.w3.org/') for d in docs))
        self.assertFalse(any(d['criterion'] == '4.1.1' and d['version'] == '2.2' for d in docs))

    def test_chunk_overlap_and_metadata(self):
        doc = {'text': 'one two three four five six seven', 'criterion': '1.1.1'}
        result = list(chunks(doc, 4, 1))
        self.assertEqual(result[1]['text'], 'four five six seven')
        self.assertTrue(all(c['criterion'] == '1.1.1' for c in result))

    def test_contrast_retrieval(self):
        hits = self.index.retrieve('insufficient color contrast', 'color-contrast')
        self.assertEqual(hits[0]['criterion'], '1.4.3')
        self.assertEqual(hits[0]['level'], 'AA')
        self.assertIn('4.5:1', hits[0]['text'])

    def test_label_retrieval(self):
        hits = self.index.retrieve('missing form label', 'label')
        self.assertTrue(hits)
        self.assertTrue(all(e['criterion'] in ['1.3.1', '4.1.2'] for e in hits))

    def test_tag_retrieval(self):
        hits = self.index.retrieve('input purpose', 'autocomplete-valid', ['wcag135'])
        self.assertEqual(hits[0]['criterion'], '1.3.5')

    def test_low_confidence_retrieval(self):
        self.assertEqual(self.index.retrieve('zzzyxquux alien quantum pizza', 'unknown'), [])

    def test_persistent_vectors(self):
        again = WCAGIndex(database=Path(self.temp.name) / 'vectors.sqlite')
        self.assertEqual(again.retrieve('contrast', 'color-contrast'), self.index.retrieve('contrast', 'color-contrast'))

    def test_explanation_grounding_and_confidence(self):
        e = explain(violation(), self.index)
        self.assertEqual(e.wcag_criteria, ['1.4.3'])
        self.assertEqual(e.confidence, 'High')
        self.assertIn('4.5:1', e.recommendation)
        self.assertTrue(e.affected_users)
        self.assertTrue(e.reasoning_summary)
        self.assertEqual(e.confidence_score, explain(violation(), self.index).confidence_score)

    def test_retrieval_failure(self):
        with patch.object(self.index, 'retrieve', side_effect=RuntimeError('offline')):
            e = explain(violation(), self.index)
        self.assertEqual(e.confidence, 'Low')
        self.assertEqual(e.wcag_criteria, [])
        self.assertIn('manual review', e.status)

    def test_similarity_alone_not_confirmed(self):
        hit = self.index.retrieve('contrast', 'color-contrast')[0]
        hit.update(criterion_match=False, rule_match=False)
        with patch.object(self.index, 'retrieve', return_value=[hit]):
            e = explain(violation('unknown'), self.index)
        self.assertEqual(e.wcag_criteria, [])
        self.assertEqual(e.confidence, 'Low')

    def test_llm_failure_preserves_results(self):
        issue = report('x', [violation()], self.index)['issues'][0]
        with patch.dict(os.environ, {'ENABLE_LLM': 'true', 'OPENAI_API_KEY': 'test'}), patch('langchain_openai.ChatOpenAI.invoke', side_effect=RuntimeError('offline')):
            status = add_ai_summaries([issue])
        self.assertIn('unavailable', status)
        self.assertEqual(issue['explanation']['wcag_criteria'], ['1.4.3'])

    def test_llm_fabrication_rejected(self):
        issue = report('x', [violation()], self.index)['issues'][0]
        response = type('Response', (), {'content': json.dumps([dict(rule_id='color-contrast', evidence_indices=[0], scanner_quote=issue['description'], guidance_quote='Invented criterion 9.9.9')])})()
        with patch.dict(os.environ, {'ENABLE_LLM': 'true', 'OPENAI_API_KEY': 'test'}), patch('langchain_openai.ChatOpenAI.invoke', return_value=response):
            add_ai_summaries([issue])
        self.assertIsNone(issue['explanation']['ai_summary'])

    def test_llm_valid_evidence_accepted(self):
        issue = report('x', [violation()], self.index)['issues'][0]
        response = type('Response', (), {'content': json.dumps([dict(rule_id='color-contrast', evidence_indices=[0], scanner_quote=issue['description'], guidance_quote=issue['explanation']['evidence'][0]['text'][:100])])})()
        with patch.dict(os.environ, {'ENABLE_LLM': 'true', 'OPENAI_API_KEY': 'test'}), patch('langchain_openai.ChatOpenAI.invoke', return_value=response):
            add_ai_summaries([issue])
        self.assertIn('Scanner:', issue['explanation']['ai_summary'])

class ScannerReadinessTests(unittest.TestCase):
    def test_delayed_spa_content_is_scanned(self):
        from playwright.sync_api import sync_playwright
        from scanner import wait_for_rendered_content, AXE
        with sync_playwright() as p:
            browser = p.chromium.launch()
            try:
                page = browser.new_page()
                page.set_content('<html lang="en"><head><title>SPA fixture</title></head><body><script>setTimeout(() => { document.body.innerHTML = "<main><h1>Ready</h1><button></button></main>"; }, 700)</script></body></html>')
                self.assertTrue(wait_for_rendered_content(page))
                page.add_script_tag(path=str(AXE))
                rules = page.evaluate('async () => (await axe.run()).violations.map(v => v.id)')
                self.assertIn('button-name', rules)
                self.assertNotIn('page-has-heading-one', rules)
            finally:
                browser.close()

    def test_blank_shell_does_not_receive_score(self):
        from scanner import wait_for_rendered_content, ScanError, PlaywrightTimeout
        from unittest.mock import Mock
        page = Mock()
        page.wait_for_function.side_effect = PlaywrightTimeout('blank')
        with self.assertRaisesRegex(ScanError, 'No accessibility score'):
            wait_for_rendered_content(page)


    def test_loaded_dom_does_not_require_network_idle(self):
        from scanner import scan_page
        with patch('scanner.sync_playwright') as playwright:
            browser = playwright.return_value.__enter__.return_value.chromium.launch.return_value
            page = browser.new_page.return_value
            page.goto.return_value.status = 200
            page.evaluate.return_value = {'violations': []}
            result = scan_page('https://example.com')
            self.assertEqual(page.goto.call_args.kwargs['wait_until'], 'domcontentloaded')
            self.assertEqual(result['loadWarning'], '')
            browser.close.assert_called_once()

    def test_slow_resources_keep_results_with_warning(self):
        from scanner import scan_page, PlaywrightTimeout
        with patch('scanner.sync_playwright') as playwright:
            page = playwright.return_value.__enter__.return_value.chromium.launch.return_value.new_page.return_value
            page.goto.return_value.status = 200
            page.wait_for_load_state.side_effect = PlaywrightTimeout('slow resources')
            page.evaluate.return_value = {'violations': []}
            result = scan_page('https://example.com')
            self.assertIn('resources', result['loadWarning'])
            self.assertEqual(result['violations'], [])

    def test_navigation_timeout_is_actionable(self):
        from scanner import scan_page, ScanError, PlaywrightTimeout
        with patch('scanner._scan_page', side_effect=PlaywrightTimeout('timeout')):
            with self.assertRaisesRegex(ScanError, 'timed out'):
                scan_page('https://example.com')

    def test_network_failure_is_actionable(self):
        from scanner import scan_page, ScanError, PlaywrightError
        with patch('scanner._scan_page', side_effect=PlaywrightError('Page.goto: net::ERR_NAME_NOT_RESOLVED')):
            with self.assertRaisesRegex(ScanError, 'ERR_NAME_NOT_RESOLVED'):
                scan_page('https://example.com')


class ComparisonTests(unittest.TestCase):
    def setUp(self):
        self.before = report('before', [violation('image-alt', 'critical'), violation()])
        self.after = report('after', [violation(), violation('document-title', 'moderate')])

    def test_score_counts_and_rule_sets(self):
        c = compare(self.before, self.after)
        self.assertEqual(c['scoreChange'], 8)
        self.assertEqual(c['violationChange'], 0)
        self.assertEqual(c['resolved'][0]['rule_id'], 'image-alt')
        self.assertEqual(c['remaining'][0]['rule_id'], 'color-contrast')
        self.assertEqual(c['new'][0]['rule_id'], 'document-title')
        self.assertEqual(c['severities']['critical'], {'before': 1, 'after': 0})

    def test_occurrence_counts_and_clamping(self):
        v = violation()
        v['nodes'] *= 10
        r = report('a', [v])
        self.assertEqual(r['score'], 0)
        self.assertEqual(r['totalIssues'], 10)
        self.assertEqual(r['severityCounts']['serious'], 10)

    def test_empty_scan(self):
        empty = report('b', [])
        c = compare(self.before, empty)
        self.assertEqual(empty['score'], 100)
        self.assertEqual(len(c['resolved']), 2)

    def test_different_urls_and_profiles(self):
        for field, value in [('url', 'https://elsewhere.test'), ('scanProfile', 'other')]:
            altered = {**self.after, field: value}
            with self.assertRaises(ValueError):
                compare(self.before, altered)

    def test_invalid_scan(self):
        with self.assertRaises(ValueError):
            report_from_scan({'violations': None}, None)
        with self.assertRaises(ValueError):
            compare(self.before, {**self.after, 'score': 101})

    def test_persistence_and_missing_baseline(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'history.sqlite'
            store = ScanHistory(path)
            c, _ = store.save(self.before)
            self.assertIsNone(c)
            self.assertEqual(ScanHistory(path).get('before')['score'], self.before['score'])
            c, _ = store.save(self.after, 'before')
            self.assertEqual(c['scoreChange'], 8)
            c, notice = store.save({**self.after, 'scanId': 'third'}, 'missing')
            self.assertIsNone(c)
            self.assertIn('unavailable', notice)

    def test_url_normalization(self):
        self.assertEqual(normalize_url('https://EXAMPLE.com:443#x'), 'https://example.com/')
        self.assertNotEqual(normalize_url('https://example.com/?a=1'), normalize_url('https://example.com/?a=2'))
        with self.assertRaises(ValueError):
            normalize_url('file:///etc/passwd')

class APITests(unittest.TestCase):
    def test_scan_and_history_endpoints(self):
        from fastapi.testclient import TestClient
        import backend
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {'SCAN_DB_PATH': str(Path(temp) / 'scans.sqlite'), 'ENABLE_LLM': 'false'}), patch('backend.scan_page', return_value={'violations': [violation()]}):
            client = TestClient(backend.api)
            first = client.post('/check-accessibility', json={'url': 'https://example.com'})
            self.assertEqual(first.status_code, 200, first.text)
            scan = first.json()
            second = client.post('/check-accessibility', json={'url': 'https://example.com', 'previous_scan_id': scan['scanId']})
            self.assertEqual(second.json()['comparison']['scoreChange'], 0)
            self.assertEqual(client.get('/scans/' + scan['scanId']).status_code, 200)
            self.assertEqual(client.get('/scans/missing').status_code, 404)
            self.assertEqual(client.post('/check-accessibility', json={'url': 'file:///tmp/x'}).status_code, 422)
            self.assertEqual(client.post('/check-accessibility', json={'url': 'https://different.test', 'previous_scan_id': scan['scanId']}).status_code, 422)

if __name__ == '__main__':
    unittest.main()
