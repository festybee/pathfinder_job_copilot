import { useState } from "react";

const STORAGE_PREFIX = "pathfinder-guide-dismissed:";

/**
 * Dismissible right-hand help sidebar. Content is passed as children (JSX),
 * one instance per page via a unique `pageKey`. Once closed, it stays closed
 * on that page (remembered in localStorage) and collapses to a small "?"
 * tab in the same spot so it can be reopened any time.
 */
export default function GuidePanel({ pageKey, title, children }) {
  const storageKey = STORAGE_PREFIX + pageKey;

  const [open, setOpen] = useState(() => {
    try {
      return localStorage.getItem(storageKey) !== "1";
    } catch {
      return true;
    }
  });

  const close = () => {
    setOpen(false);
    try {
      localStorage.setItem(storageKey, "1");
    } catch {
      // localStorage unavailable (private browsing etc.) - just close for this visit
    }
  };

  const reopen = () => {
    setOpen(true);
    try {
      localStorage.removeItem(storageKey);
    } catch {
      // ignore
    }
  };

  if (!open) {
    return (
      <button className="guide-reopen" onClick={reopen} title="Show help" aria-label="Show help">
        ?
      </button>
    );
  }

  return (
    <aside className="guide-panel">
      <div className="guide-panel-header">
        <strong>{title}</strong>
        <button className="guide-panel-close" onClick={close} aria-label="Close guide">
          &times;
        </button>
      </div>
      <div className="guide-panel-body">{children}</div>
    </aside>
  );
}
