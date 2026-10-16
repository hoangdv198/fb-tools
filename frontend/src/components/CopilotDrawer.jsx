import React from 'react';
import { Bot, ChevronRight, Sparkles, AlertTriangle, Trash2, RefreshCw, Send } from 'lucide-react';

export default function CopilotDrawer({
  isOpen,
  onClose,
  totalPosts,
  analyzedPosts,
  scamPosts,
  filterScamOnly,
  onToggleFilterScam,
  chatMessages,
  onClearChat,
  chatInput,
  setChatInput,
  chatLoading,
  onSendMessage,
  onBatchAnalyze,
  chatScrollRef
}) {
  return (
    <div style={{
      width: isOpen ? 380 : 0,
      minWidth: isOpen ? 380 : 0,
      transition: 'all 0.25s cubic-bezier(0.4, 0, 0.2, 1)',
      overflow: 'hidden',
      backgroundColor: 'var(--bg-secondary)',
      borderLeft: isOpen ? '1px solid var(--border-color)' : 'none',
      display: 'flex',
      flexDirection: 'column',
      height: '100vh',
      zIndex: 50
    }}>
      {isOpen && (
        <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
          {/* Header */}
          <div style={{
            height: 48,
            padding: '0 14px',
            borderBottom: '1px solid var(--border-color)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            backgroundColor: 'var(--bg-secondary)'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Bot size={18} color="var(--accent-blue)" />
              <span style={{ fontWeight: 700, fontSize: 13, letterSpacing: 0.5 }}>AGENT COPILOT</span>
              <span style={{
                padding: '2px 8px',
                borderRadius: 999,
                background: 'rgba(63, 185, 80, 0.15)',
                border: '1px solid rgba(63, 185, 80, 0.3)',
                color: 'var(--accent-green)',
                fontSize: 10,
                fontWeight: 600,
                display: 'flex',
                alignItems: 'center',
                gap: 4
              }}>
                <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--accent-green)' }} />
                Online (20128)
              </span>
            </div>
            <button onClick={onClose} title="Thu gọn panel" style={{ color: 'var(--text-muted)' }}>
              <ChevronRight size={16} />
            </button>
          </div>

          {/* Quick Stats Chips */}
          <div style={{ padding: '8px 12px', background: 'var(--bg-tertiary)', borderBottom: '1px solid var(--border-color)', display: 'flex', gap: 6, alignItems: 'center' }}>
            <span style={{ background: 'rgba(255,255,255,0.06)', border: '1px solid var(--border-subtle)', padding: '2px 8px', borderRadius: 6, fontSize: 11, color: 'var(--text-secondary)' }}>
              📄 <b>{totalPosts}</b> bài
            </span>
            <span style={{ background: 'rgba(255,255,255,0.06)', border: '1px solid var(--border-subtle)', padding: '2px 8px', borderRadius: 6, fontSize: 11, color: 'var(--text-secondary)' }}>
              🧠 <b>{analyzedPosts}</b> thẩm định
            </span>
            <span style={{ background: 'rgba(255,255,255,0.06)', border: '1px solid var(--border-subtle)', padding: '2px 8px', borderRadius: 6, fontSize: 11, color: scamPosts > 0 ? 'var(--accent-red)' : 'var(--text-secondary)' }}>
              🚨 <b>{scamPosts}</b> rủi ro
            </span>
          </div>

          {/* Actions Toolbar */}
          <div style={{ padding: '10px 12px', borderBottom: '1px solid var(--border-color)', display: 'flex', flexDirection: 'column', gap: 6 }}>
            <button
              onClick={onBatchAnalyze}
              disabled={chatLoading}
              style={{
                width: '100%',
                padding: '7px 0',
                borderRadius: 6,
                background: 'var(--accent-red)',
                color: '#fff',
                fontSize: 12,
                fontWeight: 600,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 6
              }}
            >
              <Sparkles size={13} />
              <span>Thẩm định toàn bộ bài viết</span>
            </button>

            <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr', gap: 6 }}>
              <button
                onClick={onToggleFilterScam}
                style={{
                  padding: '6px 0',
                  borderRadius: 6,
                  background: filterScamOnly ? 'rgba(248, 81, 73, 0.2)' : 'var(--bg-tertiary)',
                  border: filterScamOnly ? '1px solid var(--accent-red)' : '1px solid var(--border-color)',
                  color: filterScamOnly ? 'var(--accent-red)' : 'var(--text-primary)',
                  fontSize: 11,
                  fontWeight: 500
                }}
              >
                {filterScamOnly ? '✅ Đang lọc Scam' : '🚨 Lọc bài Scam'}
              </button>
              <button
                onClick={onClearChat}
                style={{
                  padding: '6px 0',
                  borderRadius: 6,
                  background: 'var(--bg-tertiary)',
                  border: '1px solid var(--border-color)',
                  color: 'var(--text-secondary)',
                  fontSize: 11,
                  fontWeight: 500,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: 4
                }}
              >
                <Trash2 size={12} />
                <span>Xóa chat</span>
              </button>
            </div>
          </div>

          {/* Messages Scroll Area */}
          <div
            ref={chatScrollRef}
            style={{
              flex: 1,
              overflowY: 'auto',
              padding: '12px 14px',
              display: 'flex',
              flexDirection: 'column',
              gap: 12
            }}
          >
            {chatMessages.map((msg, idx) => (
              <div
                key={idx}
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
                  maxWidth: '92%'
                }}
              >
                <div style={{
                  fontSize: 10,
                  color: 'var(--text-muted)',
                  marginBottom: 3,
                  textAlign: msg.role === 'user' ? 'right' : 'left'
                }}>
                  {msg.role === 'user' ? '🧑‍💻 Bạn' : '🤖 AI Agent'}
                </div>
                <div
                  style={{
                    padding: '10px 12px',
                    borderRadius: 8,
                    fontSize: 12,
                    lineHeight: 1.5,
                    whiteSpace: 'pre-wrap',
                    background: msg.role === 'user' ? 'var(--bg-hover)' : 'var(--bg-tertiary)',
                    border: '1px solid var(--border-color)',
                    color: 'var(--text-primary)'
                  }}
                >
                  {msg.content}
                </div>

                {msg.action && msg.action.type === 'FILTER_POSTS' && (
                  <div style={{
                    marginTop: 6,
                    padding: '6px 10px',
                    borderRadius: 6,
                    background: 'rgba(31, 111, 235, 0.12)',
                    border: '1px solid rgba(31, 111, 235, 0.35)',
                    color: 'var(--accent-blue)',
                    fontSize: 11,
                    display: 'flex',
                    alignItems: 'center',
                    gap: 6
                  }}>
                    <span>🎯 Đã lọc dữ liệu web: <b>{msg.action.filter_name}</b> ({msg.action.count || msg.action.post_ids?.length || 0} bài)</span>
                  </div>
                )}

                {msg.action && msg.action.type === 'RESET_FILTER' && (
                  <div style={{
                    marginTop: 6,
                    padding: '6px 10px',
                    borderRadius: 6,
                    background: 'rgba(63, 185, 80, 0.12)',
                    border: '1px solid rgba(63, 185, 80, 0.35)',
                    color: 'var(--accent-green)',
                    fontSize: 11,
                    display: 'flex',
                    alignItems: 'center',
                    gap: 6
                  }}>
                    <span>🔄 Đã khôi phục hiển thị toàn bộ bài viết</span>
                  </div>
                )}
              </div>
            ))}

            {chatLoading && (
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--text-muted)', fontSize: 11 }}>
                <RefreshCw size={12} className="animate-spin" />
                <span>Agent đang truy vấn database & xử lý...</span>
              </div>
            )}
          </div>

          {/* Quick Prompt Suggestions */}
          <div style={{
            padding: '6px 12px',
            borderTop: '1px solid var(--border-subtle)',
            backgroundColor: 'var(--bg-tertiary)',
            display: 'flex',
            flexWrap: 'wrap',
            gap: 4
          }}>
            <button
              onClick={() => onSendMessage('list cho tôi những tin gia sư lớp 6 trở xuống')}
              disabled={chatLoading}
              style={{
                fontSize: 10.5,
                padding: '3px 7px',
                borderRadius: 4,
                background: 'rgba(255,255,255,0.05)',
                border: '1px solid var(--border-subtle)',
                color: 'var(--text-secondary)',
                cursor: 'pointer'
              }}
            >
              🎯 Lớp 6 trở xuống
            </button>
            <button
              onClick={() => onSendMessage('tìm các bài dạy môn toán')}
              disabled={chatLoading}
              style={{
                fontSize: 10.5,
                padding: '3px 7px',
                borderRadius: 4,
                background: 'rgba(255,255,255,0.05)',
                border: '1px solid var(--border-subtle)',
                color: 'var(--text-secondary)',
                cursor: 'pointer'
              }}
            >
              📐 Môn Toán
            </button>
            <button
              onClick={() => onSendMessage('lọc các bài nghi vấn lừa đảo')}
              disabled={chatLoading}
              style={{
                fontSize: 10.5,
                padding: '3px 7px',
                borderRadius: 4,
                background: 'rgba(255,255,255,0.05)',
                border: '1px solid var(--border-subtle)',
                color: 'var(--text-secondary)',
                cursor: 'pointer'
              }}
            >
              🚨 Lừa đảo / cọc
            </button>
            <button
              onClick={() => onSendMessage('bỏ lọc hiển thị lại tất cả bài')}
              disabled={chatLoading}
              style={{
                fontSize: 10.5,
                padding: '3px 7px',
                borderRadius: 4,
                background: 'rgba(255,255,255,0.05)',
                border: '1px solid var(--border-subtle)',
                color: 'var(--text-secondary)',
                cursor: 'pointer'
              }}
            >
              🔄 Bỏ lọc
            </button>
          </div>

          {/* Pinned Bottom Chat Input */}
          <div style={{
            padding: '10px 12px',
            borderTop: '1px solid var(--border-color)',
            backgroundColor: 'var(--bg-secondary)',
            display: 'flex',
            gap: 8
          }}>
            <input
              type="text"
              placeholder="Nhập câu hỏi hoặc yêu cầu cho AI Agent..."
              value={chatInput}
              onChange={e => setChatInput(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') onSendMessage(); }}
              disabled={chatLoading}
              style={{
                flex: 1,
                padding: '8px 12px',
                borderRadius: 6,
                backgroundColor: 'var(--bg-primary)',
                border: '1px solid var(--border-color)',
                color: 'var(--text-primary)',
                fontSize: 12
              }}
            />
            <button
              onClick={() => onSendMessage()}
              disabled={chatLoading || !chatInput.trim()}
              style={{
                padding: '0 12px',
                borderRadius: 6,
                background: 'var(--accent-blue)',
                color: '#fff',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}
            >
              <Send size={14} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
