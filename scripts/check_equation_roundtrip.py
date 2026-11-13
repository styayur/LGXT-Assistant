"""Verify QA Word round-trips and source text in independently reopened PDFs."""
import argparse
import json
from pathlib import Path
import subprocess

from docx import Document
from check_equation_exports import CASES


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    evidence = []
    for name, (latex, _) in CASES.items():
        filename = 'Equation fixture-' + name
        original = Document(args.output / 'question-documents' / (filename + '.docx'))
        reopened = Document(args.output / 'roundtrip' / (filename + '.docx'))
        assert latex in '\n'.join(p.text for p in reopened.paragraphs)
        assert len(reopened.inline_shapes) == len(original.inline_shapes)
        assert [[c.text for c in row.cells] for t in reopened.tables for row in t.rows] == [[c.text for c in row.cells] for t in original.tables for row in t.rows]
        for directory in ['question-documents', 'word-pdfs']:
            path = args.output / directory / (filename + '.pdf')
            result = subprocess.run(['pdftotext', str(path), '-'], capture_output=True, text=True, check=True)
            assert ''.join(latex.split()) in ''.join(result.stdout.split()), str(path)
            pages = [''.join(page.split()) for page in result.stdout.split('\f')]
            caption = '预览为位图' if CASES[name][1] == 'rendered' else '此表达式未生成预览'
            assert any('公式预览位图' in page and caption in page for page in pages), f'Orphaned preview caption: {path}'
        evidence.append({'case': name, 'source': 'retained', 'pictures': len(reopened.inline_shapes), 'tables': len(reopened.tables)})
    (args.output / 'roundtrip-report.json').write_text(json.dumps(evidence, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
