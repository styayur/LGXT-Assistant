#!/usr/bin/env python3
"""Evidence-bound OCR evaluation harness for LGXT Assistant.

Mock and replay modes never become an OCR accuracy claim. Live mode is refused
unless an approved provider profile and independently verified corpus review are
supplied. Requests are sequential, bounded and never retried.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
import mimetypes
import os
import re
import subprocess
import sys
import threading
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from mobile.src.question_documents import parse_recognition  # noqa: E402

TOOL_NAME = 'LGXT OCR Evaluation Harness'
TOOL_VERSION = '1.0.0'
DEFAULT_CORPUS = ROOT / 'docs/research/ocr-eval/corpus.json'
DEFAULT_OUTPUT = ROOT / 'docs/research/ocr-eval/results.json'
DEFAULT_MOCK = ROOT / 'docs/research/ocr-eval/mock-responses.jsonl'
UNSAFE_LATEX = re.compile(
    r'\\(?:input|include|includeonly|includegraphics|includepdf|usepackage|documentclass|'
    r'write18|openout|read|catcode|csname|href|url|htmlClass|htmlId|htmlStyle)\b'
)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def normalize_text(value: str) -> str:
    value = value.replace('\r\n', '\n').replace('\r', '\n')
    value = re.sub(r'\s+', ' ', value).strip().casefold()
    return value


def normalize_latex(value: str) -> str:
    value = re.sub(r'\s+', '', value)
    value = value.replace('\\left', '').replace('\\right', '')
    value = re.sub(r'\\,|\\!|\\;|\\:', '', value)
    return value


def unsafe_latex(value: str) -> bool:
    return bool(UNSAFE_LATEX.search(value or ''))


def wilson_interval(successes: int, total: int, z: float = 1.959963984540054):
    if total <= 0:
        return None
    p = successes / total
    denom = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / denom
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * total)) / total) / denom
    return {'low': max(0.0, centre - margin), 'high': min(1.0, centre + margin)}


def metric(values):
    available = [v for v in values if isinstance(v, bool)]
    if not available:
        return {'sampleCount': 0, 'successCount': 0, 'rate': None, 'ci95': None, 'status': 'NOT_VERIFIED'}
    successes = sum(available)
    return {
        'sampleCount': len(available),
        'successCount': successes,
        'rate': successes / len(available),
        'ci95': wilson_interval(successes, len(available)),
        'status': 'MEASURED',
    }


def load_json(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))


def git_commit() -> str | None:
    try:
        return subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    except Exception:
        return None


def load_corpus(path: Path):
    corpus = load_json(path)
    if corpus.get('schemaVersion') != 1:
        raise ValueError('unsupported corpus schemaVersion')
    cases = corpus.get('cases')
    if not isinstance(cases, list) or len(cases) < 10:
        raise ValueError('corpus must contain at least 10 cases')
    ids = [c.get('id') for c in cases]
    if len(ids) != len(set(ids)) or not all(isinstance(x, str) and x for x in ids):
        raise ValueError('corpus case ids must be unique non-empty strings')
    categories = {c.get('category') for c in cases}
    required = {'formula', 'matrix', 'integral', 'degraded', 'diagram'}
    missing = sorted(required - categories)
    if missing:
        raise ValueError(f'corpus missing required categories: {missing}')
    for case in cases:
        image = ROOT / case['image']
        if not image.is_file():
            raise ValueError(f"missing image for {case['id']}: {image}")
        digest = sha256_file(image)
        if case.get('imageSha256') != digest:
            raise ValueError(f"image hash mismatch for {case['id']}")
        gt = case.get('groundTruth') or {}
        if not isinstance(gt, dict):
            raise ValueError(f"invalid groundTruth for {case['id']}")
        if case['category'] != 'diagram' and not (gt.get('text') or gt.get('latex')):
            raise ValueError(f"non-diagram case lacks ground truth: {case['id']}")
    return corpus


def load_review(corpus_sha: str, path: Path | None = None):
    review_path = path or (DEFAULT_CORPUS.parent / 'corpus-review.json')
    review = load_json(review_path)
    status = review.get('status')
    valid = (
        status == 'VERIFIED'
        and review.get('corpusSha256') == corpus_sha
        and bool(review.get('independentReviewer'))
        and review.get('reviewedAt')
    )
    return review_path, review, valid


def load_jsonl(path: Path):
    meta = {}
    records = {}
    for line_number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        value = json.loads(line)
        if '_meta' in value:
            meta = dict(value['_meta'])
            continue
        case_id = value.get('caseId')
        if not isinstance(case_id, str) or not case_id:
            raise ValueError(f'line {line_number}: missing caseId')
        if case_id in records:
            raise ValueError(f'duplicate response for {case_id}')
        records[case_id] = value
    return meta, records


def load_manual_reviews(path: Path | None, corpus_sha: str):
    if path is None:
        return {}
    value = load_json(path)
    if value.get('corpusSha256') != corpus_sha:
        raise ValueError('manual review corpusSha256 does not match corpus')
    if not value.get('independentReviewer'):
        raise ValueError('manual review must name an independent reviewer')
    reviews = value.get('cases')
    if not isinstance(reviews, dict):
        raise ValueError('manual review cases must be an object')
    for case_id, review in reviews.items():
        if not isinstance(review, dict):
            raise ValueError(f'invalid manual review for {case_id}')
    return reviews


def image_data_url(path: Path) -> str:
    mime = mimetypes.guess_type(path.name)[0]
    if mime not in ('image/png', 'image/jpeg', 'image/webp'):
        raise ValueError(f'unsupported image type: {path}')
    return f'data:{mime};base64,' + base64.b64encode(path.read_bytes()).decode('ascii')


def build_messages(provider: str, image: Path):
    prompt = ('Return only JSON with exactly two string fields, text and latex. '
              'Transcribe all visible printed text and formulas. Do not solve. '
              'For a diagram, transcribe labels and return an empty latex string when no formula is present.')
    url = image_data_url(image)
    if provider == 'Claude':
        _, encoded = url.split(',', 1)
        content = [
            {'type': 'image', 'source': {'type': 'base64', 'media_type': mimetypes.guess_type(image.name)[0], 'data': encoded}},
            {'type': 'text', 'text': prompt},
        ]
    else:
        content = [
            {'type': 'text', 'text': prompt},
            {'type': 'image_url', 'image_url': {'url': url}},
        ]
    return [{'role': 'user', 'content': content}]


def live_request(profile: dict, image: Path, api_key: str | None) -> str:
    from mobile.src import model_transport
    settings = {
        'provider': profile['provider'],
        'endpoint': profile['endpoint'],
        'model': profile['model'],
        'temperature': profile.get('temperature', 0),
        'maxTokens': profile.get('maxTokens', 4096),
        'visionEnabled': True,
    }
    chunks = []
    for chunk in model_transport.stream(settings, api_key, build_messages(profile['provider'], image), threading.Event()):
        chunks.append(chunk)
        if sum(len(x) for x in chunks) > 64000:
            raise ValueError('live model response exceeded 64,000 characters')
    raw = ''.join(chunks)
    if not raw:
        raise ValueError('live model returned an empty response')
    return raw


def make_renderer(enabled: bool):
    if not enabled:
        return None
    try:
        from playwright.sync_api import sync_playwright
        browser = sync_playwright().start()
        browser_obj = browser.chromium.launch(headless=True)
        page = browser_obj.new_page(viewport={'width': 800, 'height': 400}, device_scale_factor=1)
        page.set_content('<!DOCTYPE html><html><body><div id="formula"></div></body></html>')
        page.add_style_tag(path=str(ROOT / 'frontend/node_modules/katex/dist/katex.min.css'))
        page.add_script_tag(path=str(ROOT / 'frontend/node_modules/katex/dist/katex.min.js'))

        def render(latex: str):
            if unsafe_latex(latex):
                return False
            return bool(page.evaluate(
                "tex => {try {katex.renderToString(tex,{throwOnError:true,trust:false,maxExpand:1000,maxSize:20});return true;}catch(e){return false;}}",
                latex,
            ))

        def close():
            browser_obj.close()
            browser.stop()

        return render, close
    except Exception as exc:
        raise RuntimeError(f'render requested but Playwright/KaTeX could not start: {exc}') from exc


def approved_profile(path: Path, case_count: int):
    profile = load_json(path)
    required = ('provider', 'model', 'endpoint', 'approvedBy', 'approvedAt', 'authorizationRef')
    missing = [k for k in required if not profile.get(k)]
    if profile.get('status') != 'APPROVED' or missing:
        raise ValueError(f'provider profile is not approved or is incomplete: missing={missing}')
    if profile.get('estimatedMaxCostUsd') is None or profile.get('budgetUsd') is None:
        raise ValueError('provider profile must state budgetUsd and estimatedMaxCostUsd')
    if float(profile['estimatedMaxCostUsd']) > float(profile['budgetUsd']):
        raise ValueError('estimated maximum cost exceeds approved budget')
    if int(profile.get('maxRequests') or 0) < case_count:
        raise ValueError('approved maxRequests is lower than corpus size')
    return profile


def evaluate_case(case, record, manual, renderer):
    raw = record.get('raw') if isinstance(record, dict) else None
    parse_ok = False
    parsed = None
    error = None
    if isinstance(raw, str):
        try:
            parsed = parse_recognition(raw)
            parse_ok = True
        except ValueError as exc:
            error = str(exc)
    else:
        error = 'no response'
    gt = case.get('groundTruth') or {}
    diagram = case.get('category') == 'diagram'
    text_exact = None
    latex_exact = None
    render_ok = None
    if parse_ok:
        text_exact = normalize_text(parsed['text']) == normalize_text(gt.get('text', ''))
        latex_exact = normalize_latex(parsed['latex']) == normalize_latex(gt.get('latex', ''))
        if renderer is not None:
            render_ok = bool(renderer(parsed['latex'])) if parsed['latex'] else True
    if diagram:
        text_exact = None
        latex_exact = None
        render_ok = None
    review = manual.get(case['id']) if isinstance(manual, dict) else None
    semantic_correct = review.get('semanticCorrect') if isinstance(review, dict) and isinstance(review.get('semanticCorrect'), bool) else None
    correction_needed = review.get('manualCorrectionNeeded') if isinstance(review, dict) and isinstance(review.get('manualCorrectionNeeded'), bool) else None
    diagram_ok = review.get('diagramSemanticsCorrect') if isinstance(review, dict) and isinstance(review.get('diagramSemanticsCorrect'), bool) else None
    return {
        'caseId': case['id'],
        'category': case['category'],
        'image': case['image'],
        'imageSha256': case['imageSha256'],
        'rawResponseSha256': sha256_bytes(raw.encode()) if isinstance(raw, str) else None,
        'parseSuccess': parse_ok,
        'textExact': text_exact,
        'latexExact': latex_exact,
        'renderSuccess': render_ok,
        'semanticCorrect': semantic_correct,
        'manualCorrectionNeeded': correction_needed,
        'diagramSemanticsCorrect': diagram_ok,
        'unsafeLatex': unsafe_latex(parsed['latex']) if parsed else None,
        'parsed': parsed,
        'error': error,
        'manualReviewNotes': review.get('notes') if isinstance(review, dict) else None,
    }


def summarize(cases):
    def collect(key):
        return [c.get(key) for c in cases]

    summary = {
        'parseSuccess': metric(collect('parseSuccess')),
        'textExact': metric(collect('textExact')),
        'latexExact': metric(collect('latexExact')),
        'renderSuccess': metric(collect('renderSuccess')),
        'semanticCorrect': metric(collect('semanticCorrect')),
        'manualCorrectionNeeded': metric(collect('manualCorrectionNeeded')),
        'diagramSemanticsCorrect': metric(collect('diagramSemanticsCorrect')),
    }
    by_category = {}
    for category in sorted({c['category'] for c in cases}):
        subset = [c for c in cases if c['category'] == category]
        by_category[category] = {
            'samples': len(subset),
            'parseSuccess': metric([c.get('parseSuccess') for c in subset]),
            'textExact': metric([c.get('textExact') for c in subset]),
            'latexExact': metric([c.get('latexExact') for c in subset]),
            'renderSuccess': metric([c.get('renderSuccess') for c in subset]),
            'semanticCorrect': metric([c.get('semanticCorrect') for c in subset]),
            'manualCorrectionNeeded': metric([c.get('manualCorrectionNeeded') for c in subset]),
            'diagramSemanticsCorrect': metric([c.get('diagramSemanticsCorrect') for c in subset]),
        }
    return summary, by_category


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('mock', 'replay', 'live'), default='mock')
    parser.add_argument('--corpus', type=Path, default=DEFAULT_CORPUS)
    parser.add_argument('--responses', type=Path, default=DEFAULT_MOCK)
    parser.add_argument('--review-file', type=Path)
    parser.add_argument('--approval-file', type=Path)
    parser.add_argument('--allow-paid', action='store_true')
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument('--no-render', action='store_true')
    args = parser.parse_args(argv)

    corpus = load_corpus(args.corpus)
    corpus_sha = sha256_file(args.corpus)
    review_path, corpus_review, review_valid = load_review(corpus_sha)
    manual = load_manual_reviews(args.review_file, corpus_sha)
    profile = None
    records = {}
    responses_meta = {}

    if args.mode == 'live':
        if not args.allow_paid:
            raise SystemExit('live mode requires --allow-paid and an approved provider profile')
        if not review_valid:
            raise SystemExit('live mode refused: corpus review is not VERIFIED for this corpus hash')
        if not args.approval_file:
            raise SystemExit('live mode refused: --approval-file is required')
        profile = approved_profile(args.approval_file, len(corpus['cases']))
        api_key = os.environ.get('LGXT_OCR_EVAL_API_KEY')
        if profile['provider'] != 'Local' and not api_key:
            raise SystemExit('live mode refused: LGXT_OCR_EVAL_API_KEY is not set')
        for case in corpus['cases']:
            records[case['id']] = {'raw': live_request(profile, ROOT / case['image'], api_key), 'source': 'live_provider'}
    else:
        responses_meta, records = load_jsonl(args.responses)

    renderer = None
    close_renderer = None
    if not args.no_render:
        renderer, close_renderer = make_renderer(True)
    try:
        evaluated = [evaluate_case(case, records.get(case['id'], {}), manual, renderer) for case in corpus['cases']]
    finally:
        if close_renderer:
            close_renderer()

    summary, by_category = summarize(evaluated)
    mode_source = records and next(iter(records.values()), {}).get('source', 'synthetic')
    if args.mode == 'live':
        measurement_status = 'MEASURED_AUTOMATED_METRICS'
        accuracy_claim = bool(all(v.get('sampleCount', 0) > 0 for v in (
            summary['textExact'], summary['latexExact'], summary['semanticCorrect'], summary['renderSuccess'])))
    elif mode_source == 'live_provider':
        measurement_status = 'LIVE_OUTPUTS_AWAITING_INDEPENDENT_REVIEW'
        accuracy_claim = False
    else:
        measurement_status = 'HARNESS_ONLY_SYNTHETIC'
        accuracy_claim = False
    if not review_valid:
        measurement_status += '_GROUND_TRUTH_NOT_VERIFIED'
    if args.mode == 'live' and not manual:
        accuracy_claim = False

    result = {
        'schemaVersion': 1,
        'generatedAt': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'tool': {'name': TOOL_NAME, 'version': TOOL_VERSION, 'command': ' '.join(sys.argv)},
        'measurement': {
            'mode': args.mode,
            'responseSource': mode_source,
            'status': measurement_status,
            'accuracyClaim': accuracy_claim,
            'realModelRequestCount': len(corpus['cases']) if args.mode == 'live' else (len(records) if mode_source == 'live_provider' else 0),
            'manualReviewCaseCount': len(manual),
        },
        'binding': {
            'repository': 'styayur/LGXT-Assistant',
            'gitCommit': git_commit(),
            'corpusPath': str(args.corpus.relative_to(ROOT)),
            'corpusSha256': corpus_sha,
            'corpusReviewPath': str(review_path.relative_to(ROOT)),
            'corpusReviewStatus': corpus_review.get('status'),
            'corpusReviewValidForHash': review_valid,
            'providerProfile': profile,
            'responsesMeta': responses_meta,
        },
        'corpus': {
            'name': corpus.get('name'),
            'caseCount': len(corpus['cases']),
            'categories': dict(Counter(c['category'] for c in corpus['cases'])),
            'license': corpus.get('license'),
        },
        'summary': summary,
        'byCategory': by_category,
        'cases': evaluated,
        'limitations': [
            'Rendered LaTeX can be syntactically valid and mathematically wrong.',
            'Mock and synthetic replay results are harness tests, not OCR accuracy.',
            'Diagram understanding requires independent manual review and is not inferred from LaTeX rendering.',
            'Wilson intervals describe this corpus only and do not establish cross-provider generalization.',
            'No endpoint data-retention behavior is certified by this harness.',
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({
        'status': measurement_status,
        'accuracyClaim': accuracy_claim,
        'cases': len(evaluated),
        'parseSuccess': summary['parseSuccess'],
        'latexExact': summary['latexExact'],
        'renderSuccess': summary['renderSuccess'],
        'semanticCorrect': summary['semanticCorrect'],
        'diagramSemanticsCorrect': summary['diagramSemanticsCorrect'],
        'output': str(args.output),
    }, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())