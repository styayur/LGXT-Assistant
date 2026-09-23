import React, { useState } from "react";
import {
  Moon,
  Sun,
  Monitor,
  SlidersHorizontal,
  BrainCircuit,
  Database,
  Terminal,
  Download,
  Check,
  Link2,
  Save,
  FolderOpen,
  Trash2,
} from "lucide-react";
import { Button, Toggle, Badge, Busy } from "../ui";
import { call, providers, switchProvider } from "../../lib/bridge";
export default function Settings({
  settings,
  exportSettings,
  hasKey,
  onSave,
  onTheme,
  onConnection,
  initialTab = "general",
  toast,
  logs,
}) {
  const [tab, setTab] = useState(initialTab);
  const [form, setForm] = useState(settings);
  const [exports, setExports] = useState(exportSettings);
  const [key, setKey] = useState("");
  const [busy, setBusy] = useState("");
  const [connected, setConnected] = useState(false);
  const change = (k, v) => {
    setForm((f) => ({ ...f, [k]: v }));
    setConnected(false);
  };
  async function save(test = false) {
    setBusy(test ? "test" : "save");
    try {
      await onSave(form, key || null, exports);
      setKey("");
      if (test) {
        const r = await call("test_model");
        setConnected(r.connected);
        onConnection(r.connected);
        toast("Connected ✓ 模型已响应");
      } else toast("设置已保存");
    } catch (e) {
      toast(e.message, true);
      if (test) {
        setConnected(false);
        onConnection(false);
      }
    } finally {
      setBusy("");
    }
  }
  const field = (label, k, description, type = "text", extra = {}) => (
    <label className="field">
      <span>{label}</span>
      {description && <small>{description}</small>}
      <input
        type={type}
        value={form[k]}
        onChange={(e) => change(k, e.target.value)}
        {...extra}
      />
    </label>
  );
  const tabs = [
    ["general", "通用", SlidersHorizontal],
    ["models", "AI 模型", BrainCircuit],
    ["memory", "记忆与存储", Database],
    ["export", "导出", Download],
    ["advanced", "高级", Terminal],
  ];
  return (
    <div className="page-scroll">
      <div className="settings-page">
        <div className="page-heading">
          <div>
            <h1>设置</h1>
            <p>让工作空间适合你的使用习惯。</p>
          </div>
          <Button
            icon={Save}
            className="primary"
            disabled={!!busy}
            onClick={() => save()}
          >
            {busy === "save" ? "正在保存…" : "保存更改"}
          </Button>
        </div>
        <div className="settings-layout">
          <nav className="settings-tabs">
            {tabs.map(([id, label, Icon]) => (
              <button
                key={id}
                className={tab === id ? "active" : ""}
                onClick={() => setTab(id)}
              >
                <Icon size={17} />
                {label}
              </button>
            ))}
          </nav>
          <div className="settings-content">
            {tab === "general" && (
              <>
                <section className="settings-card">
                  <h2>外观</h2>
                  <p>选择适合当前环境的主题。</p>
                  <div className="theme-options">
                    {[
                      ["dark", "深色", Moon],
                      ["light", "浅色", Sun],
                      ["system", "跟随系统", Monitor],
                    ].map(([id, label, Icon]) => (
                      <button
                        key={id}
                        className={`theme-option ${form.theme === id ? "selected" : ""}`}
                        onClick={() => {
                          change("theme", id);
                          onTheme(id);
                        }}
                      >
                        <div className={`theme-preview ${id}`}>
                          <i />
                          <span>
                            <b />
                            <b />
                            <b />
                          </span>
                        </div>
                        <span>
                          <Icon size={15} />
                          {label}
                          {form.theme === id && <Check size={15} />}
                        </span>
                      </button>
                    ))}
                  </div>
                  <Toggle
                    label="减少动态效果"
                    description="关闭过渡与装饰动画，保留任务状态反馈。"
                    checked={form.reduceMotion}
                    onChange={(v) => change("reduceMotion", v)}
                  />
                </section>
                <section className="settings-card">
                  <h2>启动与语言</h2>
                  <label className="setting-row">
                    <span>
                      <strong>界面语言</strong>
                      <small>主导航与对话界面；课程数据保留原文。</small>
                    </span>
                    <select
                      value={form.language}
                      onChange={(e) => change("language", e.target.value)}
                    >
                      <option value="zh">简体中文</option>
                      <option value="en">English</option>
                    </select>
                  </label>
                  <label className="setting-row">
                    <span>
                      <strong>启动时打开</strong>
                      <small>继续上一次思路，或从空白开始。</small>
                    </span>
                    <select
                      value={form.startup}
                      onChange={(e) => change("startup", e.target.value)}
                    >
                      <option value="last">最近会话</option>
                      <option value="new">新会话</option>
                      <option value="courses">我的课程</option>
                    </select>
                  </label>
                </section>
              </>
            )}
            {tab === "models" && (
              <>
                <section className="settings-card">
                  <div className="card-heading">
                    <div>
                      <h2>模型连接</h2>
                      <p>连接你自己的云端服务或本地模型。</p>
                    </div>
                    <Badge status={connected ? "success" : ""}>
                      {connected ? "Connected ✓" : "尚未验证"}
                    </Badge>
                  </div>
                  <label className="field">
                    <span>Provider</span>
                    <select
                      value={form.provider}
                      onChange={(e) => {
                        setForm((f) => switchProvider(f, e.target.value));
                        setConnected(false);
                        setKey("");
                      }}
                    >
                      {Object.keys(providers).map((p) => (
                        <option key={p}>{p}</option>
                      ))}
                    </select>
                  </label>
                  {field(
                    "API Endpoint",
                    "endpoint",
                    "填写 API 基础地址，不包含 /chat/completions 或 /messages。",
                    "url",
                  )}
                  {field("模型 ID", "model", providers[form.provider].hint)}
                  <label className="field">
                    <span>API Key</span>
                    <small>
                      密钥保存在系统凭据管理器；留空保留该服务已有密钥。
                    </small>
                    <input
                      type="password"
                      autoComplete="new-password"
                      aria-label="API Key"
                      placeholder={
                        hasKey &&
                        form.endpoint === settings.endpoint &&
                        form.provider === settings.provider
                          ? "已保存密钥 · 输入可替换"
                          : "输入 API Key（本地模型可留空）"
                      }
                      value={key}
                      onChange={(e) => setKey(e.target.value)}
                    />
                  </label>
                  <div className="row-actions">
                    <Button
                      icon={Link2}
                      onClick={() => save(true)}
                      disabled={!!busy || !form.model.trim()}
                    >
                      {busy === "test" ? (
                        <Busy>正在测试…</Busy>
                      ) : (
                        "保存并测试连接"
                      )}
                    </Button>
                    <Button
                      icon={Trash2}
                      disabled={
                        !!busy ||
                        !hasKey ||
                        form.endpoint !== settings.endpoint ||
                        form.provider !== settings.provider
                      }
                      onClick={async () => {
                        try {
                          await call("remove_key");
                          await onSave(form, null, exports);
                          setConnected(false);
                          onConnection(false);
                          toast("已移除密钥");
                        } catch (e) {
                          toast(e.message, true);
                        }
                      }}
                    >
                      移除密钥
                    </Button>
                  </div>
                  <p className="field-note">
                    连接测试会发送一次简短请求，可能产生少量服务费用。图片附件需要模型支持视觉输入。
                  </p>
                </section>
                <section className="settings-card">
                  <h2>生成参数</h2>
                  <label className="field">
                    <span>
                      Temperature <b>{form.temperature}</b>
                    </span>
                    <small>
                      较低值更稳定，较高值更有变化；部分推理模型不支持自定义此参数。
                    </small>
                    <input
                      type="range"
                      min="0"
                      max="2"
                      step="0.1"
                      value={form.temperature}
                      onChange={(e) =>
                        change("temperature", Number(e.target.value))
                      }
                    />
                  </label>
                  <div className="field-grid">
                    {field(
                      "上下文消息数",
                      "contextMessages",
                      "发送最近多少条消息；附件也会占用上下文。",
                      "number",
                      { min: 2, max: 200 },
                    )}
                    {field(
                      "最大输出 Token",
                      "maxTokens",
                      "以所选模型的限制为准。",
                      "number",
                      { min: 128, max: 32768 },
                    )}
                  </div>
                </section>
              </>
            )}
            {tab === "memory" && (
              <>
                <section className="settings-card">
                  <h2>长期记忆</h2>
                  <Toggle
                    label="在新请求中加入学习偏好"
                    description="以下内容作为系统指令发送给所选模型；不会自动提取会话内容。"
                    checked={form.memoryEnabled}
                    onChange={(v) => change("memoryEnabled", v)}
                  />
                  <label className="field">
                    <span>学习偏好与长期背景</span>
                    <textarea
                      rows="6"
                      placeholder="例如：我正在学习大学物理，希望先理解直觉，再看公式推导。"
                      value={form.memory}
                      onChange={(e) => change("memory", e.target.value)}
                      maxLength={16000}
                    />
                  </label>
                </section>
                <section className="settings-card">
                  <h2>会话存储</h2>
                  <Toggle
                    label="在本机保存会话"
                    description="关闭后新消息仅保留在当前窗口；已有历史不会自动删除。"
                    checked={form.storeConversations}
                    onChange={(v) => change("storeConversations", v)}
                  />
                  <p className="field-note">
                    会话与附件保存在本机应用数据目录。可以在侧栏逐条删除，或先导出为
                    Markdown。
                  </p>
                </section>
                <section className="settings-card">
                  <h2>知识资料</h2>
                  <p>
                    在工作区添加文本、代码或图片，再附加到对话中。资料会随消息传给模型；当前使用文件引用，不进行自动向量检索。
                  </p>
                </section>
              </>
            )}
            {tab === "export" && (
              <section className="settings-card">
                <h2>题目导出</h2>
                <p>兼容原有 Word、PDF 格式与目录结构。</p>
                <label className="field">
                  <span>导出目录</span>
                  <div className="input-action">
                    <input
                      aria-label="导出目录"
                      value={exports.export_path}
                      onChange={(e) =>
                        setExports({ ...exports, export_path: e.target.value })
                      }
                    />
                    <Button
                      icon={FolderOpen}
                      label="选择导出目录"
                      onClick={async () => {
                        try {
                          const path = await call("choose_directory");
                          if (path)
                            setExports({ ...exports, export_path: path });
                        } catch (e) {
                          toast(e.message, true);
                        }
                      }}
                    />
                  </div>
                </label>
                {[
                  ["export_word", "Word 文档 (.docx)"],
                  ["export_word_include_answers", "Word 包含答案"],
                  ["export_pdf", "PDF 文档 (.pdf)"],
                  ["export_pdf_include_answers", "PDF 包含答案"],
                ].map(([k, label]) => (
                  <Toggle
                    key={k}
                    label={label}
                    checked={exports[k]}
                    onChange={(v) => setExports({ ...exports, [k]: v })}
                  />
                ))}
              </section>
            )}
            {tab === "advanced" && (
              <>
                <section className="settings-card">
                  <h2>开发者选项</h2>
                  <Toggle
                    label="Debug 模式"
                    description="重启桌面应用后启用 WebView 开发者工具。"
                    checked={form.debug}
                    onChange={(v) => change("debug", v)}
                  />
                  <p className="field-note">
                    桌面架构：WebView2 + Python。原 Tk 界面可通过 --legacy
                    启动。
                  </p>
                </section>
                <section className="settings-card">
                  <h2>本次运行日志</h2>
                  <p>记录界面状态与错误，不记录密码或 API Key。</p>
                  <pre className="log-view">
                    {logs.length ? logs.join("\n") : "当前没有日志。"}
                  </pre>
                </section>
                <section className="settings-card">
                  <h2>关于 LGXT Assistant</h2>
                  <p>
                    理工学堂助手 · 桌面界面 4.0
                    <br />
                    StyAyur · GPL-3.0-or-later
                  </p>
                </section>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
