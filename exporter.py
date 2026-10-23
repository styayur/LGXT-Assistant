# -*- coding: utf-8 -*-
"""导出：题目图片缓存 + Word / PDF 输出。任务线程中调用，不触碰 UI。"""
import collections
import logging
import os

from docx import Document
from docx.oxml.ns import qn
from docx.shared import Inches, RGBColor
from reportlab.lib import colors
from reportlab.lib.units import inch

log = logging.getLogger(__name__)
WINDOWS_RESERVED = {'CON','PRN','AUX','NUL'} | {f'COM{i}' for i in range(1, 10)} | {f'LPT{i}' for i in range(1, 10)}

IMAGE_DIR = '题目图片'
FOLDER_ROOT = '作业'

# 导出开关快照（主线程读取 Tk 变量后传入 worker，避免跨线程访问）
ExportOptions = collections.namedtuple(
    'ExportOptions', 'export_path export_word export_word_answers export_pdf export_pdf_answers')


def clean_name(name):
    """清洗文件名：非法字符、结尾空格/点、Windows 保留名、超长截断。"""
    cleaned = ''.join(c for c in str(name) if c not in r'<>:"/\|?*').strip().rstrip(' .')
    if not cleaned:
        cleaned = 'unnamed'
    if cleaned.upper().split('.')[0] in WINDOWS_RESERVED:
        cleaned = '_' + cleaned
    return cleaned[:120]


def assignment_folder(export_path, course_name, course_id, work_name, work_id):
    return os.path.join(export_path, FOLDER_ROOT,
                        f'{clean_name(course_name)} (ID_{clean_name(course_id)})',
                        f'{clean_name(work_name)} (ID_{clean_name(work_id)})')


def save_question(client, question, assignment_folder_path):
    """把题目图片下载到 题目图片/<id>.png；已存在且非空则跳过（缓存）。"""
    question_id = clean_name(question.get('id', 'N/A'))
    imgurl = question.get('imgurl', 'N/A')
    images_folder = os.path.join(assignment_folder_path, IMAGE_DIR)
    os.makedirs(images_folder, exist_ok=True)
    if not imgurl or imgurl == 'N/A':
        return
    image_path = os.path.join(images_folder, f'{clean_name(question_id)}.png')
    if os.path.exists(image_path) and os.path.getsize(image_path) > 0:
        return  # 已缓存，避免重复下载
    try:
        with open(image_path, 'wb') as f:
            f.write(client.fetch_image(imgurl))
    except Exception as e:
        log.warning('无法下载题目图片：请检查来源或图片内容')


def save_collected(client, collected_questions, work_name, course_name, work_id, course_id,
                   chapter_name, opts):
    """把收集结果写入磁盘：图片 + 可选 Word/PDF。与旧版目录结构一致。"""
    folder = assignment_folder(opts.export_path, course_name, course_id, work_name, work_id)
    os.makedirs(folder, exist_ok=True)
    for question in collected_questions.values():
        save_question(client, question, folder)
    if opts.export_word:
        save_questions_to_word(collected_questions, folder, chapter_name,
                               export_answers=opts.export_word_answers)
    if opts.export_pdf:
        save_questions_to_pdf(collected_questions, folder, chapter_name,
                              export_answers=opts.export_pdf_answers)


def save_questions_to_word(collected_questions, assignment_folder_path, work_name, export_answers=True):
    document = Document()
    style = document.styles['Normal']
    style.font.name = '宋体'
    style.font.element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')
    document.add_heading(work_name, 0)

    images_folder = os.path.join(assignment_folder_path, IMAGE_DIR)
    for idx, question_id in enumerate(sorted(collected_questions, key=int)):
        question = collected_questions[question_id]
        document.add_heading(f'题目 {idx + 1}: {question.get("name", "N/A")}', level=2)
        image_path = os.path.join(images_folder, f'{clean_name(question_id)}.png')
        if os.path.exists(image_path):
            document.add_picture(image_path, width=Inches(5))
        else:
            document.add_paragraph('（无图片）')
        if export_answers:
            run = document.add_paragraph('答案：').add_run(question.get('answer', 'N/A'))
            run.font.color.rgb = RGBColor(255, 0, 0)

    document.save(os.path.join(assignment_folder_path, f'{work_name}.docx'))


def save_questions_to_pdf(collected_questions, assignment_folder_path, work_name, export_answers=True):
    from html import escape
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    from reportlab.platypus import (BaseDocTemplate, Frame, Image as RLImage,
                                    PageTemplate, Paragraph, Spacer)

    pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
    styles = getSampleStyleSheet()
    for name, parent, size, leading, color in [
        ('ChineseTitle', 'Title', 20, 24, '#333333'),
        ('ChineseHeading1', 'Heading1', 16, 20, '#555555'),
        ('Chinese', 'Normal', 12, 18, '#000000'),
    ]:
        styles.add(ParagraphStyle(name=name, parent=styles[parent], fontName='STSong-Light',
                                  fontSize=size, leading=leading,
                                  alignment=1 if name == 'ChineseTitle' else 0,
                                  textColor=colors.HexColor(color)))
    normal_style = styles['Chinese']

    def add_page_number(canvas, _doc):
        canvas.setFont('STSong-Light', 9)
        canvas.drawRightString(A4[0] - 50, 15, f'第 {canvas.getPageNumber()} 页')

    doc = BaseDocTemplate(os.path.join(assignment_folder_path, f'{work_name}.pdf'), pagesize=A4,
                          rightMargin=40, leftMargin=40, topMargin=60, bottomMargin=60)
    frame = Frame(40, 60, doc.width, doc.height, id='normal')
    doc.addPageTemplates([PageTemplate(id='test', frames=frame, onPage=add_page_number)])

    elements = [Paragraph(escape(work_name), styles['ChineseTitle']), Spacer(1, 0.3 * inch)]
    images_folder = os.path.join(assignment_folder_path, IMAGE_DIR)
    for idx, question_id in enumerate(sorted(collected_questions, key=int)):
        question = collected_questions[question_id]
        elements.append(Paragraph(escape(f'题目 {idx + 1}: {question.get("name", "N/A")}'), styles['ChineseHeading1']))
        elements.append(Spacer(1, 0.1 * inch))
        image_path = os.path.join(images_folder, f'{clean_name(question_id)}.png')
        if os.path.exists(image_path):
            img = ImageReader(image_path)
            width, height = img.getSize()
            display_width = doc.width * 0.8
            elements.append(RLImage(image_path, width=display_width,
                                    height=display_width * height / float(width)))
        else:
            elements.append(Paragraph('（无图片）', normal_style))
        if export_answers:
            elements.append(Paragraph(f"答案：<font color='red'>{escape(str(question.get('answer', 'N/A')))}</font>", normal_style))
        elements.append(Spacer(1, 0.2 * inch))

    doc.build(elements)

def export_question_document(document, export_path, format='md'):
    """Export a recoverable Markdown document. Equations remain editable source.

    Word/PDF preserve original image and basic Markdown blocks. LaTeX is exported
    verbatim, not falsely described as native Word equations or typeset PDF math.
    """
    import io
    import re
    from pathlib import Path
    from html import escape
    from question_documents import image_data_url, validate_document
    d = validate_document(document)
    if format not in ('md', 'docx', 'pdf'):
        raise ValueError('不支持的导出格式')
    if not export_path:
        raise ValueError('请先在导出设置中指定目录')
    directory = Path(export_path).expanduser().resolve() / 'question-documents'
    directory.mkdir(parents=True, exist_ok=True)
    name = clean_name(d['workName']) + '-' + clean_name(d['questionId'])
    path = directory / (name + '.' + format)
    text = (f"# {d['title']}\n\n来源：{d['courseName']} / {d['workName']} / {d['questionId']}\n\n"
            f"## 原始文字\n\n{d['sourceText']}\n\n## 校正题面\n\n{d['correctedMarkdown']}\n\n"
            f"## 解答（含用户编辑与模型生成内容，请核对）\n\n{d['solutionMarkdown']}\n\n"
            f"## 识别 LaTeX 源码（机器生成，可能有误）\n\n```latex\n{d['latex']}\n```\n\n"
            f"导出时间：{d['updatedAt']}\n\n公式保留为 LaTeX 源码；未转换为 Word 原生公式或 PDF 数学排版。\n")
    text += f"\n## 平台参考答案（如有）\n\n{d['answer']}\n\n## 识别文字（机器生成）\n\n{d['recognizedText']}\n"
    if d.get('recognition'):
        import json
        text += '\n识别来源：' + json.dumps(d['recognition'], ensure_ascii=False) + '\n'
    for message in d.get('discussion', []):
        text += f"\n## 题目对话（{message['role']}）\n\n{message['content']}\n"
    for source in d['sources']:
        text += f"\n## 用户选择资料：{source['name']}\n\n{source['text']}\n"
    raw = image_data_url(d['originalImage']) if d['originalImage'] else None
    if raw:
        image_path = directory / (name + '-original.png')
        from PIL import Image
        with Image.open(io.BytesIO(raw)) as image:
            image.convert('RGB').save(image_path, format='PNG')
        text += f'\n![原始题目]({image_path.name})\n'
    # Always retain a lossless sidecar; unsupported Markdown remains recoverable.
    (directory / (name + '.md')).write_text(text, encoding='utf-8')
    if format == 'md':
        return {'path': str(path), 'equations': 'latex-source'}
    if format == 'docx':
        doc = Document()
        if raw:
            doc.add_picture(str(image_path), width=Inches(5))
        table = None
        code = False
        for line in text.splitlines():
            images = re.findall(r'!\[[^\]]*\]\((data:image/(?:png|jpeg|webp);base64,[A-Za-z0-9+/=]+)\)', line) if not code else []
            for image_data in images:
                doc.add_picture(io.BytesIO(image_data_url(image_data)), width=Inches(5))
            if images:
                line = re.sub(r'!\[[^\]]*\]\(data:image/(?:png|jpeg|webp);base64,[A-Za-z0-9+/=]+\)', '', line)
            if line.startswith('```'):
                code = not code
                continue
            if not code and re.match(r'^\|?[ :\-]+\|[ :|\-]*$', line):
                continue
            if not code and line.startswith('|') and line.endswith('|'):
                cells = line.strip('|').split('|')
                if table is None or len(table.columns) != len(cells):
                    table = doc.add_table(rows=0, cols=len(cells)); table.style = 'Table Grid'
                for cell, value in zip(table.add_row().cells, cells):
                    cell.text = value.strip()
                continue
            table = None
            if not code and line.startswith('#'):
                level = min(3, len(line) - len(line.lstrip('#')))
                doc.add_heading(line.lstrip('# ').strip(), level)
            elif not line.startswith('![原始题目]'):
                para = doc.add_paragraph(style='List Bullet' if line.startswith('- ') and not code else None)
                for i, fragment in enumerate(re.split(r'\*\*(.*?)\*\*', line[2:] if line.startswith('- ') and not code else line)):
                    run = para.add_run(fragment)
                    run.bold = bool(i % 2) and not code
                    if code:
                        run.font.name = 'Consolas'
        doc.save(path)
    else:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.cidfonts import UnicodeCIDFont
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, Table, TableStyle
        from reportlab.pdfbase.ttfonts import TTFont
        font = 'STSong-Light'
        system_font = Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts/msyh.ttc'
        if system_font.is_file():
            pdfmetrics.registerFont(TTFont('QuestionCJK', str(system_font), subfontIndex=0))
            font = 'QuestionCJK'
        else:
            pdfmetrics.registerFont(UnicodeCIDFont(font))
        normal = ParagraphStyle('QuestionBody', fontName=font, fontSize=10, leading=16, wordWrap='CJK')
        heading = ParagraphStyle('QuestionHeading', parent=normal, fontSize=15, leading=22, spaceBefore=14)
        story = []
        if raw:
            from PIL import Image
            with Image.open(image_path) as image:
                width = min(480, image.width)
                factor = min(width / image.width, 550 / image.height)
                story.append(RLImage(str(image_path), width=image.width*factor, height=image.height*factor))
        rows = []
        def flush_table():
            if rows:
                count = max(len(r) for r in rows)
                grid = Table([r + ['']*(count-len(r)) for r in rows], colWidths=[480/count]*count, repeatRows=1)
                grid.setStyle(TableStyle([('GRID',(0,0),(-1,-1),0.5,colors.lightgrey),('VALIGN',(0,0),(-1,-1),'TOP')]))
                story.extend([grid, Spacer(1,8)])
                rows.clear()
        code = False
        for line in text.splitlines():
            if line.startswith('```'):
                code = not code
                continue
            images = re.findall(r'!\[[^\]]*\]\((data:image/(?:png|jpeg|webp);base64,[A-Za-z0-9+/=]+)\)', line) if not code else []
            for image_data in images:
                image_bytes = image_data_url(image_data)
                from PIL import Image
                with Image.open(io.BytesIO(image_bytes)) as image:
                    factor = min(480/image.width, 550/image.height)
                    story.append(RLImage(io.BytesIO(image_bytes), width=image.width*factor, height=image.height*factor))
            if images:
                line = re.sub(r'!\[[^\]]*\]\(data:image/(?:png|jpeg|webp);base64,[A-Za-z0-9+/=]+\)', '', line)
            if re.match(r'^\|?[ :\-]+\|[ :|\-]*$', line):
                continue
            if line.startswith('|') and line.endswith('|'):
                rows.append([Paragraph(escape(c.strip()), normal) for c in line.strip('|').split('|')])
                continue
            flush_table()
            if line.startswith('![原始题目]'):
                continue
            safe = escape(line.lstrip('# ') if line.startswith('#') else line)
            safe = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', safe)
            # Wrap long unbroken LaTeX/code lines at safe positions for narrow pages.
            parts = [safe[i:i+90] for i in range(0,len(safe),90)] if len(safe) > 90 and '<' not in safe else [safe]
            for part in parts:
                story.append(Paragraph(part or ' ', heading if line.startswith('#') else normal))
            story.append(Spacer(1,4))
        flush_table()
        SimpleDocTemplate(str(path), pagesize=A4, leftMargin=45, rightMargin=45, topMargin=40, bottomMargin=40).build(story)
    return {'path': str(path), 'equations': 'latex-source'}
