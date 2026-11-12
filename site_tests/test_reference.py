import hashlib
import json
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

import pytest

# This presentation dependency is deliberately outside frozen research environments.
pytest.importorskip('markdown')

from site_tools.build_reference import DocumentHTML, build, reader_context


def put(root, path, value):
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(value if isinstance(value, str) else json.dumps(value))
    return target


def fixture(root):
    put(root, 'config.json', {'experiment': 'research-2.0.0', 'portfolio': {'minimumProbability': .55}})
    put(root, 'site/data/live.json', {'updatedAt': '2026-11-05T01:00:00Z',
                                    'latest': {'sessionDate': '2026-11-04'},
                                    'portfolio': {'plans': [{'signalDate': '2026-11-03', 'allocations': [], 'cashWeight': 1}]}})
    put(root, 'site/data/risk.json', {'latest': {'forecastId': 'risk:2026-11-04'}})
    put(root, 'records/forecasts/2026-11-03.json', {'experiment': 'research-2.0.0', 'snapshotId': 'actual-plan',
                                                 'sessionDate': '2026-11-03', 'forecasts': [{'ticker': 'XLB', 'p_logistic': .49}]})
    put(root, 'records/forecasts/2026-11-04.json', {'experiment': 'research-2.0.0', 'snapshotId': 'newer-not-the-plan'})


def test_plan_explanation_uses_original_signal_not_newer_daily_forecast(tmp_path):
    fixture(tmp_path)
    result = reader_context(tmp_path)
    assert result['portfolioDecision']['snapshotId'] == 'actual-plan'
    assert result['portfolioDecision']['forecasts'][0]['p_logistic'] == .49
    assert result['liveUpdatedAt'] == '2026-11-05T01:00:00Z'
    put(tmp_path, 'records/forecasts/2026-11-03.json', {'experiment': 'another-version'})
    assert reader_context(tmp_path)['portfolioDecision'] is None


def test_hub_receipt_preserves_lateness_and_checks_exact_export_bytes(tmp_path):
    fixture(tmp_path)
    path = put(tmp_path, 'site/data/export/latest-variance.json', {'forecastId': 'export:variance', 'task': {'description': 'Variance'}})
    receipt = {'forecastId': 'export:variance', 'status': 'late', 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
    hub = {'updatedAt': '2026-11-05', 'labs': [{'id': 'risk-lab', 'recent': [receipt]}]}
    row = reader_context(tmp_path, hub)['hub']['exports'][0]
    assert row['receipt']['status'] == 'late'
    assert row['matches'] is True
    path.write_text(path.read_text() + '\n')
    assert reader_context(tmp_path, hub)['hub']['exports'][0]['matches'] is False
    assert reader_context(tmp_path)['hub']['status'] == 'unavailable'


def test_full_reader_preserves_original_reports_and_hashes(tmp_path):
    fixture(tmp_path)
    report = put(tmp_path, 'site/data/program.json', '{\n  "result": "negative", "loss": 25.12044, "unsafe": "<script>alert(1)</script>"\n}\n')
    doc = put(tmp_path, 'docs/PROTOCOL.md', '# Protocol\n\n[Settings](../config.json)\n\n[Report](../site/data/program.json)\n')
    originals = {p: p.read_bytes() for p in [report, doc]}
    manifest = build(tmp_path)
    for path, raw in originals.items():
        source = path.relative_to(tmp_path).as_posix()
        assert path.read_bytes() == raw
        assert (tmp_path / 'site/reference/raw' / source).read_bytes() == raw
        assert next(m['sha256'] for m in manifest if m['source'] == source) == hashlib.sha256(raw).hexdigest()
    text = (tmp_path / 'site/reference/site/data/program.html').read_text()
    assert '25.12044' in text and 'negative' in text
    assert '<script>' not in text and '&lt;script&gt;' in text
    text = (tmp_path / 'site/reference/docs/PROTOCOL.html').read_text()
    assert 'href="../config.html"' in text
    assert 'href="../site/data/program.html"' in text


def test_document_markup_is_inert_and_export_links_use_correct_depth():
    parser = DocumentHTML('docs/PROTOCOL.md', {'config.json'})
    parser.feed('<p onclick="alert(1)">Text<script>alert(2)</script><a href="javascript:alert(3)">No</a></p>')
    result = ''.join(parser.output)
    assert '<script' not in result and 'onclick' not in result and 'javascript:' not in result
    assert parser.link('../site/data/export/latest-risk.json') == '../../data/export/latest-risk.json'
    assert parser.link('../config.json') == '../config.html'


def test_repository_links_are_local_and_source_archives_have_readers(tmp_path):
    fixture(tmp_path)
    put(tmp_path, 'unpriced/controls.py', 'print("<test>")\n')
    input_file = tmp_path / 'archive/inputs/sample.csv.gz'
    input_file.parent.mkdir(parents=True, exist_ok=True)
    input_file.write_bytes(b'\x1f\x8b\x08sample')
    put(tmp_path, 'docs/SOURCES.md', (
        '# Local research readers\n'
        '[Controls](../unpriced/controls.py)\n'
        '[Input](https://github.com/PrototypeVersions/UnpricedZ/blob/main/archive/inputs/sample.csv.gz)\n'
        '[Workflow](https://github.com/PrototypeVersions/UnpricedZ/actions)\n'
    ))
    build(tmp_path)
    reader = (tmp_path / 'site/reference/docs/SOURCES.html').read_text()
    assert 'href="../unpriced/controls.html"' in reader
    assert 'href="../archive/inputs/sample.csv.html"' in reader
    assert 'github.com/' not in reader
    assert '<a>Workflow</a>' in reader
    source = (tmp_path / 'site/reference/unpriced/controls.html').read_text()
    assert '&lt;test&gt;' in source
    binary = (tmp_path / 'site/reference/archive/inputs/sample.csv.html').read_text()
    assert 'SHA-256' in binary and 'Download the original file' in binary
    assert (tmp_path / 'site/reference/raw/archive/inputs/sample.csv.gz').read_bytes() == input_file.read_bytes()
    assert 'github.com/' not in binary



def test_internal_docs_and_github_help_are_omitted_from_public_navigation(tmp_path):
    setup = put(tmp_path, 'docs/FRED_SETUP.md', '# FRED setup\n')
    put(tmp_path, 'docs/OPERATIONS.md', '# Operations\n')
    put(tmp_path, 'docs/CROSS_LAB_REPLY_2026-11-05.md', '# Cross-lab reply\n')
    public = put(tmp_path, 'docs/PUBLIC.md', (
        '# Research\n\n[Setup](FRED_SETUP.md)\n\n'
        '[Secrets help](https://docs.github.com/en/actions/security-guides/using-secrets-in-github-actions)\n\n'
        '[Another lab](https://prototypeversions.github.io/UnpricedX/)\n\n'
        'The tests passed in GitHub Actions.\n'
    ))
    # Simulate a rebuild in a directory that still has copies from an earlier build.
    stale_page = put(tmp_path, 'site/reference/docs/FRED_SETUP.html', '<h1>FRED setup</h1>')
    stale_download = put(tmp_path, 'site/reference/raw/docs/FRED_SETUP.md', setup.read_text())
    (tmp_path / 'site/data').mkdir()
    output = tmp_path / 'site/reference'
    assert [entry['source'] for entry in build(tmp_path)] == ['docs/PUBLIC.md']
    assert not stale_page.exists() and not stale_download.exists()
    assert setup.is_file()
    assert 'FRED_SETUP' not in (output / 'index.html').read_text()
    reader = (output / 'docs/PUBLIC.html').read_text()
    assert '<a>Setup</a>' in reader and '<a>Secrets help</a>' in reader
    assert 'href="https://prototypeversions.github.io/UnpricedX/"' in reader
    assert 'passed in the automated test pipeline' in reader
    assert (output / 'raw/docs/PUBLIC.md').read_bytes() == public.read_bytes()


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        self.links += [v for k, v in attrs if k in ('href', 'src')]


def test_generated_reference_navigation_and_download_links_resolve(tmp_path):
    fixture(tmp_path)
    put(tmp_path, 'docs/PROTOCOL.md', '# Protocol\n\n[Settings](../config.json)\n')
    put(tmp_path, 'site/styles.css', '')
    put(tmp_path, 'site/assets/favicon-paper-ink-v2.svg', '')
    put(tmp_path, 'site/assets/unpriced-paper-ink-icon-v1.png', '')
    build(tmp_path)
    for page in (tmp_path / 'site/reference').rglob('*.html'):
        parser = Links()
        parser.feed(page.read_text())
        for href in parser.links:
            parsed = urlsplit(href)
            if not parsed.scheme and parsed.path:
                assert (page.parent / parsed.path).exists(), (page, href)
