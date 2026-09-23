import React, { useState, useEffect, useRef } from "react";
import {
  BookOpen,
  Search,
  ArrowLeft,
  ArrowRight,
  RefreshCw,
  Download,
  Check,
  LogIn,
  FileQuestion,
  ArrowUpRight,
  LogOut,
  BarChart3,
} from "lucide-react";
import { Button, Empty, Skeleton, Badge, Modal } from "./ui";
import { call } from "../lib/bridge";
function QuestionImage({ url }) {
  const [image, setImage] = useState("");
  const [error, setError] = useState("");
  useEffect(() => {
    let alive = true;
    setImage("");
    setError("");
    call("question_image", url)
      .then((x) => {
        if (alive) setImage(x);
      })
      .catch((e) => {
        if (alive) setError(e.message);
      });
    return () => {
      alive = false;
    };
  }, [url]);
  return error ? (
    <p className="inline-error">图片加载失败：{error}</p>
  ) : image ? (
    <img className="question-image" src={image} alt="题目图片" />
  ) : (
    <Skeleton />
  );
}
export default function Courses({
  username,
  onLogin,
  onLogout,
  onTask,
  taskBusy,
  onReference,
  toast,
}) {
  const [course, setCourse] = useState(null);
  const [work, setWork] = useState(null);
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState("all");
  const [sort, setSort] = useState("default");
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState(null);
  const [grade, setGrade] = useState("100");
  const [confirm, setConfirm] = useState(null);
  const [revision, setRevision] = useState(0);
  const [stats, setStats] = useState(null);
  const [statsLoading, setStatsLoading] = useState(false);
  const [answer, setAnswer] = useState(false);
  const request = useRef(0);
  useEffect(() => {
    const token = ++request.current;
    if (!username) return;
    setLoading(true);
    setError("");
    setData([]);
    setSelected(null);
    setQuery("");
    setFilter("all");
    setSort("default");
    setPage(1);
    setAnswer(false);
    call(
      work ? "questions" : course ? "works" : "courses",
      ...(work ? [work.workId] : course ? [course.courseId] : []),
    )
      .then((rows) => {
        if (token === request.current) {
          setData(rows || []);
          if (work) setSelected(rows[0]);
        }
      })
      .catch((e) => {
        if (token === request.current) setError(e.message);
      })
      .finally(() => {
        if (token === request.current) setLoading(false);
      });
    return () => {
      request.current++;
    };
  }, [course, work, username, revision]);
  if (!username)
    return (
      <div className="page-scroll">
        <div className="content-page">
          <div className="page-heading">
            <div>
              <h1>我的课程</h1>
              <p>连接理工学堂，继续你的课程与作业。</p>
            </div>
          </div>
          <Empty
            icon={BookOpen}
            title="你的课程，在这里连接"
            action={
              <Button icon={LogIn} className="primary" onClick={onLogin}>
                登录理工学堂
              </Button>
            }
          >
            登录后查看真实课程、浏览题目并导出学习资料。
            <br />
            AI 会话可独立使用，无需课程账号。
          </Empty>
        </div>
      </div>
    );
  let rows = data.filter((r) =>
    JSON.stringify(r).toLowerCase().includes(query.toLowerCase()),
  );
  if (course && !work && filter !== "all")
    rows = rows.filter((w) =>
      filter === "available"
        ? Number(w.tryTimes || 0) > Number(w.times || 0)
        : w.grade != null && w.grade !== "",
    );
  if (work && filter === "answer")
    rows = rows.filter((q) => q.answer != null && q.answer !== "");
  if (sort === "name")
    rows = [...rows].sort((a, b) =>
      String(a.workName || a.courseName || a.name).localeCompare(
        String(b.workName || b.courseName || b.name),
      ),
    );
  if (sort === "deadline")
    rows = [...rows].sort((a, b) =>
      String(a.expireTime || "9999").localeCompare(
        String(b.expireTime || "9999"),
      ),
    );
  const pages = Math.max(1, Math.ceil(rows.length / 20));
  const currentPage = Math.min(page, pages);
  const visible = rows.slice((currentPage - 1) * 20, currentPage * 20);
  const batch = (action) => {
    if (action.startsWith("submit"))
      setConfirm({
        title: "确认批量提交成绩",
        text: `将为${course ? "“" + course.courseName + "”的所有作业" : "全部课程的所有作业"}提交 100 分。这会修改服务器成绩并消耗提交次数。`,
        action: () => onTask(action, course),
      });
    else onTask(action, course, work);
  };
  return (
    <div className="page-scroll">
      <div className="content-page course-page">
        <div className="page-heading">
          <div>
            {course && (
              <button
                className="text-link"
                onClick={() => (work ? setWork(null) : setCourse(null))}
              >
                <ArrowLeft size={14} />
                {work ? "返回作业" : "返回课程"}
              </button>
            )}
            <h1>{work?.workName || course?.courseName || "我的课程"}</h1>
            <p>
              {work
                ? "浏览题目，整理答案与解题思路。"
                : course
                  ? "查看作业状态，安排下一步学习。"
                  : `已连接理工学堂 · ${username}`}
            </p>
          </div>
          <div className="row-actions">
            <Button
              icon={RefreshCw}
              label="刷新课程数据"
              disabled={loading}
              onClick={() => setRevision((r) => r + 1)}
            />
            {!course && (
              <Button
                icon={LogOut}
                label="退出理工学堂登录"
                onClick={onLogout}
              />
            )}
            <Button
              icon={Download}
              disabled={taskBusy || loading || !data.length}
              onClick={() =>
                batch(
                  work
                    ? "export_work"
                    : course
                      ? "export_course"
                      : "export_all",
                )
              }
            >
              {work ? "导出全部题目" : course ? "导出课程" : "导出全部课程"}
            </Button>
          </div>
        </div>
        {!course && (
          <div className="course-summary">
            <div>
              <span className="summary-icon">
                <BookOpen size={22} />
              </span>
              <strong>{data.length}</strong>
              <span>已加入课程</span>
            </div>
            {stats ? (
              <>
                <div>
                  <strong>{stats.pending}</strong>
                  <span>待完成作业</span>
                </div>
                <div>
                  <strong>{stats.completed}</strong>
                  <span>已完成作业</span>
                </div>
                <div>
                  <strong>
                    {stats.average == null
                      ? "—"
                      : Number(stats.average).toFixed(1)}
                  </strong>
                  <span>
                    平均成绩{stats.fetch_fail > 0 ? "（部分课程未加载）" : ""}
                  </span>
                </div>
              </>
            ) : (
              <Button
                icon={BarChart3}
                disabled={statsLoading}
                onClick={async () => {
                  setStatsLoading(true);
                  try {
                    setStats(await call("dashboard"));
                  } catch (e) {
                    toast(e.message, true);
                  } finally {
                    setStatsLoading(false);
                  }
                }}
              >
                {statsLoading ? "正在统计…" : "加载学习概览"}
              </Button>
            )}
          </div>
        )}
        <div className="list-toolbar">
          <div className="search-box">
            <Search size={16} />
            <input
              aria-label="搜索课程内容"
              placeholder={
                work
                  ? "搜索题名、答案或编号…"
                  : course
                    ? "搜索作业、章节或编号…"
                    : "搜索课程名称或编号…"
              }
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                setPage(1);
              }}
            />
          </div>
          {course && (
            <select
              aria-label="筛选状态"
              value={filter}
              onChange={(e) => {
                setFilter(e.target.value);
                setPage(1);
              }}
            >
              <option value="all">全部状态</option>
              {work ? (
                <option value="answer">有答案</option>
              ) : (
                <>
                  <option value="available">可提交</option>
                  <option value="completed">已完成</option>
                </>
              )}
            </select>
          )}
          <select
            aria-label="排序"
            value={sort}
            onChange={(e) => setSort(e.target.value)}
          >
            <option value="default">默认排序</option>
            <option value="name">名称排序</option>
            {course && !work && <option value="deadline">截止时间</option>}
          </select>
        </div>
        {loading ? (
          <Skeleton />
        ) : error ? (
          <Empty
            icon={RefreshCw}
            title="暂时无法加载"
            action={
              <Button onClick={() => setRevision((r) => r + 1)}>重试</Button>
            }
          >
            {error}
          </Empty>
        ) : !rows.length ? (
          <Empty
            icon={Search}
            title={query ? "没有匹配结果" : "这里还没有内容"}
          >
            {query ? "试试其他关键词。" : "刷新以获取服务器最新数据。"}
          </Empty>
        ) : work ? (
          <div className="question-layout">
            <div className="question-list">
              {visible.map((q, i) => (
                <button
                  key={String(q.id) + i}
                  className={selected === q ? "selected" : ""}
                  onClick={() => {
                    setSelected(q);
                    setAnswer(false);
                  }}
                >
                  <span>{(currentPage - 1) * 20 + i + 1}</span>
                  <div>
                    <strong>{q.name || `题目 ${q.id}`}</strong>
                    <small>编号 {q.id}</small>
                  </div>
                </button>
              ))}
            </div>
            {selected && (
              <section className="question-detail">
                <span className="section-label">题目 {selected.id}</span>
                <h2>{selected.name || "题目详情"}</h2>
                {selected.imgurl && selected.imgurl !== "N/A" ? (
                  <QuestionImage url={selected.imgurl} />
                ) : (
                  <p className="muted">该题目没有图片。</p>
                )}
                <Button onClick={() => setAnswer(!answer)}>
                  {answer ? "收起答案" : "查看答案"}
                </Button>
                {answer && (
                  <div className="answer">
                    <strong>参考答案</strong>
                    <p>{String(selected.answer ?? "暂无答案")}</p>
                  </div>
                )}
                <div className="row-actions">
                  <Button
                    icon={ArrowUpRight}
                    onClick={async () => {
                      try {
                        const ref = {
                          id: crypto.randomUUID(),
                          name: `${work.workName} · 题目 ${selected.id}.txt`,
                          text: `课程：${course.courseName}\n作业：${work.workName}\n题目：${selected.name || selected.id}\n参考答案：${selected.answer ?? "暂无"}`,
                        };
                        const files = [ref];
                        if (selected.imgurl && selected.imgurl !== "N/A")
                          files.push({
                            id: crypto.randomUUID(),
                            name: `题目 ${selected.id}.png`,
                            data: await call("question_image", selected.imgurl),
                          });
                        onReference(files);
                      } catch (e) {
                        toast(e.message, true);
                      }
                    }}
                  >
                    向 AI 请教这道题
                  </Button>
                </div>
                <div className="grade-form">
                  <label>
                    提交本作业成绩
                    <input
                      aria-label="提交成绩"
                      type="number"
                      min="0"
                      max="100"
                      step="1"
                      value={grade}
                      onChange={(e) => setGrade(e.target.value)}
                    />
                  </label>
                  <Button
                    icon={Check}
                    disabled={taskBusy || !/^(100|[1-9]?\d)$/.test(grade)}
                    onClick={() =>
                      setConfirm({
                        title: "确认提交成绩",
                        text: `将为“${work.workName}”提交 ${grade} 分，会消耗一次提交机会。`,
                        action: async () => {
                          await call("submit_grade", work.workId, grade);
                          toast("成绩已提交");
                          setRevision((r) => r + 1);
                        },
                      })
                    }
                  >
                    提交成绩
                  </Button>
                </div>
              </section>
            )}
          </div>
        ) : (
          <div className={course ? "assignment-list" : "course-grid"}>
            {visible.map((r, i) =>
              course ? (
                <button
                  className="assignment-row"
                  key={String(r.workId) + i}
                  onClick={() => setWork(r)}
                >
                  <span className="assignment-icon">
                    <FileQuestion size={21} />
                  </span>
                  <div>
                    <strong>{r.workName}</strong>
                    <small>
                      {r.chapterName || "作业"}
                      {r.expireTime ? ` · 截止 ${r.expireTime}` : ""}
                    </small>
                  </div>
                  <Badge
                    status={r.grade != null && r.grade !== "" ? "success" : ""}
                  >
                    {r.grade != null && r.grade !== ""
                      ? `${r.grade} 分`
                      : `剩余 ${Math.max(0, Number(r.tryTimes || 0) - Number(r.times || 0))} 次`}
                  </Badge>
                  <ArrowRight size={17} />
                </button>
              ) : (
                <button
                  className="course-card"
                  key={String(r.courseId) + i}
                  onClick={() => setCourse(r)}
                >
                  <div className="course-card-top">
                    <span className="course-icon">
                      <BookOpen size={24} />
                    </span>
                    <ArrowUpRight size={17} />
                  </div>
                  <h2>{r.courseName}</h2>
                  <span>课程编号 {r.courseId}</span>
                  <div className="course-card-bottom">
                    进入课程
                    <ArrowRight size={16} />
                  </div>
                </button>
              ),
            )}
          </div>
        )}
        {rows.length > 20 && (
          <div className="pagination">
            <Button
              icon={ArrowLeft}
              label="上一页"
              disabled={currentPage === 1}
              onClick={() => setPage(currentPage - 1)}
            />
            <span>
              {currentPage} / {pages} 页 · 共 {rows.length} 项
            </span>
            <Button
              icon={ArrowRight}
              label="下一页"
              disabled={currentPage === pages}
              onClick={() => setPage(currentPage + 1)}
            />
          </div>
        )}
        {!work && data.length > 0 && (
          <div className="batch-footer">
            <span>批量操作会修改服务器数据。</span>
            <Button
              disabled={taskBusy}
              onClick={() => batch(course ? "submit_course" : "submit_all")}
            >
              批量提交 100 分…
            </Button>
          </div>
        )}
        {confirm && (
          <Confirm
            data={confirm}
            onClose={() => setConfirm(null)}
            toast={toast}
          />
        )}
      </div>
    </div>
  );
}
function Confirm({ data, onClose, toast }) {
  const [busy, setBusy] = useState(false);
  return (
    <Modal
      title={data.title}
      onClose={() => {
        if (!busy) onClose();
      }}
    >
      <p className="dialog-copy">{data.text}</p>
      <div className="dialog-actions">
        <Button disabled={busy} onClick={onClose}>
          取消
        </Button>
        <Button
          disabled={busy}
          className="primary"
          onClick={async () => {
            setBusy(true);
            try {
              await data.action();
              onClose();
            } catch (e) {
              toast(e.message, true);
            } finally {
              setBusy(false);
            }
          }}
        >
          {busy ? "正在提交…" : "确认提交"}
        </Button>
      </div>
    </Modal>
  );
}
