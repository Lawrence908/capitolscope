import React, { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import apiClient from '../../services/api';
import type { SocialPost, SocialPostStatus, SocialStatus } from '../../types/social';
import { PageHeader, Spinner, Tabs } from '../../components/ui';

const X_LIMIT = 280;
const TABS: { id: SocialPostStatus; label: string }[] = [
  { id: 'draft', label: 'Drafts' },
  { id: 'approved', label: 'Approved' },
  { id: 'posted', label: 'Posted' },
  { id: 'failed', label: 'Failed' },
  { id: 'rejected', label: 'Rejected' },
  { id: 'skipped', label: 'Skipped' },
];

// X counts every URL as 23 characters.
const xLength = (text: string): number => text.replace(/https?:\/\/\S+/g, 'x'.repeat(23)).length;

const fmtTime = (iso: string | null): string =>
  iso ? new Date(iso).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' }) : '';

const errorMessage = (e: unknown): string => {
  const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
  return detail || (e instanceof Error ? e.message : 'Request failed');
};

const PostCard: React.FC<{ post: SocialPost; onChange: () => void }> = ({ post, onChange }) => {
  const [text, setText] = useState(post.text);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const editable = ['draft', 'approved', 'failed'].includes(post.status);
  const dirty = text !== post.text;
  const length = xLength(text);

  const run = async (fn: () => Promise<unknown>) => {
    setBusy(true);
    setError(null);
    try {
      await fn();
      onChange();
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <article className="grid gap-5 border-b border-line py-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,420px)]">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2 font-ui text-xs font-semibold uppercase tracking-[0.08em] text-content-faint">
          <span className="border-2 border-content px-1.5 py-px font-display text-[13px] font-extrabold text-content">
            {post.kind}
          </span>
          <span>Score {post.score}</span>
          <span>{fmtTime(post.created_at)}</span>
          {post.trade_ids.length > 0 && <span>{post.trade_ids.length} trade{post.trade_ids.length === 1 ? '' : 's'}</span>}
        </div>
        {post.reasons.length > 0 && (
          <p className="mt-2 font-ui text-sm text-content-muted">{post.reasons.join(' · ')}</p>
        )}

        {editable ? (
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={7}
            className="input-field mt-3 font-ui text-[15px] leading-relaxed"
          />
        ) : (
          <pre className="mt-3 whitespace-pre-wrap border-l-4 border-content bg-surface-inset p-4 font-ui text-[15px] leading-relaxed text-content">
            {post.text}
          </pre>
        )}
        <div className={`mt-1 font-ui text-xs ${length > X_LIMIT ? 'font-bold text-accent' : 'text-content-faint'}`}>
          {length} / {X_LIMIT}
        </div>
        {post.thread.length > 0 && (
          <div className="mt-3 space-y-2">
            <div className="font-ui text-[11px] font-semibold uppercase tracking-[0.08em] text-content-faint">
              Thread replies ({post.thread.length})
            </div>
            {post.thread.map((reply, i) => (
              <pre key={i} className="whitespace-pre-wrap border-l-2 border-line pl-3 font-ui text-sm leading-relaxed text-content-muted">
                {reply}
              </pre>
            ))}
          </div>
        )}

        {post.error && (
          <p className="mt-2 border-l-4 border-accent bg-surface-inset px-3 py-2 font-ui text-sm text-content">{post.error}</p>
        )}
        {error && (
          <p className="mt-2 border-l-4 border-accent bg-surface-inset px-3 py-2 font-ui text-sm text-content">{error}</p>
        )}

        <div className="mt-4 flex flex-wrap items-center gap-3">
          {editable && dirty && (
            <button
              type="button"
              className="btn-secondary"
              disabled={busy || length > X_LIMIT}
              onClick={() => run(() => apiClient.editSocialPost(post.id, text))}
            >
              Save edit
            </button>
          )}
          {editable && post.status !== 'approved' && (
            <button
              type="button"
              className="btn-primary"
              disabled={busy || dirty}
              title={dirty ? 'Save the edit first' : undefined}
              onClick={() => run(() => apiClient.approveSocialPost(post.id))}
            >
              Approve
            </button>
          )}
          {editable && (
            <button
              type="button"
              className="btn-outline"
              disabled={busy}
              onClick={() => run(() => apiClient.rejectSocialPost(post.id))}
            >
              Reject
            </button>
          )}
          {post.link_url && (
            <a href={post.link_url} target="_blank" rel="noreferrer" className="font-ui text-sm font-semibold text-content underline hover:text-accent">
              Open link
            </a>
          )}
          {post.external_url && (
            <a href={post.external_url} target="_blank" rel="noreferrer" className="font-ui text-sm font-semibold text-accent underline">
              View on X
            </a>
          )}
          {post.posted_at && <span className="font-ui text-xs text-content-faint">Posted {fmtTime(post.posted_at)}</span>}
        </div>
      </div>

      {post.image_url && (
        <div>
          <img
            src={post.image_url}
            alt="Card attached to the post"
            loading="lazy"
            className="w-full border-2 border-content bg-surface-inset"
          />
        </div>
      )}
    </article>
  );
};

/** Admin-only review queue for the public X account. */
const SocialQueuePage: React.FC = () => {
  const [tab, setTab] = useState<SocialPostStatus>('draft');
  const [posts, setPosts] = useState<SocialPost[] | null>(null);
  const [status, setStatus] = useState<SocialStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [s, p] = await Promise.all([apiClient.getSocialStatus(), apiClient.getSocialPosts(tab)]);
      setStatus(s);
      setPosts(p);
    } catch (e) {
      setError(errorMessage(e));
      setPosts([]);
    }
  }, [tab]);

  useEffect(() => {
    setPosts(null);
    void load();
  }, [load]);

  const draftNow = async (kind: 'trades' | 'weekly' = 'trades') => {
    try {
      await apiClient.draftSocialPostsNow(kind);
      setNotice('Drafting run queued. Refresh in a minute.');
    } catch (e) {
      setError(errorMessage(e));
    }
  };

  return (
    <div>
      <PageHeader
        eyebrow="Admin"
        title="X post queue"
        subtitle={
          status
            ? `Mode: ${status.mode === 'auto' ? 'auto-post' : 'review (posts need approval)'}. Posting ${
                status.x_enabled ? 'enabled' : 'disabled'
              }. ${status.posted_24h} of ${status.daily_cap} posts in the last 24 hours. Window ${status.window_utc} UTC.`
            : 'Drafts from newly disclosed trades. Nothing posts until it is approved.'
        }
        actions={
          <div className="flex flex-wrap gap-2">
            <button type="button" className="btn-secondary" onClick={() => draftNow('trades')}>
              Draft new trades
            </button>
            <button type="button" className="btn-outline" onClick={() => draftNow('weekly')}>
              Draft weekly recap
            </button>
          </div>
        }
      />

      <Tabs
        items={TABS.map((t) => ({
          id: t.id,
          label: status ? `${t.label} ${status.counts[t.id] ?? 0}` : t.label,
        }))}
        active={tab}
        onChange={setTab}
        className="mb-2 border-b border-line"
      />

      {notice && <p className="my-3 border-l-4 border-content bg-surface-inset px-3 py-2 font-ui text-sm text-content">{notice}</p>}
      {error && (
        <p className="my-3 border-l-4 border-accent bg-surface-inset px-3 py-2 font-ui text-sm text-content">
          {error.includes('403') || error.toLowerCase().includes('permission') ? 'This page is for administrators.' : error}
        </p>
      )}

      {posts == null ? (
        <Spinner label="Loading posts" />
      ) : posts.length === 0 ? (
        <p className="py-12 text-center font-ui text-content-faint">
          Nothing here. New drafts appear after each sync. <Link to="/" className="underline">Back to the site</Link>
        </p>
      ) : (
        posts.map((p) => <PostCard key={`${p.id}-${p.status}-${p.text.length}`} post={p} onChange={load} />)
      )}
    </div>
  );
};

export default SocialQueuePage;
