# OCR evaluation harness

This directory contains a self-authored, project-owned evaluation corpus. It is **not** a measured accuracy result.

## What is separated

- OCR text exact match
- JSON/schema parsing
- whitespace-normalized LaTeX exact match
- KaTeX rendering with `trust: false`
- independent semantic correctness
- manual correction rate
- diagram semantics, reviewed separately

Every proportion includes its sample count and a Wilson 95% confidence interval. Diagram understanding is never inferred from successful formula rendering.

## Fail-closed gates

Live paid requests require all of the following:

1. `corpus-review.json` has `status: VERIFIED`, a matching `corpusSha256`, and an independent reviewer.
2. `--approval-file` names a pinned provider, endpoint, model, request limit, approved budget and authorization reference.
3. `LGXT_OCR_EVAL_API_KEY` is supplied at runtime, or the approved endpoint is local.
4. `--allow-paid` is passed explicitly.

The harness makes one sequential request per case and never retries a paid call. Model keys are not written to results.

Independent review of model outputs is supplied separately with `--review-file`; without it, semantic and manual-correction metrics remain `NOT_VERIFIED`.

## Commands

```bash
# Synthetic harness regression only; never an accuracy claim
python scripts/evaluate_ocr.py --mode mock

# Evaluate archived outputs without making requests
python scripts/evaluate_ocr.py --mode replay --responses path/to/live-responses.jsonl --review-file path/to/manual-review.json

# Authorized live run; refused until the corpus review and provider approval are complete
python scripts/evaluate_ocr.py --mode live --approval-file path/to/approval.json --allow-paid
```

The default result is written to `results.json`. Current state remains **BLOCKED** pending independent ground-truth review, an approved provider/model and request budget, and live responses.
