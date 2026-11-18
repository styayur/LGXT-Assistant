"""Task-first overview derived only from server fields, including partial failures."""
from datetime import datetime


def deadline_key(value):
    if not isinstance(value, str) or not value.strip():
        return (1, float('inf'))
    try:
        return (0, datetime.fromisoformat(value.replace('Z', '+00:00')).timestamp())
    except (ValueError, OverflowError):
        return (1, float('inf'))


def overview(courses, load_works):
    pending, done, total, failed = [], 0, 0, 0
    for course in courses:
        ok, works = load_works(course['courseId'])
        if not ok or not isinstance(works, list):
            failed += 1
            continue
        for work in works:
            total += 1
            if work.get('grade') is not None:
                done += 1
            else:
                pending.append((course, work))
    pending.sort(key=lambda item: deadline_key(item[1].get('expireTime')))
    return {'pending': pending, 'done': done, 'total': total, 'failed': failed}
