"""Generate self-authored Word/PDF compatibility fixtures, never live OCR inputs."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests'))
from test_equation_preview import fixture
from exporter import export_question_document

CASES = {
    'fraction': (r'\frac{a_1}{b^2}', 'rendered'),
    'radical': (r'\sqrt{x^2+1}', 'rendered'),
    'matrix': (r'\begin{pmatrix}1&0\\0&1\end{pmatrix}', 'source-fallback'),
    'aligned': (r'\begin{aligned}x&=1\\y&=2\end{aligned}', 'source-fallback'),
    'long': ('x+' * 600, 'source-fallback'),
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = []
    for name, (latex, expected) in CASES.items():
        document = fixture(latex)
        document['questionId'] = name
        for format in ('docx', 'pdf'):
            result = export_question_document(document, args.output, format, render_equations=True)
            assert result['equationPreview']['status'] == expected, result
            report.append(dict(case=name, format=format, expected=expected, result=result))
    (args.output / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
