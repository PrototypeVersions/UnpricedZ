import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from site_tools.build_context import build


def fixture(tmp_path):
    directory = tmp_path / 'risk_records/risk-1.0.0/forecasts'
    directory.mkdir(parents=True)
    snap = {'forecastId': 'risk-1.0.0:2026-11-03', 'sessionDate': '2026-11-03',
            'issuedAt': '2026-11-04T02:00:00Z', 'entryDate': '2026-11-04',
            'exitDate': '2026-11-10', 'forecasts': [{'ticker': 'SPY', 'variance': {'ewma': 0.001}}]}
    frozen = directory / '2026-11-03.json'
    frozen.write_text(json.dumps(snap))
    digest = hashlib.sha256(frozen.read_bytes()).hexdigest()
    report = {'experiment': 'risk-1.0.0', 'latest': snap, 'updatedAt': '2026-11-04T02:00:00Z',
              'history': [{'path': str(frozen.relative_to(tmp_path)), 'sessionDate': '2026-11-03',
                           'fileSha256': digest, 'resolved': False}]}
    (tmp_path / 'site/data').mkdir(parents=True)
    public = tmp_path / 'site/data/risk.json'
    public.write_text(json.dumps(report))
    return frozen, public, report


def test_context_reads_without_mutating_the_record(tmp_path):
    frozen, public, report = fixture(tmp_path)
    before = frozen.read_bytes(), public.read_bytes()
    context = build(tmp_path, datetime(2026, 11, 5, tzinfo=timezone.utc), calendar=[])
    assert before == (frozen.read_bytes(), public.read_bytes())
    assert context['forecastId'] == report['latest']['forecastId']
    assert context['riskUpdatedAt'] == report['updatedAt']
    assert 'outcomes' not in context['history'][0]


def test_display_refuses_a_changed_frozen_file(tmp_path):
    frozen, _, _ = fixture(tmp_path)
    frozen.write_text(frozen.read_text() + '\n')
    with pytest.raises(ValueError, match='public hash'):
        build(tmp_path, calendar=[])


def test_resolved_outcomes_require_the_exact_forecast(tmp_path):
    frozen, public, report = fixture(tmp_path)
    report['history'][0]['resolved'] = True
    public.write_text(json.dumps(report))
    directory = frozen.parent.parent / 'resolutions'
    directory.mkdir()
    resolution = {'forecastId': report['latest']['forecastId'],
                  'forecastFileSha256': report['history'][0]['fileSha256'],
                  'rows': [{'ticker': 'SPY', 'realizedVariance': 0.002, 'drawdownSeverity': 0.04, 'drawdownEvent': 1}]}
    (directory / frozen.name).write_text(json.dumps(resolution))
    context = build(tmp_path, calendar=[])
    assert context['history'][0]['outcomes'][0]['drawdownSeverity'] == 0.04
    resolution['forecastFileSha256'] = 'different'
    (directory / frozen.name).write_text(json.dumps(resolution))
    with pytest.raises(ValueError, match='different frozen forecast'):
        build(tmp_path, calendar=[])


def test_calendar_carries_holidays_early_closes_and_dst(tmp_path):
    fixture(tmp_path)
    context = build(tmp_path, datetime(2026, 11, 5, tzinfo=timezone.utc))
    sessions = {r['date']: r for r in context['calendar']['sessions']}
    assert '2026-11-26' not in sessions  # Thanksgiving
    assert sessions['2026-11-27']['close'].startswith('2026-11-27T18:00:00')
    assert sessions['2026-10-30']['open'].startswith('2026-10-30T13:30:00')
    assert sessions['2026-11-02']['open'].startswith('2026-11-02T14:30:00')
    assert '2026-11-11' in sessions  # NYSE is open on Veterans Day
