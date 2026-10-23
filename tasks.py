# -*- coding: utf-8 -*-
"""后台任务：题目收集 / 批量提交 / 批量导出。

线程安全约定：worker 内绝不直接操作 Tkinter 控件，只调用 ui 适配器的方法；
适配器把事件写入 queue，由主线程轮询（after）消费后更新界面。
"""
import time

from exporter import save_collected

MIN_ITERATIONS = 30          # 连续无新题目达到该阈值才允许提前停止
NO_NEW_THRESHOLD = 10
MAX_API_ERRORS = 3
SEQUENTIAL_LIMIT = 200       # 串行收集上限
PARALLEL_WORKERS = 10


def _merge_questions(collected, questions):
    """把一批题目并入结果；返回是否发现了新题目。"""
    new_found = False
    for q in questions:
        qid = q.get('id')
        if qid and qid not in collected:
            collected[qid] = q
            new_found = True
    return new_found


def _cancel_pending(futures):
    """提前结束收集时取消尚未执行的任务，避免无意义的 API 请求。"""
    for future in futures:
        if not future.done():
            future.cancel()


def collect_single(ui, client, work_id, work_name, course_name, course_id, opts, max_iterations=100):
    """单个作业“导出所有题目”：并行翻页收集 → 落盘。成功返回 collected，失败返回 None。"""
    collected = {}
    ui.status('开始收集题目...')
    start_time = time.time()
    api_errors = 0
    no_new = 0

    def fail(text):
        ui.status(text)
        ui.stop_and_close(3000)
        return None

    # showQuestions samples a question set; it is not a paginated endpoint.
    # Sequential sampling avoids identical concurrent calls and speculative queues.
    for processed in range(1, min(max_iterations, SEQUENTIAL_LIMIT) + 1):
        if getattr(ui, 'cancelled', lambda: False)():
            return fail('已取消收集；未宣称题库完整')
        ok, questions = client.get_questions(work_id)
        ui.progress(int(processed / max_iterations * 100))
        if not ok:
            api_errors += 1
            if api_errors >= MAX_API_ERRORS:
                return fail('获取题目失败；已有题目未标记为完整题库')
            continue
        api_errors = 0
        no_new = 0 if _merge_questions(collected, questions) else no_new + 1
        ui.status(f'抽样 {processed} 次，已收集 {len(collected)} 道；不保证题库完整')
        if processed >= MIN_ITERATIONS and no_new >= NO_NEW_THRESHOLD:
            break
    if not collected:
        return fail('没有找到任何题目')
    save_collected(client, collected, work_name, course_name, work_id, course_id, work_name, opts)
    ui.status(f'收集完成，共 {len(collected)} 道题；抽样结果不保证完整')
    ui.stop_and_close(1000)
    return collected


def batch_collect(ui, client, work_id, course_name, work_name):
    """串行翻页收集（供批量导出）；返回 (collected, None) 或 ({}, 错误信息)。"""
    collected = {}
    no_new = 0
    processed = 0
    api_errors = 0
    for _ in range(SEQUENTIAL_LIMIT):
        processed += 1
        try:
            ok, questions = client.get_questions(work_id)
            if ok:
                api_errors = 0
                new_found = _merge_questions(collected, questions)
                ui.status(f'正在导出课程：{course_name}\n作业：{work_name}\n'
                          f'已获取题目数量：{len(collected)}\n迭代次数：{processed}/{SEQUENTIAL_LIMIT}')
                if not new_found:
                    no_new += 1
                    if processed >= MIN_ITERATIONS and no_new >= NO_NEW_THRESHOLD:
                        break
                else:
                    no_new = 0
            else:
                api_errors += 1
                err = f'API错误: {questions}'
                ui.status(f'导出课程时发生错误: {err}\n重试中... ({api_errors}/{MAX_API_ERRORS})')
                if api_errors >= MAX_API_ERRORS:
                    return None, err
        except Exception as e:
            err = f'导出题目时出现异常: {str(e)}'
            ui.status(err)
            return None, err
    if collected:
        return collected, None
    return {}, '没有找到任何题目'


def load_all_works(client, courses, messages):
    """拉取所有课程的作业；返回 (作业扁平列表, 拉取失败课程数)。"""
    works = []
    fetch_fail = 0
    for course in courses:
        ok, data = client.get_course_works(course['courseId'])
        if ok:
            works.extend((course['courseId'], course['courseName'], w['workId'], w['workName']) for w in data)
        else:
            fetch_fail += 1
            messages.append(f"获取课程 '{course['courseName']}' 的作业失败：{data}")
    return works, fetch_fail


def _export_summary(total_courses, total_works, messages):
    return {'title': '导出结果',
            'text': f'共处理 {total_courses} 门课程，{total_works} 个作业。\n\n' + '\n'.join(messages)}


def export_all_courses(ui, client, courses, opts):
    messages = []
    works, _ = load_all_works(client, courses, messages)
    total_courses = len(courses)
    total_works = len(works)
    if total_works == 0:
        return _export_summary(total_courses, total_works, messages)

    ui.maximum(total_works)
    for processed, (course_id, course_name, work_id, work_name) in enumerate(works, 1):
        ui.status(f'正在导出课程：{course_name}\n作业：{work_name}')
        collected, err = batch_collect(ui, client, work_id, course_name, work_name)
        if collected:
            save_collected(client, collected, work_name, course_name, work_id, course_id, work_name, opts)
            messages.append(f"课程 '{course_name}' 的作业 '{work_name}' 导出成功，共 {len(collected)} 道题目。")
        else:
            messages.append(f"课程 '{course_name}' 的作业 '{work_name}' 导出失败: {err}")
        ui.progress(processed)
    return _export_summary(total_courses, total_works, messages)


def batch_plan(client, scope, course=None, work=None):
    """Read-only snapshot. A caller must present this exact scope before writing."""
    messages = []
    failed = 0
    if scope == 'assignment':
        if not course or not work:
            raise ValueError('请选择课程与作业')
        ok, rows = client.get_course_works(course['courseId'])
        if not ok:
            raise ValueError('无法核对当前作业')
        works = [w for w in rows if str(w['workId']) == str(work['workId'])]
    elif scope == 'course':
        if not course:
            raise ValueError('请选择课程')
        ok, works = client.get_course_works(course['courseId'])
        if not ok:
            raise ValueError('无法读取课程作业')
    elif scope == 'all':
        ok, courses = client.get_my_courses()
        if not ok:
            raise ValueError('无法读取课程')
        flat, failed = load_all_works(client, courses, messages)
        works = [{'workId': wid, 'workName': name} for _, _, wid, name in flat]
    else:
        raise ValueError('未知范围')
    seen = set()
    unique = []
    for item in works:
        wid = str(item['workId'])
        if wid not in seen:
            seen.add(wid)
            unique.append(item)
    return {'scope': scope, 'grade': '100', 'works': unique, 'count': len(unique),
            'fetchFailed': failed, 'warnings': messages}


def execute_batch(ui, client, works, cancel=None, audit=None):
    """One write at a time. Cancellation stops future writes, never rolls back."""
    results = []
    seen = set()
    unique = [w for w in works if not (str(w['workId']) in seen or seen.add(str(w['workId'])))]
    ui.maximum(len(unique))
    for item in unique:
        if (cancel and cancel.is_set()) or getattr(ui, 'cancelled', lambda: False)():
            break
        ui.status(f"一键满分：{item.get('workName', item['workId'])}")
        try:
            ok, message = client.submit_answer(item['workId'], '100')
            status = 'succeeded' if ok else ('verification_required' if str(message).startswith('结果待核实') else 'failed')
        except Exception:
            status, message = 'verification_required', '结果待核实：请求异常，请先检查平台记录'
        result = {'workId': item['workId'], 'status': status, 'message': str(message)}
        results.append(result)
        if audit:
            audit(result)
        ui.status(f"{item.get('workName', item['workId'])}：{status}")
        ui.progress(len(results))
    lines = [f"{r['workId']}：{r['status']} — {r['message']}" for r in results]
    return {'title': '一键满分结果', 'results': results, 'cancelled': len(results) < len(unique),
            'text': f'已处理 {len(results)}/{len(unique)}。已提交的更改不能撤销。成功表示平台确认接收，非独立核验。\n' + '\n'.join(lines)}


def submit_all_courses(ui, client, courses):
    messages = []
    flat, failed = load_all_works(client, courses, messages)
    result = execute_batch(ui, client, [{'workId': wid, 'workName': name} for _, _, wid, name in flat])
    result['text'] += f'\n有 {failed} 门课程读取失败。'
    return result


def submit_all_works(ui, client, works):
    return execute_batch(ui, client, works)


def export_all_works(ui, client, works, course_id, course_name, opts):
    total_works = len(works)
    success_count = fail_count = 0
    messages = []

    ui.maximum(total_works)
    for processed, work in enumerate(works, 1):
        work_id = work['workId']
        work_name = work['workName']
        ui.status(f'正在导出作业：{work_name}')
        collected, err = batch_collect(ui, client, work_id, course_name, work_name)
        if collected:
            save_collected(client, collected, work_name, course_name, work_id, course_id, work_name, opts)
            messages.append(f"作业 '{work_name}' 导出成功，共 {len(collected)} 道题目")
            success_count += 1
        else:
            messages.append(f"作业 '{work_name}' 导出失败: {err}")
            fail_count += 1
        ui.progress(processed)

    return {'title': '导出结果',
            'text': (f'共处理 {total_works} 个作业。\n成功导出: {success_count} 个\n导出失败: {fail_count} 个\n\n'
                     + '\n'.join(messages))}
