"""Versioned question documents and provider-neutral recognition validation."""
import base64
import hashlib
import json
from datetime import datetime, timezone

try:
    from . import lgxt_transport as api
except ImportError:
    import lgxt_transport as api

SCHEMA = 1
MAX_TEXT = 200_000


def image_data_url(value):
    if not isinstance(value, str) or len(value) > 12 * 1024 * 1024:
        raise ValueError('图片数据过大或无效')
    try:
        head, encoded = value.split(',', 1)
        if head not in ('data:image/png;base64', 'data:image/jpeg;base64', 'data:image/webp;base64'):
            raise ValueError()
        raw = base64.b64decode(encoded, validate=True)
        mime = api.validate_image(raw)
        if head != 'data:' + mime + ';base64':
            raise ValueError()
        return raw
    except (ValueError, TypeError):
        raise ValueError('图片数据无效；仅支持有大小限制的 PNG、JPEG、WebP') from None


def document_key(course_id, work_id, question_id):
    return hashlib.sha256(json.dumps([str(course_id), str(work_id), str(question_id)]).encode()).hexdigest()


def validate_document(value):
    if not isinstance(value, dict) or value.get('schemaVersion') != SCHEMA:
        raise ValueError('不支持的文档版本；请保留原文件并导出 Markdown 后转换')
    fields = ('courseId', 'workId', 'questionId', 'courseName', 'workName', 'title',
              'sourceText', 'recognizedText', 'latex', 'correctedMarkdown', 'solutionMarkdown')
    result = {'schemaVersion': SCHEMA}
    for key in fields:
        item = value.get(key, '')
        if not isinstance(item, (str, int)) or len(str(item)) > MAX_TEXT:
            raise ValueError('文档字段无效或过长')
        result[key] = str(item)
    if not all(result[k] for k in ('courseId', 'workId', 'questionId')):
        raise ValueError('缺少课程、作业或题目编号')
    original = value.get('originalImage', '')
    if original:
        image_data_url(original)
    result['originalImage'] = original
    # Source references are user-selected local excerpts, never model citations.
    sources = value.get('sources', [])
    if not isinstance(sources, list) or len(sources) > 8:
        raise ValueError('最多选择 8 份资料')
    result['sources'] = []
    for source in sources:
        if not isinstance(source, dict) or not isinstance(source.get('text'), str) or len(source['text']) > 60000:
            raise ValueError('资料内容无效')
        result['sources'].append({'name': str(source.get('name', '资料'))[:200], 'text': source['text']})
    recognition = value.get('recognition')
    if recognition is not None:
        if not isinstance(recognition, dict):
            raise ValueError('识别来源无效')
        result['recognition'] = {k: str(recognition.get(k, ''))[:500] for k in ('provider', 'model', 'at', 'region')}
    discussion = value.get('discussion', [])
    if not isinstance(discussion, list) or len(discussion) > 20:
        raise ValueError('题目对话超过本地上下文上限')
    result['discussion'] = []
    for message in discussion:
        if (not isinstance(message, dict) or message.get('role') not in ('user', 'assistant')
                or not isinstance(message.get('content'), str) or len(message['content']) > 30000):
            raise ValueError('题目对话内容无效')
        result['discussion'].append({'role': message['role'], 'content': message['content']})
    result['answer'] = str(value.get('answer', ''))[:MAX_TEXT]
    result['updatedAt'] = datetime.now(timezone.utc).isoformat()
    return result


def parse_recognition(text):
    if not isinstance(text, str) or len(text) > 64000:
        raise ValueError('识别输出过长或无效')
    raw = text.strip()
    if raw.startswith('```json\n') and raw.endswith('```'):
        raw = raw[8:-3].strip()
    try:
        value = json.loads(raw)
    except (ValueError, TypeError):
        raise ValueError('识别服务未返回约定的 JSON；原图和已有编辑已保留') from None
    if (not isinstance(value, dict) or set(value) != {'text', 'latex'}
            or not all(isinstance(value[k], str) and len(value[k]) <= 30000 for k in ('text', 'latex'))):
        raise ValueError('识别结果必须包含 text 和 latex 字符串')
    return value


def context_messages(document, prompt, image=None):
    d = validate_document(document)
    text = (f"来源：课程 {d['courseName']} / 作业 {d['workName']} / 题目 {d['questionId']}\n"
            f"原始文字：{d['sourceText']}\n用户校正题面（优先）：{d['correctedMarkdown']}\n"
            f"识别 LaTeX（机器生成，可能有误）：{d['latex']}\n已有解答：{d['solutionMarkdown']}\n")
    for message in d['discussion']:
        text += f"\n先前题目对话（{message['role']}）：{message['content']}"
    attachments = [{'name': '题目上下文', 'text': text}]
    for source in d['sources']:
        attachments.append(source)
    if image:
        image_data_url(image)
        attachments.append({'name': '原题或用户裁剪区域', 'data': image})
    return [{'role': 'user', 'content': prompt, 'attachments': attachments}]
