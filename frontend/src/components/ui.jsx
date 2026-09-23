import React, { useEffect, useRef } from "react";
import { X, CheckCircle2, AlertCircle, Loader2 } from "lucide-react";
export function Button({
  icon: Icon,
  children,
  label,
  className = "",
  ...props
}) {
  return (
    <button
      title={label || (typeof children === "string" ? children : undefined)}
      aria-label={label}
      className={`button ${!children ? "icon-button" : ""} ${className}`}
      {...props}
    >
      {Icon && <Icon size={17} />} {children}
    </button>
  );
}
export function Badge({ children, status = "" }) {
  return (
    <span className={`badge ${status}`}>
      <span className="status-dot" />
      {children}
    </span>
  );
}
export function Empty({ icon: Icon, title, children, action }) {
  return (
    <div className="empty">
      <div className="empty-icon">{Icon && <Icon size={27} />}</div>
      <h2>{title}</h2>
      <p>{children}</p>
      {action}
    </div>
  );
}
export function Skeleton() {
  return (
    <div className="skeleton-list" aria-label="正在加载" role="status">
      {[1, 2, 3, 4].map((x) => (
        <div className="skeleton" key={x} />
      ))}
    </div>
  );
}
export function Modal({ title, children, onClose, wide = false }) {
  const ref = useRef();
  useEffect(() => {
    const previous = document.activeElement;
    ref.current.showModal();
    const d = ref.current;
    return () => {
      d.close();
      previous?.focus?.();
    };
  }, []);
  return (
    <dialog
      className={`dialog ${wide ? "wide" : ""}`}
      ref={ref}
      onCancel={(e) => {
        e.preventDefault();
        onClose();
      }}
      onClick={(e) => {
        if (e.target === ref.current) onClose();
      }}
    >
      <header>
        <h2>{title}</h2>
        <Button icon={X} label="关闭" onClick={onClose} />
      </header>
      {children}
    </dialog>
  );
}
export function Toasts({ items, dismiss }) {
  return (
    <div className="toasts" aria-live="polite">
      {items.map((t) => (
        <div key={t.id} className={`toast ${t.error ? "error" : ""}`}>
          {t.error ? <AlertCircle size={18} /> : <CheckCircle2 size={18} />}
          <span>{t.text}</span>
          <Button icon={X} label="关闭通知" onClick={() => dismiss(t.id)} />
        </div>
      ))}
    </div>
  );
}
export function Toggle({ label, description, checked, onChange }) {
  return (
    <label className="setting-row">
      <span>
        <strong>{label}</strong>
        {description && <small>{description}</small>}
      </span>
      <input
        className="toggle"
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
      />
    </label>
  );
}
export function Busy({ children }) {
  return (
    <span className="busy">
      <Loader2 size={15} className="spin" />
      {children}
    </span>
  );
}
