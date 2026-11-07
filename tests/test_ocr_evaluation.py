import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import evaluate_ocr as harness


def test_wilson_interval_is_bounded_and_needs_samples():
    assert harness.wilson_interval(0, 0) is None
    interval = harness.wilson_interval(8, 10)
    assert 0 <= interval['low'] < 0.8 < interval['high'] <= 1
    empty = harness.metric([None, None])
    assert empty['status'] == 'NOT_VERIFIED'
    assert empty['sampleCount'] == 0


def test_corpus_contract_covers_required_categories_and_hashes():
    corpus = harness.load_corpus(harness.DEFAULT_CORPUS)
    categories = {case['category'] for case in corpus['cases']}
    assert {'formula', 'matrix', 'integral', 'degraded', 'diagram'} <= categories
    assert len(corpus['cases']) >= 10
    for case in corpus['cases']:
        assert harness.sha256_file(ROOT / case['image']) == case['imageSha256']


def test_mock_mode_never_claims_ocr_accuracy(tmp_path):
    output = tmp_path / 'results.json'
    result = subprocess.run(
        [sys.executable, 'scripts/evaluate_ocr.py', '--mode', 'mock', '--no-render', '--output', str(output)],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr
    data = json.loads(output.read_text())
    assert data['measurement']['accuracyClaim'] is False
    assert data['measurement']['realModelRequestCount'] == 0
    assert data['measurement']['status'].startswith('HARNESS_ONLY_SYNTHETIC')
    assert data['summary']['semanticCorrect']['status'] == 'NOT_VERIFIED'
    assert data['summary']['diagramSemanticsCorrect']['status'] == 'NOT_VERIFIED'


def test_live_mode_is_refused_until_independent_corpus_review_exists(tmp_path):
    result = subprocess.run(
        [sys.executable, 'scripts/evaluate_ocr.py', '--mode', 'live', '--no-render', '--output', str(tmp_path/'r.json')],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert result.returncode != 0
    assert 'live mode requires --allow-paid' in (result.stderr + result.stdout)


def test_unsafe_latex_is_detected_separately_from_rendering():
    assert harness.unsafe_latex(r'\input{private.tex}') is True
    assert harness.unsafe_latex(r'\frac{1}{2}') is False


def test_diagram_is_excluded_from_formula_accuracy_metrics():
    corpus = harness.load_corpus(harness.DEFAULT_CORPUS)
    diagram = next(c for c in corpus['cases'] if c['category'] == 'diagram')
    record = {'raw': json.dumps({'text': 'triangle labels only', 'latex': ''}), 'source': 'synthetic'}
    evaluated = harness.evaluate_case(diagram, record, {}, None)
    assert evaluated['parseSuccess'] is True
    assert evaluated['textExact'] is None
    assert evaluated['latexExact'] is None
    assert evaluated['renderSuccess'] is None
    assert evaluated['diagramSemanticsCorrect'] is None