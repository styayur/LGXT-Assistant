import React, { useState } from "react";
import {
  FolderOpen,
  Plus,
  FileText,
  ArrowUpRight,
  Trash2,
  Check,
  Library,
  Search,
} from "lucide-react";
import { Button, Empty, Modal } from "./ui";
export function Workspace({ files, onAdd, onUse, onRemove, task, setTask }) {
  return (
    <div className="page-scroll">
      <div className="content-page">
        <div className="page-heading">
          <div>
            <h1>工作区</h1>
            <p>把学习资料和当前任务放在一起。</p>
          </div>
          <Button icon={Plus} className="primary" onClick={onAdd}>
            添加资料
          </Button>
        </div>
        <section className="task-card">
          <span className="section-label">当前学习任务</span>
          <input
            aria-label="当前学习任务"
            placeholder="这次想完成什么？例如：理解动量守恒的适用条件"
            value={task}
            onChange={(e) => setTask(e.target.value)}
          />
          <small>保存在本机工作区 · 发送消息时作为上下文引用</small>
        </section>
        <div className="section-heading">
          <h2>上下文资料</h2>
          <span>{files.length} 个文件</span>
        </div>
        {files.length ? (
          <div className="file-grid">
            {files.map((f) => (
              <div className="file-card" key={f.id}>
                {f.data ? (
                  <img src={f.data} alt={f.name} />
                ) : (
                  <div className="file-preview">
                    <FileText size={30} />
                    <span>{f.name.split(".").pop()?.toUpperCase()}</span>
                  </div>
                )}
                <div className="file-card-info">
                  <strong>{f.name}</strong>
                  <small>
                    {Math.max(1, Math.round((f.size || 0) / 1024))} KB ·{" "}
                    {f.data ? "图片" : "文本资料"}
                  </small>
                </div>
                <div className="row-actions">
                  <Button icon={ArrowUpRight} onClick={() => onUse(f)}>
                    引用到对话
                  </Button>
                  <Button
                    icon={Trash2}
                    label={`移除资料 ${f.name}`}
                    onClick={() => onRemove(f.id)}
                  />
                </div>
              </div>
            ))}
          </div>
        ) : (
          <Empty
            icon={FolderOpen}
            title="给思考多一点上下文"
            action={
              <Button icon={Plus} onClick={onAdd}>
                选择文件
              </Button>
            }
          >
            添加笔记、代码或题目图片，在发送前选择需要引用的资料。
          </Empty>
        )}
      </div>
    </div>
  );
}
export const builtInPrompts = [
  {
    id: "concept",
    title: "概念拆解",
    category: "理解知识",
    text: "请帮我深入理解以下概念。先给出直观解释，再介绍关键公式、适用条件和常见误区，最后用一道小题检查我的理解：",
  },
  {
    id: "solve",
    title: "分步解题",
    category: "解题思路",
    text: "请作为学习导师，引导我分析以下题目。先列出已知条件与目标，再提示解题方向，不要直接跳到最终答案：",
  },
  {
    id: "review",
    title: "复习计划",
    category: "学习规划",
    text: "请为我制定一份复习计划。先询问学习范围、薄弱环节和剩余时间，再安排每天的重点、练习与回顾：",
  },
  {
    id: "code",
    title: "代码走读",
    category: "编程学习",
    text: "请解释以下代码的执行流程，指出潜在问题，给出可运行的小例子帮助我理解：",
  },
];
export function Prompts({ prompts, onUse, onSave }) {
  const [query, setQuery] = useState("");
  const [editing, setEditing] = useState(null);
  const all = [...prompts, ...builtInPrompts].filter((p) =>
    (p.title + p.text).toLowerCase().includes(query.toLowerCase()),
  );
  return (
    <div className="page-scroll">
      <div className="content-page">
        <div className="page-heading">
          <div>
            <h1>提示词库</h1>
            <p>把好用的提问方式，变成下一次的起点。</p>
          </div>
          <Button
            icon={Plus}
            className="primary"
            onClick={() =>
              setEditing({
                id: crypto.randomUUID(),
                title: "",
                text: "",
                category: "我的模板",
              })
            }
          >
            新建提示词
          </Button>
        </div>
        <div className="search-box">
          <Search size={17} />
          <input
            placeholder="搜索提示词与工作流…"
            aria-label="搜索提示词"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
        <div className="prompt-grid">
          {all.map((p) => (
            <article className="prompt-card" key={p.id}>
              <span className="prompt-category">
                <Library size={15} />
                {p.category}
              </span>
              <h2>{p.title}</h2>
              <p>{p.text}</p>
              <div className="row-actions">
                <Button icon={ArrowUpRight} onClick={() => onUse(p.text)}>
                  使用模板
                </Button>
                {prompts.some((x) => x.id === p.id) && (
                  <Button
                    label={`编辑提示词 ${p.title}`}
                    onClick={() => setEditing({ ...p })}
                  >
                    编辑
                  </Button>
                )}
              </div>
            </article>
          ))}
        </div>
        {!all.length && (
          <Empty icon={Search} title="没有找到提示词">
            试试更短的关键词，或创建自己的模板。
          </Empty>
        )}
        {editing && (
          <Modal title="编辑提示词" onClose={() => setEditing(null)}>
            <form
              onSubmit={async (e) => {
                e.preventDefault();
                await onSave([
                  editing,
                  ...prompts.filter((p) => p.id !== editing.id),
                ]);
                setEditing(null);
              }}
            >
              <label className="field">
                <span>名称</span>
                <input
                  required
                  autoFocus
                  maxLength={80}
                  value={editing.title}
                  onChange={(e) =>
                    setEditing({ ...editing, title: e.target.value })
                  }
                />
              </label>
              <label className="field">
                <span>提示词内容</span>
                <textarea
                  required
                  rows={7}
                  maxLength={16000}
                  value={editing.text}
                  onChange={(e) =>
                    setEditing({ ...editing, text: e.target.value })
                  }
                />
              </label>
              <div className="dialog-actions">
                {prompts.some((p) => p.id === editing.id) && (
                  <Button
                    type="button"
                    icon={Trash2}
                    className="danger"
                    onClick={async () => {
                      await onSave(prompts.filter((p) => p.id !== editing.id));
                      setEditing(null);
                    }}
                  >
                    删除
                  </Button>
                )}
                <Button type="submit" icon={Check} className="primary">
                  保存提示词
                </Button>
              </div>
            </form>
          </Modal>
        )}
      </div>
    </div>
  );
}
