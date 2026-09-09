# -*- coding: utf-8 -*-
"""后台任务：题目收集 / 批量提交 / 批量导出。

线程安全约定：worker 内绝不直接操作 Tkinter 控件，只调用 ui 适配器的方法，
这些方法内部一律通过 root.after() 把 UI 更新调度回主线程执行。
"""
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

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

    with ThreadPoolExecutor(max_workers=PARALLEL_WORKERS) as pool:
        futures = [pool.submit(client.get_questions, work_id) for _ in range(max_iterations)]
        total = len(futures)
        processed = 0
        for future in as_completed(futures):
            processed += 1
            ui.status(f'正在收集题目...({processed}/{total}) - {int(processed / total * 100)}% - 已找到 {len(collected)} 道题目')
            ui.progress(int(processed / total * 100))
            try:
                ok, questions = future.result()
                if ok:
                    api_errors = 0
                    if not _merge_questions(collected, questions):
                        no_new += 1
                        if processed >= MIN_ITERATIONS and no_new >= NO_NEW_THRESHOLD:
                            break
                    else:
                        no_new = 0
                else:
                    api_errors += 1
                    err = f'API错误: {questions}'
                    ui.status(f'获取题目时发生错误: {err}\n重试中... ({api_errors}/{MAX_API_ERRORS})')
                    if api_errors >= MAX_API_ERRORS:
                        return fail('获取题目失败: 多次请求失败')
            except Exception as exc:
                return fail(f'处理题目时出现错误: {exc}')

        if not collected:
            return fail('没有找到任何题目，可能是API错误或作业中没有题目')

        save_collected(client, collected, work_name, course_name, work_id, course_id, work_name, opts)
        ui.status(f'收集完成，共收集到 {len(collected)} 道题目。用时: {time.time() - start_time:.2f}秒')
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


def submit_all_courses(ui, client, courses):
    messages = []
    works, fetch_fail = load_all_works(client, courses, messages)
    total_courses = len(courses)
    total_works = len(works)
    success_count = fail_count = 0

    ui.maximum(total_works)
    for processed, (course_id, course_name, work_id, work_name) in enumerate(works, 1):
        ui.status(f'正在提交课程：{course_name}\n作业：{work_name}')
        ok, data = client.submit_answer(work_id, '100')
        if ok:
            success_count += 1
            messages.append(f"课程 '{course_name}' 的作业 '{work_name}' 提交成功。")
        else:
            fail_count += 1
            messages.append(f"课程 '{course_name}' 的作业 '{work_name}' 提交失败：{data}")
        ui.progress(processed)

    return {'title': '提交结果',
            'text': (f'共处理 {total_courses} 门课程，{total_works} 个作业。\n'
                     f'成功提交 {success_count} 个作业，提交失败 {fail_count} 个作业。\n'
                     f'有 {fetch_fail} 门课程的作业获取失败。\n\n' + '\n'.join(messages))}


def submit_all_works(ui, client, works):
    total = len(works)
    success_count = fail_count = 0
    messages = []
    ui.maximum(total)

    with ThreadPoolExecutor(max_workers=PARALLEL_WORKERS) as executor:
        futures = {executor.submit(client.submit_answer, work['workId'], '100'): work for work in works}
        completed = 0
        for future in as_completed(futures):
            completed += 1
            work_name = futures[future]['workName']
            try:
                ok, data = future.result()
                if ok:
                    success_count += 1
                    messages.append(f"作业 '{work_name}' 提交成功。")
                else:
                    fail_count += 1
                    messages.append(f"作业 '{work_name}' 提交失败：{data}")
            except Exception as e:
                fail_count += 1
                messages.append(f"作业 '{work_name}' 提交时出现错误：{str(e)}")
            ui.progress(int(completed / total * 100))
            ui.status(f'正在提交作业 ({completed}/{total})...')

    return {'title': '提交结果',
            'text': f'成功提交 {success_count} 个作业，失败 {fail_count} 个作业。\n\n' + '\n'.join(messages)}


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
