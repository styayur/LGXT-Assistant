import React, { useState } from "react";
import { Search, ArrowUpRight, Command } from "lucide-react";
import { Modal } from "../ui";
export default function CommandPalette({ commands, onClose }) {
  const [query, setQuery] = useState("");
  const [index, setIndex] = useState(0);
  const filtered = commands
    .filter((c) =>
      (c.label + " " + (c.keywords || ""))
        .toLowerCase()
        .includes(query.toLowerCase()),
    )
    .slice(0, 30);
  return (
    <Modal title="搜索与命令" onClose={onClose}>
      <div className="palette-search">
        <Search size={20} />
        <input
          autoFocus
          placeholder="搜索功能、会话、模型或文件…"
          aria-label="搜索命令"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setIndex(0);
          }}
          onKeyDown={(e) => {
            if (e.key === "ArrowDown") {
              e.preventDefault();
              setIndex((i) => Math.min(i + 1, filtered.length - 1));
            }
            if (e.key === "ArrowUp") {
              e.preventDefault();
              setIndex((i) => Math.max(0, i - 1));
            }
            if (e.key === "Enter" && filtered[index]) {
              onClose();
              filtered[index].run();
            }
          }}
        />
        <kbd>Esc</kbd>
      </div>
      <div className="palette-results">
        {filtered.map((c, i) => (
          <button
            key={c.label}
            className={i === index ? "active" : ""}
            onMouseEnter={() => setIndex(i)}
            onClick={() => {
              onClose();
              c.run();
            }}
          >
            <Command size={16} />
            <span>{c.label}</span>
            {c.shortcut ? <kbd>{c.shortcut}</kbd> : <ArrowUpRight size={14} />}
          </button>
        ))}
        {!filtered.length && (
          <p className="muted">未找到匹配命令，试试“设置”或“课程”。</p>
        )}
      </div>
      <footer className="palette-footer">
        ↑ ↓ 选择 <span>↵ 执行</span>
      </footer>
    </Modal>
  );
}
