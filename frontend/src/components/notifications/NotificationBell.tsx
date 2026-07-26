import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { BellIcon } from '@heroicons/react/24/outline';
import { apiClient } from '../../services/api';
import type { InboxNotification } from '../../types';

const timeAgo = (iso?: string | null): string => {
  if (!iso) return '';
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 1) return 'just now';
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
};

const NotificationBell: React.FC = () => {
  const [open, setOpen] = useState(false);
  const [unread, setUnread] = useState(0);
  const [items, setItems] = useState<InboxNotification[]>([]);
  const [loading, setLoading] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const refreshCount = useCallback(async () => {
    try {
      setUnread(await apiClient.getInboxUnreadCount());
    } catch {
      /* silent */
    }
  }, []);

  // Poll the unread count.
  useEffect(() => {
    void refreshCount();
    const t = setInterval(refreshCount, 60000);
    return () => clearInterval(t);
  }, [refreshCount]);

  // Close on outside click.
  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', onClick);
    return () => document.removeEventListener('mousedown', onClick);
  }, []);

  const openPanel = async () => {
    const next = !open;
    setOpen(next);
    if (next) {
      setLoading(true);
      try {
        const inbox = await apiClient.getInbox({ limit: 8 });
        setItems(inbox.items);
        setUnread(inbox.unread);
      } catch {
        setItems([]);
      } finally {
        setLoading(false);
      }
    }
  };

  const markOne = async (n: InboxNotification) => {
    if (n.is_read) return;
    try {
      await apiClient.markInboxRead(n.id);
      setItems((prev) => prev.map((x) => (x.id === n.id ? { ...x, is_read: true } : x)));
      setUnread((u) => Math.max(0, u - 1));
    } catch {
      /* silent */
    }
  };

  const markAll = async () => {
    try {
      await apiClient.markInboxAllRead();
      setItems((prev) => prev.map((x) => ({ ...x, is_read: true })));
      setUnread(0);
    } catch {
      /* silent */
    }
  };

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={openPanel}
        className="relative rounded-lg p-2 text-content-muted transition-colors hover:bg-surface-inset hover:text-content"
        aria-label="Notifications"
      >
        <BellIcon className="h-5 w-5" />
        {unread > 0 && (
          <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-sev-flag px-1 font-data text-[10px] font-medium leading-none text-white">
            {unread > 9 ? '9+' : unread}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 z-50 mt-2 w-80 overflow-hidden rounded-md border border-line bg-surface-raised shadow-xl">
          <div className="flex items-center justify-between border-b border-line px-4 py-2.5">
            <span className="font-data text-[11px] uppercase tracking-[0.14em] text-content-faint">
              Notifications
            </span>
            {unread > 0 && (
              <button
                type="button"
                onClick={markAll}
                className="font-data text-[11px] uppercase tracking-[0.1em] text-accent hover:text-accent-strong"
              >
                Mark all read
              </button>
            )}
          </div>

          <div className="max-h-96 overflow-y-auto">
            {loading ? (
              <p className="px-4 py-8 text-center font-ui text-sm text-content-faint">Loading…</p>
            ) : items.length === 0 ? (
              <p className="px-4 py-8 text-center font-ui text-sm text-content-faint">
                No notifications yet.
              </p>
            ) : (
              <ul className="divide-y divide-line">
                {items.map((n) => (
                  <li key={n.id}>
                    <button
                      type="button"
                      onClick={() => markOne(n)}
                      className={`flex w-full gap-3 px-4 py-3 text-left transition-colors hover:bg-surface-inset ${
                        n.is_read ? '' : 'bg-accent/5'
                      }`}
                    >
                      <span
                        className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${
                          n.is_read ? 'bg-transparent' : 'bg-accent'
                        }`}
                      />
                      <span className="min-w-0 flex-1">
                        <span className="block truncate font-ui text-sm font-medium text-content">
                          {n.title}
                        </span>
                        <span className="block truncate font-ui text-xs text-content-faint">
                          {n.message}
                        </span>
                        <span className="mt-0.5 block font-data text-[10px] uppercase tracking-[0.1em] text-content-faint">
                          {timeAgo(n.created_at)}
                        </span>
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <Link
            to="/alerts"
            onClick={() => setOpen(false)}
            className="block border-t border-line px-4 py-2.5 text-center font-data text-[11px] uppercase tracking-[0.12em] text-accent hover:bg-surface-inset"
          >
            View all alerts
          </Link>
        </div>
      )}
    </div>
  );
};

export default NotificationBell;
