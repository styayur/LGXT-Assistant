import React, { useState, useEffect, useRef, lazy, Suspense } from "react";
import {
  PanelLeft,
  PanelRight,
  ChevronRight,
  ChevronDown,
  Search,
  Download,
  Plus,
  X,
  LogIn,
  Trash2,
  Check,
  FileText,
  ArrowUpRight,
} from "lucide-react";
import Sidebar from "./components/sidebar/Sidebar";
import Context from "./components/Context";
import Chat from "./components/chat/Chat";
import CommandPalette from "./components/dialogs/CommandPalette";
import { Button, Toasts, Modal, Skeleton, Badge } from "./components/ui";
import {
  call,
  defaults,
  providers,
  uid,
  newConversation,
  isDesktop,
  isConnected,
  isBrowserApp,
  browserFiles,
  switchProvider,
  waitForBridge,
  withTimeout,
} from "./lib/bridge";
const Settings = lazy(() => import("./components/settings/Settings"));
const Courses = lazy(() => import("./components/Courses"));
const Workspace = lazy(() =>
  import("./components/Workspace").then((m) => ({ default: m.Workspace })),
);
const Prompts = lazy(() =>
  import("./components/Workspace").then((m) => ({ default: m.Prompts })),
);
export default function App() {
  const [ready, setReady] = useState(false),
    [desktop, setDesktop] = useState(false),
    [page, setPage] = useState("chat"),
    [settings, setSettings] = useState(defaults),
    [exportSettings, setExportSettings] = useState({}),
    [hasKey, setHasKey] = useState(false),
    [connected, setConnected] = useState(false),
    [username, setUsername] = useState(""),
    [savedUsername, setSavedUsername] = useState("");
  const [conversations, setConversations] = useState([]),
    [conversation, setConversation] = useState(newConversation),
    [draft, setDraft] = useState(""),
    [attachments, setAttachments] = useState([]),
    [files, setFiles] = useState([]),
    [task, setTask] = useState(""),
    [prompts, setPrompts] = useState([]),
    [busy, setBusy] = useState(false),
    [job, setJob] = useState(null);
  const [sidebar, setSidebar] = useState(() => innerWidth >= 1000),
    [context, setContext] = useState(() => innerWidth >= 1180),
    [palette, setPalette] = useState(false),
    [modal, setModal] = useState(null),
    [settingsTab, setSettingsTab] = useState("general"),
    [toasts, setToasts] = useState([]),
    [logs, setLogs] = useState([]),
    [startupError, setStartupError] = useState("");
  const active = useRef(conversation),
    cached = useRef(new Map()),
    drafts = useRef(new Map()),
    fileInput = useRef(),
    jobId = useRef(null),
    running = useRef(false),
    cancelled = useRef(false),
    saveQueue = useRef(Promise.resolve()),
    mounted = useRef(true),
    actions = useRef({});
  function toast(text, error = false) {
    const id = uid();
    setToasts((x) => [...x.slice(-3), { id, text: String(text), error }]);
    setLogs((x) => [
      ...x.slice(-99),
      `${new Date().toLocaleTimeString()} ${error ? "错误" : "状态"} ${String(text)}`,
    ]);
    setTimeout(
      () => {
        if (mounted.current) setToasts((x) => x.filter((t) => t.id !== id));
      },
      error ? 10000 : 4500,
    );
  }
  function applyConversation(c) {
    active.current = c;
    cached.current.set(c.id, c);
    if (settings.storeConversations && cached.current.size > 12) {
      const oldest = cached.current.keys().next().value;
      if (oldest !== c.id) cached.current.delete(oldest);
    }
    setConversation(c);
  }
  function persist(c) {
    c = { ...c, updated: Date.now() };
    cached.current.set(c.id, c);
    setConversations((rows) => [
      { id: c.id, title: c.title, updated: c.updated },
      ...rows.filter((x) => x.id !== c.id),
    ]);
    saveQueue.current = saveQueue.current
      .catch(() => {})
      .then(() => call("save_conversation", c))
      .catch((e) => toast(`会话未保存：${e.message}`, true));
    return saveQueue.current;
  }
  useEffect(() => {
    mounted.current = true;
    let disposed = false;
    let version = 0;
    async function init() {
      const thisVersion = ++version;
      try {
        setStartupError("");
        await waitForBridge();
        const b = await withTimeout(
          call("bootstrap"),
          15000,
          "读取本机资料超时。请关闭其他 LGXT 窗口后重试，资料不会被删除。",
        );
        if (disposed || thisVersion !== version) return;
        setSettings(b.settings);
        setExportSettings(b.export);
        setHasKey(b.hasKey);
        setConversations(b.conversations);
        setPrompts(b.prompts);
        setFiles(b.workspace?.files || []);
        setTask(b.workspace?.task || "");
        setUsername(b.username);
        setSavedUsername(b.savedUsername);
        setDesktop(isConnected());
        if (b.settings.startup === "last" && b.conversations.length) {
          try {
            const c = await withTimeout(
              call("conversation", b.conversations[0].id),
              5000,
              "最近会话读取超时",
            );
            if (c && !disposed && thisVersion === version) applyConversation(c);
          } catch (e) {
            if (!disposed)
              toast(
                `最近会话暂时无法恢复，可以新建会话继续使用。${e.message}`,
                true,
              );
          }
        }
        if (disposed || thisVersion !== version) return;
        if (b.settings.startup === "courses") setPage("courses");
        setReady(true);
        for (const warning of b.warnings || []) toast(warning, true);
        if (isConnected())
          withTimeout(call("credential_status"), 8000, "凭据库响应超时")
            .then((c) => {
              if (!disposed && thisVersion === version) {
                setHasKey(c.hasKey);
                setSavedUsername(c.savedUsername);
              }
            })
            .catch(() => {});
      } catch (e) {
        if (!disposed && thisVersion === version) setStartupError(e.message);
      }
    }
    const timer = setTimeout(init, 700);
    const bridgeReady = () => {
      clearTimeout(timer);
      init();
    };
    window.addEventListener("pywebviewready", bridgeReady);
    if (isDesktop()) bridgeReady();
    const onError = (e) => toast(e.detail, true);
    window.addEventListener("lgxt-error", onError);
    return () => {
      disposed = true;
      mounted.current = false;
      clearTimeout(timer);
      window.removeEventListener("pywebviewready", bridgeReady);
      window.removeEventListener("lgxt-error", onError);
    };
  }, []);
  useEffect(() => {
    const media = matchMedia("(prefers-color-scheme: dark)");
    const apply = () =>
      (document.documentElement.dataset.theme =
        settings.theme === "system"
          ? media.matches
            ? "dark"
            : "light"
          : settings.theme);
    apply();
    media.addEventListener("change", apply);
    document.documentElement.dataset.motion = settings.reduceMotion
      ? "reduced"
      : "normal";
    document.documentElement.lang = settings.language === "en" ? "en" : "zh-CN";
    return () => media.removeEventListener("change", apply);
  }, [settings.theme, settings.reduceMotion, settings.language]);
  useEffect(() => {
    if (!ready) return;
    const timer = setTimeout(
      () =>
        call("save_workspace", { files, task }).catch((e) =>
          toast(`工作区未保存：${e.message}`, true),
        ),
      500,
    );
    return () => clearTimeout(timer);
  }, [files, task, ready]);
  useEffect(() => {
    const resize = () => {
      if (innerWidth < 1180) setContext(false);
      if (innerWidth < 1000) setSidebar(false);
    };
    window.addEventListener("resize", resize);
    return () => window.removeEventListener("resize", resize);
  }, []);
  useEffect(() => {
    const key = (e) => {
      if (e.isComposing) return;
      if (e.key === "F11" && isDesktop()) {
        e.preventDefault();
        call("toggle_fullscreen").catch((e) => toast(e.message, true));
      }
      if (e.key === "Escape" && !document.querySelector("dialog[open]")) {
        e.preventDefault();
        actions.current.stop();
      }
      if (document.querySelector("dialog[open]")) return;
      if (
        e.ctrlKey &&
        (e.key.toLowerCase() === "k" ||
          (e.shiftKey && e.key.toLowerCase() === "p"))
      ) {
        e.preventDefault();
        setPalette(true);
      }
      if (e.ctrlKey && e.key.toLowerCase() === "n") {
        e.preventDefault();
        actions.current.newChat();
      }
      if (e.ctrlKey && e.key === "Enter" && e.target.tagName !== "TEXTAREA") {
        e.preventDefault();
        actions.current.send();
      }
    };
    window.addEventListener("keydown", key);
    return () => window.removeEventListener("keydown", key);
  }, []);
  function go(next) {
    setPage(next);
    if (innerWidth < 1000) setSidebar(false);
  }
  function modelSettings() {
    setSettingsTab("models");
    go("settings");
  }
  function storeDraft() {
    drafts.current.set(active.current.id, { draft, attachments });
  }
  function newChat() {
    if (running.current) {
      toast("请先停止当前生成或等待任务完成");
      return;
    }
    storeDraft();
    applyConversation(newConversation());
    setDraft("");
    setAttachments([]);
    go("chat");
  }
  async function selectConversation(id) {
    if (running.current) {
      toast("请先停止当前生成或等待任务完成");
      return;
    }
    try {
      storeDraft();
      await saveQueue.current;
      const c = cached.current.get(id) || (await call("conversation", id));
      if (!c) throw Error("未找到会话文件");
      applyConversation(c);
      const d = drafts.current.get(id);
      setDraft(d?.draft || "");
      setAttachments(d?.attachments || []);
      go("chat");
    } catch (e) {
      toast(e.message, true);
    }
  }
  async function saveSettings(values, key, exports) {
    if (
      running.current &&
      [
        "provider",
        "endpoint",
        "model",
        "temperature",
        "contextMessages",
        "maxTokens",
        "memory",
        "memoryEnabled",
      ].some((k) => values[k] !== settings[k])
    ) {
      throw Error("请先结束当前任务，再更改模型配置");
    }
    const r = await call("save_settings", values, key, exports);
    setSettings(r.settings);
    setHasKey(r.hasKey);
    setExportSettings(exports);
    setConnected(false);
    return r;
  }
  async function attach() {
    try {
      if (isDesktop()) {
        const added = await call("choose_files");
        addFiles(added);
      } else fileInput.current.click();
    } catch (e) {
      toast(e.message, true);
    }
  }
  function addFiles(added) {
    setFiles((f) => [...f, ...added].slice(-80));
    if (page === "chat") setAttachments((a) => [...a, ...added].slice(-8));
    if (added.length) toast(`已添加 ${added.length} 个文件`);
  }
  async function stop() {
    if (running.current && job?.kind === "chat") {
      cancelled.current = true;
      setJob((j) => ({ ...j, status: "正在停止…" }));
      try {
        if (jobId.current) await call("stop_chat", jobId.current);
      } catch (e) {
        toast(e.message, true);
      }
    }
  }
  async function generate(base) {
    if (running.current) return;
    running.current = true;
    cancelled.current = false;
    setBusy(true);
    go("chat");
    const assistant = {
      id: uid(),
      role: "assistant",
      content: "",
      model: settings.model,
    };
    let updated = { ...base, messages: [...base.messages, assistant] };
    applyConversation(updated);
    persist(base);
    setJob({ kind: "chat", status: "正在连接模型…", done: false });
    let text = "";
    let finalError = "";
    try {
      const id = await call("start_chat", base.messages);
      jobId.current = id;
      if (cancelled.current) await call("stop_chat", id);
      let offset = 0;
      let lastSave = Date.now();
      while (mounted.current) {
        const result = await call("poll_job", id, offset);
        offset = result.offset;
        text += result.delta;
        setJob(result);
        updated = {
          ...base,
          messages: [
            ...base.messages,
            {
              ...assistant,
              content: text,
              error: result.error,
              stopped: cancelled.current,
            },
          ],
        };
        applyConversation(updated);
        if (Date.now() - lastSave > 2500) {
          persist(updated);
          lastSave = Date.now();
        }
        if (result.done) {
          if (result.error) {
            finalError = result.error;
            toast(result.error, true);
            setConnected(false);
          } else if (!cancelled.current) setConnected(true);
          break;
        }
        await new Promise((r) => setTimeout(r, 85));
      }
    } catch (e) {
      finalError = e.message;
      toast(e.message, true);
      setConnected(false);
      if (jobId.current) call("stop_chat", jobId.current).catch(() => {});
      updated = {
        ...base,
        messages: [
          ...base.messages,
          { ...assistant, content: text, error: e.message },
        ],
      };
      applyConversation(updated);
    } finally {
      setJob((j) => ({
        ...j,
        done: true,
        status: cancelled.current
          ? "已停止"
          : finalError
            ? "生成失败"
            : "已完成",
      }));
      await persist(updated);
      jobId.current = null;
      running.current = false;
      setBusy(false);
    }
  }
  async function send() {
    if (page !== "chat") return;
    if (running.current || (!draft.trim() && !attachments.length)) return;
    if (!settings.model.trim()) {
      toast("先配置模型连接，即可开始对话");
      modelSettings();
      return;
    }
    const content = draft.trim();
    const refs = [...attachments];
    if (task.trim())
      refs.unshift({ id: uid(), name: "当前学习任务.txt", text: task });
    const m = { id: uid(), role: "user", content, attachments: refs };
    const base = {
      ...active.current,
      title: active.current.messages.length
        ? active.current.title
        : (content || attachments[0]?.name || "新会话").slice(0, 36),
      messages: [...active.current.messages, m],
    };
    setDraft("");
    setAttachments([]);
    drafts.current.delete(base.id);
    await generate(base);
  }
  async function exportChat() {
    try {
      const c = active.current;
      const markdown =
        `# ${c.title}\n\n` +
        c.messages
          .map(
            (m) =>
              `## ${m.role === "user" ? "你" : "LGXT Assistant"}\n\n${m.content}\n\n${(m.attachments || []).map((a) => `> 附件：${a.name}`).join("\n")}`,
          )
          .join("\n\n");
      if (await call("export_chat", c.title, markdown)) toast("会话已导出");
    } catch (e) {
      toast(e.message, true);
    }
  }
  async function startTask(action, course, work) {
    if (running.current) {
      toast("请等待当前任务完成");
      return;
    }
    running.current = true;
    setBusy(true);
    let text = "";
    try {
      const id = await call("start_task", action, course, work);
      jobId.current = id;
      let offset = 0;
      while (mounted.current) {
        const result = await call("poll_job", id, offset);
        offset = result.offset;
        text += result.delta;
        setJob(result);
        if (result.done) {
          if (result.error) throw Error(result.error);
          setModal({ type: "result", text });
          toast("任务结束，请查看详细结果");
          break;
        }
        await new Promise((r) => setTimeout(r, 300));
      }
    } catch (e) {
      toast(e.message, true);
      setJob((j) => ({
        ...j,
        done: true,
        error: e.message,
        status: "任务失败",
      }));
    } finally {
      running.current = false;
      setBusy(false);
      jobId.current = null;
    }
  }
  actions.current = { newChat, send, stop };
  const commands = [
    {
      label: "新建会话",
      keywords: "new chat",
      shortcut: "Ctrl N",
      run: newChat,
    },
    {
      label: "打开设置",
      keywords: "settings",
      run: () => {
        setSettingsTab("general");
        go("settings");
      },
    },
    { label: "我的课程", keywords: "courses", run: () => go("courses") },
    { label: "工作区", keywords: "workspace", run: () => go("workspace") },
    { label: "打开文件 / 添加上下文", keywords: "open file", run: attach },
    { label: "提示词库", keywords: "prompts", run: () => go("prompts") },
    { label: "导出当前会话", run: exportChat },
    {
      label: "切换深色 / 浅色主题",
      run: async () => {
        try {
          await saveSettings(
            {
              ...settings,
              theme: settings.theme === "dark" ? "light" : "dark",
            },
            null,
            exportSettings,
          );
        } catch (e) {
          toast(e.message, true);
        }
      },
    },
    ...Object.keys(providers).map((p) => ({
      label: `切换模型服务 · ${p}`,
      keywords: "model",
      run: async () => {
        try {
          if (p !== settings.provider)
            await saveSettings(
              switchProvider(settings, p),
              null,
              exportSettings,
            );
          if (settings.profiles?.[p]?.model) {
            go("chat");
            toast(`已切换至 ${settings.profiles[p].model}`);
          } else modelSettings();
        } catch (e) {
          toast(e.message, true);
        }
      },
    })),
    ...conversations.map((c) => ({
      label: `会话 · ${c.title}`,
      run: () => selectConversation(c.id),
    })),
    ...files.map((f) => ({
      label: `引用文件 · ${f.name}`,
      run: () => {
        setAttachments((a) => [...a.filter((x) => x.id !== f.id), f].slice(-8));
        go("chat");
      },
    })),
  ];
  const titles = {
    chat: settings.language === "en" ? "Assistant" : "学习助手",
    courses: "我的课程",
    workspace: "工作区",
    prompts: "提示词库",
    settings: "设置",
  };
  if (startupError)
    return (
      <div className="fatal">
        <h1>暂时无法进入工作空间</h1>
        <p>{startupError}</p>
        <Button onClick={() => location.reload()}>重新连接</Button>
        <p className="muted">
          你的资料仍保留在本机。完整解压便携版，并保留 _internal
          文件夹；也可以重新下载单文件版。
        </p>
        <a
          href="https://github.com/styayur/LGXT-Assistant/releases/latest"
          target="_blank"
          rel="noreferrer"
        >
          下载完整版
        </a>
      </div>
    );
  if (!ready)
    return (
      <div className="startup">
        <span className="startup-mark">L</span>
        <h2>LGXT Assistant</h2>
        <p>正在准备工作空间…</p>
        <Skeleton />
      </div>
    );
  return (
    <div
      className={`app-shell ${sidebar ? "" : "sidebar-closed"} ${context ? "" : "context-closed"}`}
    >
      <Sidebar
        page={page}
        go={(p) => {
          if (p === "settings") setSettingsTab("general");
          go(p);
        }}
        conversations={conversations}
        current={conversation.id}
        onSelect={selectConversation}
        onNew={newChat}
        onManage={(c) => setModal({ type: "manage", c })}
        onPalette={() => setPalette(true)}
        onCollapse={() => setSidebar(false)}
        username={username}
        language={settings.language}
      />
      <main>
        <header className="topbar">
          <div className="breadcrumbs">
            {!sidebar && (
              <Button
                icon={PanelLeft}
                label="展开侧栏"
                onClick={() => setSidebar(true)}
              />
            )}
            <span>个人工作空间</span>
            <ChevronRight size={13} />
            <strong>{titles[page]}</strong>
          </div>
          <div className="topbar-actions">
            {isBrowserApp() && <span className="preview-badge" title="已连接 Windows 本机服务">Windows 网页版</span>}
            {!desktop && (
              <span
                className="preview-badge"
                title="浏览器预览可保存本地会话与设置；课程和模型调用需要桌面应用"
              >
                浏览器预览
              </span>
            )}
            {page === "chat" && (
              <>
                <button className="top-model" onClick={modelSettings}>
                  {settings.model || settings.provider}
                  <ChevronDown size={13} />
                </button>
                <Button
                  icon={Download}
                  label="导出会话"
                  disabled={!conversation.messages.length || busy}
                  onClick={exportChat}
                />
              </>
            )}
            <Button
              icon={Search}
              label="搜索与命令 Ctrl+K"
              onClick={() => setPalette(true)}
            />
            <Button
              icon={PanelRight}
              label={context ? "收起上下文面板" : "展开上下文面板"}
              onClick={() => setContext(!context)}
            />
          </div>
        </header>
        <div className="page-host">
          <Suspense fallback={<Skeleton />}>
            {page === "chat" && (
              <Chat
                conversation={conversation}
                draft={draft}
                setDraft={setDraft}
                onSend={send}
                onStop={stop}
                onEdit={(index) => setModal({ type: "edit", index })}
                onRegenerate={(index) =>
                  setModal({ type: "regenerate", index })
                }
                onExport={exportChat}
                onAttach={attach}
                attachments={attachments}
                removeAttachment={(id) =>
                  setAttachments((a) => a.filter((x) => x.id !== id))
                }
                busy={busy && job?.kind !== "task"}
                job={job}
                settings={settings}
                onSettings={modelSettings}
                onPrompt={() => go("prompts")}
                toast={toast}
              />
            )}
            {page === "settings" && (
              <Settings
                key={settingsTab}
                settings={settings}
                exportSettings={exportSettings}
                hasKey={hasKey}
                onSave={saveSettings}
                onTheme={(theme) => setSettings((s) => ({ ...s, theme }))}
                onConnection={setConnected}
                initialTab={settingsTab}
                toast={toast}
                logs={logs}
              />
            )}
            {page === "workspace" && (
              <Workspace
                files={files}
                onAdd={attach}
                onUse={(f) => {
                  setAttachments((a) =>
                    [...a.filter((x) => x.id !== f.id), f].slice(-8),
                  );
                  go("chat");
                }}
                onRemove={(id) => {
                  setFiles((f) => f.filter((x) => x.id !== id));
                  setAttachments((a) => a.filter((x) => x.id !== id));
                }}
                task={task}
                setTask={setTask}
              />
            )}
            {page === "prompts" && (
              <Prompts
                prompts={prompts}
                onUse={(text) => {
                  setDraft(text);
                  go("chat");
                }}
                onSave={async (list) => {
                  try {
                    await call("save_prompts", list);
                    setPrompts(list);
                    toast("提示词库已更新");
                  } catch (e) {
                    toast(e.message, true);
                  }
                }}
              />
            )}
            {page === "courses" && (
              <Courses
                username={username}
                onLogin={() => setModal({ type: "login" })}
                onLogout={async () => {
                  try {
                    await call("logout");
                    setUsername("");
                    toast("已退出理工学堂");
                  } catch (e) {
                    toast(e.message, true);
                  }
                }}
                onTask={startTask}
                taskBusy={busy}
                onReference={(refs) => {
                  setFiles((f) => [...f, ...refs].slice(-80));
                  setAttachments((a) => [...a, ...refs].slice(-8));
                  setDraft("请引导我分析这道题的解题思路。");
                  go("chat");
                }}
                toast={toast}
              />
            )}
          </Suspense>
        </div>
        {job?.kind === "task" && !job.done && (
          <div className="task-strip" role="status">
            <span className="status-dot" />
            {job.status}
            <progress max={job.maximum || 100} value={job.progress} />
          </div>
        )}
      </main>
      <Context
        onClose={() => setContext(false)}
        settings={settings}
        connected={connected}
        onSettings={modelSettings}
        attachments={attachments}
        onAttach={attach}
        task={task}
        job={job}
        onWorkspace={() => go("workspace")}
      />
      <input
        hidden
        ref={fileInput}
        type="file"
        multiple
        accept=".txt,.md,.py,.js,.ts,.json,.csv,.png,.jpg,.jpeg,.webp"
        onChange={async (e) => {
          try {
            addFiles(await browserFiles(e.target.files));
          } catch (err) {
            toast(err.message, true);
          }
          e.target.value = "";
        }}
      />
      {palette && (
        <CommandPalette commands={commands} onClose={() => setPalette(false)} />
      )}
      {modal?.type === "login" && (
        <Login
          savedUsername={savedUsername}
          onClose={() => setModal(null)}
          onDone={(r) => {
            setUsername(r.username);
            setModal(null);
            toast(r.warning || "已连接理工学堂");
          }}
          toast={toast}
        />
      )}
      {modal?.type === "manage" && (
        <Manage
          conversation={modal.c}
          onClose={() => setModal(null)}
          onRename={async (title) => {
            try {
              const c =
                cached.current.get(modal.c.id) ||
                (await call("conversation", modal.c.id));
              if (!c) throw Error("会话不存在");
              const updated = { ...c, title };
              if (active.current.id === c.id) applyConversation(updated);
              await persist(updated);
              setModal(null);
            } catch (e) {
              toast(e.message, true);
            }
          }}
          onDelete={() => setModal({ type: "delete", c: modal.c })}
        />
      )}
      {modal?.type === "delete" && (
        <Modal title="删除会话" onClose={() => setModal(null)}>
          <p className="dialog-copy">
            将删除“{modal.c.title}”及其中保存的消息与附件。
          </p>
          <div className="dialog-actions">
            <Button onClick={() => setModal(null)}>取消</Button>
            <Button
              className="danger"
              disabled={busy}
              icon={Trash2}
              onClick={async () => {
                try {
                  await saveQueue.current;
                  await call("delete_conversation", modal.c.id);
                  cached.current.delete(modal.c.id);
                  drafts.current.delete(modal.c.id);
                  setConversations((c) => c.filter((x) => x.id !== modal.c.id));
                  if (active.current.id === modal.c.id) newChat();
                  setModal(null);
                  toast("会话已删除");
                } catch (e) {
                  toast(e.message, true);
                }
              }}
            >
              删除会话
            </Button>
          </div>
        </Modal>
      )}
      {(modal?.type === "edit" || modal?.type === "regenerate") && (
        <Modal
          title={modal.type === "edit" ? "编辑这条消息" : "重新生成回复"}
          onClose={() => setModal(null)}
        >
          <p className="dialog-copy">
            此操作将替换该位置之后的消息。可先导出会话保留当前内容。
          </p>
          <div className="dialog-actions">
            <Button onClick={() => setModal(null)}>取消</Button>
            <Button
              className="primary"
              disabled={busy}
              onClick={() => {
                const m = modal;
                setModal(null);
                if (m.type === "edit") {
                  const msg = active.current.messages[m.index];
                  const c = {
                    ...active.current,
                    messages: active.current.messages.slice(0, m.index),
                  };
                  applyConversation(c);
                  persist(c);
                  setDraft(msg.content);
                  setAttachments(msg.attachments || []);
                } else {
                  const base = {
                    ...active.current,
                    messages: active.current.messages.slice(0, m.index),
                  };
                  generate(base);
                }
              }}
            >
              继续
            </Button>
          </div>
        </Modal>
      )}
      {modal?.type === "result" && (
        <Modal title="任务结果" wide onClose={() => setModal(null)}>
          <pre className="result-text">{modal.text}</pre>
          <div className="dialog-actions">
            <Button onClick={() => setModal(null)}>完成</Button>
          </div>
        </Modal>
      )}
      <Toasts
        items={toasts}
        dismiss={(id) => setToasts((t) => t.filter((x) => x.id !== id))}
      />
    </div>
  );
}
function Login({ savedUsername, onClose, onDone, toast }) {
  const attempt = useRef(null);
  const [username, setUsername] = useState(savedUsername),
    [password, setPassword] = useState(""),
    [remember, setRemember] = useState(false),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  function cancel() {
    if (attempt.current) call("cancel_login", attempt.current).catch(() => {});
    attempt.current = null;
    onClose();
  }
  return (
    <Modal title="连接理工学堂" onClose={cancel}>
      <p className="dialog-copy">使用理工学堂账号同步你的课程与作业。</p>
      <form
        onSubmit={async (e) => {
          e.preventDefault();
          if (busy) return;
          const id = uid();
          attempt.current = id;
          setError("");
          setBusy(true);
          try {
            const result = await withTimeout(
              call("login", username, password, remember, id),
              20000,
              "登录超时。请检查网络后重试；也可以取消并继续使用其他功能。",
            );
            if (attempt.current === id) {
              attempt.current = null;
              onDone(result);
            }
          } catch (e) {
            if (attempt.current === id) {
              setError(e.message);
              call("cancel_login", id).catch(() => {});
            }
          } finally {
            if (attempt.current === id) {
              attempt.current = null;
              setBusy(false);
            }
          }
        }}
      >
        <label className="field">
          <span>账号</span>
          <input
            autoFocus
            required
            autoComplete="username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
          />
        </label>
        <label className="field">
          <span>密码</span>
          <input
            type="password"
            autoComplete="current-password"
            placeholder={savedUsername ? "留空可使用已保存的密码" : ""}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>
        <label className="checkbox-row">
          <input
            type="checkbox"
            checked={remember}
            onChange={(e) => setRemember(e.target.checked)}
          />
          在系统凭据库中记住账号
        </label>
        {error && (
          <p className="inline-error" role="alert">
            {error}
          </p>
        )}
        <div className="dialog-actions">
          <Button type="button" onClick={cancel}>
            取消
          </Button>
          <Button
            icon={LogIn}
            className="primary"
            disabled={busy}
            type="submit"
          >
            {busy ? "正在连接…" : "登录"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
function Manage({ conversation, onClose, onRename, onDelete }) {
  const [title, setTitle] = useState(conversation.title);
  return (
    <Modal title="管理会话" onClose={onClose}>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (title.trim()) onRename(title.trim());
        }}
      >
        <label className="field">
          <span>会话名称</span>
          <input
            autoFocus
            maxLength={80}
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
        </label>
        <div className="dialog-actions">
          <Button
            type="button"
            icon={Trash2}
            className="danger"
            onClick={onDelete}
          >
            删除会话
          </Button>
          <Button
            type="submit"
            icon={Check}
            className="primary"
            disabled={!title.trim()}
          >
            保存名称
          </Button>
        </div>
      </form>
    </Modal>
  );
}
