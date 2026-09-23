import React, { lazy, Suspense, useEffect, useRef, useState } from "react";
import {
  ArrowUp,
  ArrowDown,
  Paperclip,
  Square,
  Copy,
  Pencil,
  RotateCcw,
  Download,
  BookOpen,
  Sparkles,
  Code2,
  ArrowUpRight,
  FileText,
  X,
  BrainCircuit,
  Plus,
  ChevronDown,
  GraduationCap,
} from "lucide-react";
import { Button, Busy } from "../ui";
const Markdown = lazy(() => import("./Markdown"));
export default function Chat({
  conversation,
  draft,
  setDraft,
  onSend,
  onStop,
  onEdit,
  onRegenerate,
  onExport,
  onAttach,
  attachments,
  removeAttachment,
  busy,
  job,
  settings,
  onSettings,
  onPrompt,
  toast,
}) {
  const scroller = useRef();
  const input = useRef();
  const follow = useRef(true);
  const [limit, setLimit] = useState(40);
  const [atBottom, setAtBottom] = useState(true);
  const en = settings.language === "en";
  useEffect(() => {
    setLimit(40);
    follow.current = true;
    input.current?.focus();
  }, [conversation.id]);
  useEffect(() => {
    if (follow.current && scroller.current)
      scroller.current.scrollTop = scroller.current.scrollHeight;
  }, [conversation.messages]);
  useEffect(() => {
    const el = input.current;
    if (el) {
      el.style.height = "auto";
      el.style.height = Math.min(el.scrollHeight, 180) + "px";
    }
  }, [draft]);
  const scrollBottom = () => {
    follow.current = true;
    scroller.current.scrollTo({
      top: scroller.current.scrollHeight,
      behavior: settings.reduceMotion ? "instant" : "smooth",
    });
  };
  const suggestions = [
    {
      icon: BookOpen,
      title: en ? "Understand a concept" : "把知识真正弄懂",
      desc: en
        ? "Break complex ideas into clear steps"
        : "拆解概念，理清推导过程",
      prompt: "请用直观的例子和逐步推导，帮我理解一个知识点：",
    },
    {
      icon: Code2,
      title: en ? "Think through a problem" : "一起推敲一道题",
      desc: en ? "Explore an approach, step by step" : "分析题意，找到解题思路",
      prompt: "请先引导我分析题意，再逐步讲解解题方法：",
    },
    {
      icon: Sparkles,
      title: en ? "Make a study plan" : "安排下一步学习",
      desc: en ? "Build a plan that works for you" : "整理重点，制定复习计划",
      prompt: "请根据我的学习目标和可用时间，制定一份可执行的复习计划：",
    },
  ];
  return (
    <div className="chat-page">
      <div
        className="chat-scroll"
        ref={scroller}
        onScroll={() => {
          const e = scroller.current;
          follow.current = e.scrollHeight - e.scrollTop - e.clientHeight < 100;
          setAtBottom(follow.current);
        }}
      >
        {!conversation.messages.length ? (
          <div className="welcome">
            <div className="welcome-symbol">
              <GraduationCap size={38} strokeWidth={1.35} />
            </div>
            <div className="welcome-kicker">LGXT Assistant</div>
            <h1>
              {en ? "Space for your next idea." : "让每一个问题，都更进一步。"}
            </h1>
            <p>
              {en
                ? "Explore a concept, work through a problem, or bring your course materials."
                : "理解知识、梳理解题思路，或带着课程资料一起探索。"}
              <br />
              {en
                ? "Start here, at your own pace."
                : "从这里开始，按你的节奏学习。"}
            </p>
            <div className="suggestion-grid">
              {suggestions.map((s) => (
                <button
                  key={s.title}
                  onClick={() => {
                    setDraft(s.prompt);
                    input.current.focus();
                  }}
                >
                  <s.icon size={20} />
                  <strong>{s.title}</strong>
                  <span>{s.desc}</span>
                  <ArrowUpRight size={15} className="suggestion-arrow" />
                </button>
              ))}
            </div>
            <button className="text-link" onClick={onPrompt}>
              {en ? "Explore prompt library" : "探索提示词库"}
              <ArrowUpRight size={14} />
            </button>
          </div>
        ) : (
          <div className="messages">
            {conversation.messages.length > limit && (
              <Button
                className="load-earlier"
                onClick={() => {
                  follow.current = false;
                  setLimit(limit + 40);
                }}
              >
                加载更早的 40 条消息
              </Button>
            )}
            {conversation.messages.slice(-limit).map((m, index) => {
              const actual =
                conversation.messages.length -
                Math.min(limit, conversation.messages.length) +
                index;
              return (
                <article key={m.id} className={`message ${m.role}`}>
                  <div className="message-byline">
                    <span
                      className={`message-avatar ${m.role === "assistant" ? "ai" : ""}`}
                    >
                      {m.role === "assistant" ? (
                        <GraduationCap size={17} />
                      ) : (
                        "你"
                      )}
                    </span>
                    <strong>
                      {m.role === "assistant"
                        ? "LGXT Assistant"
                        : en
                          ? "You"
                          : "你"}
                    </strong>
                    <span>
                      {m.role === "assistant" ? m.model || settings.model : ""}
                    </span>
                  </div>
                  <div className="message-body">
                    {m.attachments?.length > 0 && (
                      <div className="attachment-list">
                        {m.attachments.map((a) => (
                          <div className="file-chip" key={a.id}>
                            {a.data ? (
                              <img src={a.data} alt={a.name} />
                            ) : (
                              <FileText size={17} />
                            )}
                            <span>{a.name}</span>
                          </div>
                        ))}
                      </div>
                    )}
                    {m.content ? (
                      <Suspense
                        fallback={<p className="plain-message">{m.content}</p>}
                      >
                        <Markdown text={m.content} />
                      </Suspense>
                    ) : busy && actual === conversation.messages.length - 1 ? (
                      <div className="thinking">
                        <BrainCircuit size={17} />
                        <span>{job?.status || "等待模型响应"}</span>
                        <i />
                        <i />
                        <i />
                      </div>
                    ) : (
                      <p className="muted">{m.error || "未生成内容"}</p>
                    )}
                    {m.error && m.content && (
                      <p className="inline-error">{m.error}</p>
                    )}
                    {m.stopped && <span className="muted">已停止生成</span>}
                    <div className="message-actions">
                      <Button
                        icon={Copy}
                        label="复制消息"
                        disabled={!m.content}
                        onClick={async () => {
                          try {
                            await navigator.clipboard.writeText(m.content);
                            toast("已复制");
                          } catch {
                            toast("复制失败，请选择文字后按 Ctrl+C", true);
                          }
                        }}
                      />
                      {m.role === "user" ? (
                        <Button
                          icon={Pencil}
                          label="编辑消息"
                          disabled={busy}
                          onClick={() => onEdit(actual)}
                        />
                      ) : (
                        <Button
                          icon={RotateCcw}
                          label="重新生成"
                          disabled={busy}
                          onClick={() => onRegenerate(actual)}
                        />
                      )}
                      <Button
                        icon={Download}
                        label="导出会话"
                        disabled={busy}
                        onClick={onExport}
                      />
                    </div>
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </div>
      {!atBottom && (
        <Button
          icon={ArrowDown}
          label="回到最新消息"
          className="jump-bottom"
          onClick={scrollBottom}
        />
      )}
      <div className="composer-area">
        <div className="composer">
          {attachments.length > 0 && (
            <div className="attachment-list composer-files">
              {attachments.map((a) => (
                <div className="file-chip" key={a.id}>
                  {a.data ? (
                    <img src={a.data} alt="" />
                  ) : (
                    <FileText size={17} />
                  )}
                  <span>{a.name}</span>
                  <Button
                    icon={X}
                    label={`移除 ${a.name}`}
                    onClick={() => removeAttachment(a.id)}
                  />
                </div>
              ))}
            </div>
          )}
          <textarea
            ref={input}
            aria-label="消息输入"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder={
              en
                ? "Ask anything, or add a file for context…"
                : "想从哪里开始？输入问题，或添加文件作为上下文…"
            }
            onKeyDown={(e) => {
              if (
                e.ctrlKey &&
                e.key === "Enter" &&
                !e.nativeEvent.isComposing
              ) {
                e.preventDefault();
                onSend();
              }
            }}
          />
          <div className="composer-toolbar">
            <div>
              <Button icon={Plus} label="添加上下文文件" onClick={onAttach} />
              <span className="composer-divider" />
              <button className="model-chip" onClick={onSettings}>
                <span className="model-dot" />
                {settings.model || (en ? "Select model" : "选择模型")}
                <ChevronDown size={13} />
              </button>
            </div>
            <div>
              <span className="send-hint">Ctrl ↵</span>
              {busy ? (
                <Button
                  icon={Square}
                  label="停止生成"
                  className="send-button stop"
                  onClick={onStop}
                />
              ) : (
                <Button
                  icon={ArrowUp}
                  label="发送消息"
                  className="send-button"
                  disabled={!draft.trim() && !attachments.length}
                  onClick={onSend}
                />
              )}
            </div>
          </div>
        </div>
        <p className="composer-note">
          {busy ? (
            <Busy>{job?.status || "正在连接模型"}</Busy>
          ) : en ? (
            "AI can make mistakes. Check important information."
          ) : (
            "AI 可能出错，请核实重要信息。"
          )}
          {!busy && (
            <span>
              {en
                ? "Your files are sent only with your message."
                : "文件仅在发送消息时交给所选模型。"}
            </span>
          )}
        </p>
      </div>
    </div>
  );
}
