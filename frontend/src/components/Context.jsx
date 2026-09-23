import React from "react";
import {
  PanelRightClose,
  Plus,
  FileText,
  FolderOpen,
  SlidersHorizontal,
  ArrowUpRight,
  ShieldCheck,
  Activity,
  BrainCircuit,
} from "lucide-react";
import { Button, Badge, Busy } from "./ui";
export default function Context({
  onClose,
  settings,
  connected,
  onSettings,
  attachments,
  onAttach,
  task,
  job,
  onWorkspace,
}) {
  return (
    <aside className="context-panel">
      <div className="context-heading">
        <span>上下文</span>
        <Button icon={PanelRightClose} label="收起上下文" onClick={onClose} />
      </div>
      <section>
        <div className="section-heading">
          <h3>当前工作区</h3>
          <FolderOpen size={15} />
        </div>
        <button className="context-workspace" onClick={onWorkspace}>
          <span className="workspace-avatar">L</span>
          <span>
            <strong>个人工作空间</strong>
            <small>{task || "专注当下的学习与探索"}</small>
          </span>
          <ArrowUpRight size={14} />
        </button>
      </section>
      <section>
        <div className="section-heading">
          <h3>本次引用</h3>
          <span>{attachments.length}</span>
        </div>
        {attachments.length ? (
          <div className="context-files">
            {attachments.map((a) => (
              <div key={a.id}>
                <FileText size={16} />
                <span>{a.name}</span>
              </div>
            ))}
          </div>
        ) : (
          <p className="context-hint">添加资料，让回答贴近你的问题。</p>
        )}
        <button className="add-context" onClick={onAttach}>
          <Plus size={16} />
          添加文件
        </button>
      </section>
      <section>
        <div className="section-heading">
          <h3>模型</h3>
          <Button
            icon={SlidersHorizontal}
            label="设置模型参数"
            onClick={onSettings}
          />
        </div>
        <div className="model-card">
          <span className="model-emblem">
            <BrainCircuit size={22} />
          </span>
          <div>
            <strong>{settings.model || "尚未选择模型"}</strong>
            <small>
              {settings.provider === "Local" ? "本地服务" : settings.provider}
            </small>
          </div>
        </div>
        <Badge status={connected ? "success" : ""}>
          {connected ? "Connected ✓" : "等待连接"}
        </Badge>
        <dl className="model-details">
          <div>
            <dt>Temperature</dt>
            <dd>{settings.temperature}</dd>
          </div>
          <div>
            <dt>上下文</dt>
            <dd>最近 {settings.contextMessages} 条</dd>
          </div>
          <div>
            <dt>长期记忆</dt>
            <dd>{settings.memoryEnabled ? "已开启" : "未开启"}</dd>
          </div>
        </dl>
        <button className="text-link" onClick={onSettings}>
          管理模型连接
          <ArrowUpRight size={13} />
        </button>
      </section>
      <section>
        <div className="section-heading">
          <h3>工具状态</h3>
          <Activity size={15} />
        </div>
        <div className="tool-row">
          <FileText size={15} />
          <span>文件引用</span>
          <span className="tool-ready">就绪</span>
        </div>
        <div className="tool-row">
          <FolderOpen size={15} />
          <span>题目导出</span>
          <span className="muted">
            {job?.kind === "task" && !job.done ? "运行中" : "待命"}
          </span>
        </div>
        {job && (
          <div className="context-job" role="status">
            {job.done ? <span>{job.status}</span> : <Busy>{job.status}</Busy>}
            {job.kind === "task" && !job.done && (
              <progress max={job.maximum || 100} value={job.progress} />
            )}
          </div>
        )}
      </section>
      <div className="context-footer">
        <ShieldCheck size={16} />
        <p>
          会话保存在本机
          <br />
          <span>模型仅接收你发送的内容</span>
        </p>
      </div>
    </aside>
  );
}
