import React, { useState } from "react";
import {
  PanelLeftClose,
  Plus,
  Search,
  MessageSquare,
  BookOpen,
  FolderOpen,
  Library,
  Settings,
  ChevronDown,
  GraduationCap,
  MoreHorizontal,
  Command,
} from "lucide-react";
import { Button } from "../ui";
export default function Sidebar({
  page,
  go,
  conversations,
  current,
  onSelect,
  onNew,
  onManage,
  onPalette,
  onCollapse,
  username,
  language,
}) {
  const [query, setQuery] = useState("");
  const [limit, setLimit] = useState(40);
  const en = language === "en";
  const rows = conversations.filter((c) =>
    c.title.toLowerCase().includes(query.toLowerCase()),
  );
  return (
    <aside className="sidebar">
      <div className="brand-row">
        <div className="brand-mark">
          <GraduationCap size={22} />
        </div>
        <div>
          <strong>
            LGXT<span> Assistant</span>
          </strong>
          <small>{en ? "Your learning workspace" : "你的学习工作空间"}</small>
        </div>
        <Button icon={PanelLeftClose} label="收起侧栏" onClick={onCollapse} />
      </div>
      <button className="workspace-switch" onClick={() => go("workspace")}>
        <span className="workspace-avatar">L</span>
        <span>
          {en ? "Personal workspace" : "个人工作空间"}
          <small>{username || (en ? "Local workspace" : "本地工作区")}</small>
        </span>
        <ChevronDown size={15} />
      </button>
      <Button icon={Plus} className="new-chat" onClick={onNew}>
        {en ? "New conversation" : "新建会话"}
        <kbd>Ctrl N</kbd>
      </Button>
      <nav>
        {[
          {
            id: "chat",
            icon: MessageSquare,
            label: en ? "Assistant" : "学习助手",
          },
          { id: "courses", icon: BookOpen, label: en ? "Courses" : "我的课程" },
          {
            id: "workspace",
            icon: FolderOpen,
            label: en ? "Workspace" : "工作区",
          },
          {
            id: "prompts",
            icon: Library,
            label: en ? "Prompt library" : "提示词库",
          },
        ].map(({ id, icon: Icon, label }) => (
          <button
            key={id}
            className={`nav-item ${page === id ? "active" : ""}`}
            onClick={() => go(id)}
          >
            <Icon size={18} />
            {label}
            {id === "chat" && <span className="nav-tag">AI</span>}
          </button>
        ))}
      </nav>
      <div className="history-heading">
        <span>{en ? "Conversations" : "最近会话"}</span>
        <Button icon={Search} label="全局搜索" onClick={onPalette} />
      </div>
      <div className="history-search">
        <Search size={14} />
        <input
          aria-label="搜索历史会话"
          placeholder={en ? "Search conversations…" : "搜索会话…"}
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setLimit(40);
          }}
        />
      </div>
      <div className="history-list">
        {rows.slice(0, limit).map((c) => (
          <div
            className={`history-row ${c.id === current && page === "chat" ? "selected" : ""}`}
            key={c.id}
          >
            <button onClick={() => onSelect(c.id)}>
              <MessageSquare size={14} />
              <span>{c.title}</span>
            </button>
            <Button
              icon={MoreHorizontal}
              label={`管理会话 ${c.title}`}
              onClick={() => onManage(c)}
            />
          </div>
        ))}
        {!rows.length && (
          <p className="history-empty">
            {en
              ? "Your conversations will appear here"
              : "从一个问题开始，思路留在这里。"}
          </p>
        )}
        {rows.length > limit && (
          <Button onClick={() => setLimit(limit + 40)}>加载更多</Button>
        )}
      </div>
      <div className="sidebar-bottom">
        <button className="command-shortcut" onClick={onPalette}>
          <Command size={16} />
          <span>{en ? "Commands" : "搜索与命令"}</span>
          <kbd>Ctrl K</kbd>
        </button>
        <button
          className={`nav-item ${page === "settings" ? "active" : ""}`}
          onClick={() => go("settings")}
        >
          <Settings size={18} />
          {en ? "Settings" : "设置"}
          <span className="version">4.0</span>
        </button>
        <div className="profile">
          <span className="avatar">
            {username ? username[0].toUpperCase() : "L"}
          </span>
          <div>
            <strong>{username || (en ? "Local user" : "本地用户")}</strong>
            <small>{en ? "LGXT learning companion" : "理工学堂学习伙伴"}</small>
          </div>
          <span
            className="online-dot"
            title={username ? "理工学堂已连接" : "本地工作区"}
          />
        </div>
      </div>
    </aside>
  );
}
