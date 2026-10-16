import React from 'react';
import { ExternalLink, Clock } from 'lucide-react';

export default function PostDetailModal({ post, onClose }) {
  if (!post) return null;

  const exactTime = post.exact_posted_time || post.posted_time || 'Không rõ';
  const rawTime = post.posted_time || '';
  const hasLink = Boolean(
    post.post_url &&
    post.post_url.startsWith('http') &&
    post.post_url !== post.group_url &&
    (post.post_url.includes('/posts/') || post.post_url.includes('/permalink/') || post.post_url.includes('story_fbid'))
  );

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      background: 'rgba(0,0,0,0.7)',
      zIndex: 1000,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: 20
    }}>
      <div style={{
        background: 'var(--bg-secondary)',
        border: '1px solid var(--border-color)',
        borderRadius: 8,
        width: 640,
        maxWidth: '100%',
        maxHeight: '85vh',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden'
      }}>
        {/* Header */}
        <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ fontWeight: 700, fontSize: 14 }}>{post.ai_title || 'Chi tiết bài viết'}</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            {hasLink && (
              <a
                href={post.post_url}
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 4,
                  padding: '4px 10px',
                  borderRadius: 6,
                  background: 'var(--accent-blue)',
                  color: '#fff',
                  fontSize: 11,
                  fontWeight: 600,
                  textDecoration: 'none'
                }}
              >
                <ExternalLink size={12} />
                <span>Mở trên Facebook</span>
              </a>
            )}
            <button onClick={onClose} style={{ color: 'var(--text-muted)', fontSize: 16, cursor: 'pointer' }}>✕</button>
          </div>
        </div>

        {/* Content */}
        <div style={{ padding: 16, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 10, fontSize: 12 }}>
          <div><b>Nhóm:</b> {post.group_name}</div>
          <div><b>Người đăng:</b> {post.author_name}</div>
          
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <b>⏰ Thời gian đăng:</b>
            <span style={{ color: 'var(--accent-blue)', fontWeight: 600 }}>{exactTime}</span>
            {rawTime && rawTime !== exactTime && (
              <span style={{ color: 'var(--text-muted)', fontSize: 11 }}>({rawTime})</span>
            )}
          </div>

          <div>
            <b>🔗 Link bài viết:</b>{' '}
            {hasLink ? (
              <a
                href={post.post_url}
                target="_blank"
                rel="noopener noreferrer"
                style={{ color: 'var(--accent-blue)', textDecoration: 'underline', wordBreak: 'break-all' }}
              >
                {post.post_url}
              </a>
            ) : (
              <span style={{ color: 'var(--text-muted)' }}>Chưa có link permalink</span>
            )}
          </div>

          <div><b>Mức lương (AI):</b> {post.ai_salary || 'Thoả thuận'}</div>
          <div><b>Độ uy tín (AI):</b> {post.ai_trust_score}/100</div>
          <div><b>Cảnh báo lừa đảo:</b> {post.ai_scam_reason || '🟢 Không phát hiện'}</div>

          <div style={{ borderTop: '1px solid var(--border-color)', paddingTop: 10, marginTop: 4 }}>
            <b>Nội dung bài viết:</b>
            <pre style={{ marginTop: 6, whiteSpace: 'pre-wrap', fontFamily: 'inherit', background: 'var(--bg-primary)', padding: 10, borderRadius: 6, lineHeight: 1.5, maxHeight: 300, overflowY: 'auto' }}>
              {post.content}
            </pre>
          </div>
        </div>
      </div>
    </div>
  );
}
