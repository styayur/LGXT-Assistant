import base64
import io
from pathlib import Path

from docx import Document
from PIL import Image
import pytest

import equation_preview
import exporter


def fixture(formula):
    image = io.BytesIO()
    Image.new('RGB', (600, 120), 'white').save(image, 'PNG')
    return dict(schemaVersion=1, courseId='qa', workId='qa', questionId='formula',
                title='Synthetic equation export', courseName='QA', workName='Equation fixture',
                originalImage='data:image/png;base64,' + base64.b64encode(image.getvalue()).decode(),
                sourceText='Self-authored fixture', recognizedText='', latex=formula,
                correctedMarkdown='Corrected source retained',
                solutionMarkdown='## Derivation\n\n| a | b |\n|---|---|\n| 1 | 2 |\n\n```python\nx=1\n```',
                sources=[])


@pytest.mark.parametrize('source', [r'\input{/etc/passwd}', r'\href{https://example.invalid}{x}',
                                   r'\begin{pmatrix}1&0\\0&1\end{pmatrix}',
                                   r'\begin{aligned}x&=1\\y&=2\end{aligned}',
                                   'x+' * 1024, '{' * 17 + 'x' + '}' * 17])
def test_unsupported_and_bounded_source_never_starts_renderer(source, monkeypatch):
    monkeypatch.setattr(equation_preview.importlib.util, 'find_spec', lambda _: pytest.fail('worker must not start'))
    result = equation_preview.render_preview(source)
    assert result['status'] == 'source-fallback' and result['editable'] is False


def test_missing_optional_renderer_preserves_source(monkeypatch):
    monkeypatch.setattr(equation_preview.importlib.util, 'find_spec', lambda _: None)
    assert equation_preview.render_preview(r'\frac{1}{2}')['reason'] == 'renderer-unavailable'


@pytest.mark.parametrize('formula', [r'\frac{1}{2}', r'\sqrt{x^2+1}'])
def test_real_pinned_offline_renderer_is_bounded(formula):
    pytest.importorskip('matplotlib')
    result = equation_preview.render_preview(formula)
    assert result['status'] == 'rendered', result
    assert result['editable'] is False
    assert result['width'] <= equation_preview.MAX_WIDTH
    assert result['height'] <= equation_preview.MAX_HEIGHT
    assert result['png'].startswith(b'\x89PNG')


def test_optional_word_and_pdf_keep_original_content_and_source(tmp_path):
    pytest.importorskip('matplotlib')
    for format in ('docx', 'pdf'):
        result = exporter.export_question_document(fixture(r'\frac{1}{2}'), tmp_path, format, render_equations=True)
        assert result['equationPreview']['status'] == 'rendered'
        assert result['equations'] == 'latex-source-with-raster-preview'
        assert r'\frac{1}{2}' in Path(result['path']).with_suffix('.md').read_text(encoding='utf-8')
        if format == 'docx':
            word = Document(result['path'])
            assert len(word.inline_shapes) == 2 and word.tables
            assert any(r'\frac{1}{2}' in p.text for p in word.paragraphs)
            assert any('x=1' in p.text for p in word.paragraphs)


def test_unsupported_formula_export_falls_back_without_losing_source(tmp_path):
    formula = r'\begin{pmatrix}1&0\\0&1\end{pmatrix}'
    result = exporter.export_question_document(fixture(formula), tmp_path, 'docx', render_equations=True)
    assert result['equations'] == 'latex-source'
    word = Document(result['path'])
    assert len(word.inline_shapes) == 1
    assert any(formula in p.text for p in word.paragraphs)
