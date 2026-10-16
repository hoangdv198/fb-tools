import React from 'react';
import { User, RefreshCw, CheckCircle, AlertTriangle, Database, Trash2, ChevronLeft } from 'lucide-react';

export default function SystemSidebar({
  isOpen,
  onClose,
  profiles,
  selectedProfile,
  setSelectedProfile,
  loginStatus,
  onCheckLogin,
  dbStats,
  onRefreshDbStats,
  onLoadPosts,
  onClearDb
}) {
  return (
    <div style={{
      width: isOpen ? 320 : 0,
      minWidth: isOpen ? 320 : 0,
      transition: 'all 0.25s cubic-bezier(0.4, 0, 0.2, 1)',
      overflow: 'hidden',
      backgroundColor: 'var(--bg-secondary)',
      borderRight: isOpen ? '1px solid var(--border-color)' : 'none',
      display: 'flex',
      flexDirection: 'column',
      zIndex: 40
    }}>
      {isOpen && (
        <div style={{ padding: '16px 14px', height: '100%', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 20 }}>
          {/* Header */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ fontWeight: 700, fontSize: 13, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: 0.5 }}>
              THIẾT LẬP HỆ THỐNG
            </div>
            <button onClick={onClose} style={{ color: 'var(--text-muted)', padding: 4 }}>
              <ChevronLeft size={16} />
            </button>
          </div>

          {/* Profile Chrome */}
          <div style={{ background: 'var(--bg-tertiary)', border: '1px solid var(--border-color)', borderRadius: 8, padding: 12 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8, fontWeight: 600, fontSize: 13 }}>
              <User size={15} color="var(--accent-blue)" />
              <span>Google Chrome Profile</span>
            </div>
            <p style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 10 }}>
              Dùng phiên đăng nhập Facebook sẵn từ máy tính.
            </p>

            <select
              value={selectedProfile}
              onChange={e => setSelectedProfile(e.target.value)}
              style={{
                width: '100%',
                padding: '7px 10px',
                borderRadius: 6,
                backgroundColor: 'var(--bg-primary)',
                color: 'var(--text-primary)',
                border: '1px solid var(--border-color)',
                fontSize: 12,
                marginBottom: 10
              }}
            >
              {profiles.map(p => (
                <option key={p.path} value={p.path}>
                  {p.display} {p.has_facebook ? '🔥 [FB]' : ''}
                </option>
              ))}
            </select>

            <button
              onClick={onCheckLogin}
              disabled={loginStatus === 'checking'}
              style={{
                width: '100%',
                padding: '7px 0',
                borderRadius: 6,
                backgroundColor: 'var(--bg-hover)',
                color: 'var(--text-primary)',
                fontSize: 12,
                fontWeight: 500,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 6,
                border: '1px solid var(--border-color)'
              }}
            >
              <RefreshCw size={13} className={loginStatus === 'checking' ? 'animate-spin' : ''} />
              <span>{loginStatus === 'checking' ? 'Đang kiểm tra...' : 'Kiểm tra đăng nhập'}</span>
            </button>

            {loginStatus === 'logged_in' && (
              <div style={{ marginTop: 8, padding: '6px 10px', borderRadius: 6, background: 'rgba(63, 185, 80, 0.15)', border: '1px solid var(--accent-green)', color: 'var(--accent-green)', fontSize: 11, display: 'flex', alignItems: 'center', gap: 6 }}>
                <CheckCircle size={13} />
                <span>Phiên Facebook hoạt động hợp lệ!</span>
              </div>
            )}
            {loginStatus === 'not_logged_in' && (
              <div style={{ marginTop: 8, padding: '6px 10px', borderRadius: 6, background: 'rgba(248, 81, 73, 0.15)', border: '1px solid var(--accent-red)', color: 'var(--accent-red)', fontSize: 11, display: 'flex', alignItems: 'center', gap: 6 }}>
                <AlertTriangle size={13} />
                <span>Chưa đăng nhập FB hoặc cookie hết hạn.</span>
              </div>
            )}
          </div>

          {/* Database Manager */}
          <div style={{ background: 'var(--bg-tertiary)', border: '1px solid var(--border-color)', borderRadius: 8, padding: 12 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontWeight: 600, fontSize: 13 }}>
                <Database size={15} color="var(--accent-yellow)" />
                <span>Cơ sở dữ liệu SQLite</span>
              </div>
              <button onClick={onRefreshDbStats} title="Làm mới số liệu" style={{ color: 'var(--text-muted)' }}>
                <RefreshCw size={13} />
              </button>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 12 }}>
              <div style={{ background: 'var(--bg-primary)', padding: '8px 10px', borderRadius: 6, border: '1px solid var(--border-subtle)' }}>
                <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>Dung lượng</div>
                <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--text-primary)' }}>{dbStats.size_human}</div>
              </div>
              <div style={{ background: 'var(--bg-primary)', padding: '8px 10px', borderRadius: 6, border: '1px solid var(--border-subtle)' }}>
                <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>Bài đã lưu</div>
                <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--text-primary)' }}>{dbStats.total_posts} bài</div>
              </div>
            </div>

            <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 10, display: 'flex', justifyContent: 'space-between' }}>
              <span>🧠 Đã thẩm định: <b>{dbStats.analyzed_posts}</b></span>
              <span style={{ color: dbStats.scam_posts > 0 ? 'var(--accent-red)' : 'var(--text-secondary)' }}>
                🚨 Scam: <b>{dbStats.scam_posts}</b>
              </span>
            </div>

            <div style={{ display: 'flex', gap: 8 }}>
              <button
                onClick={onLoadPosts}
                style={{
                  flex: 1,
                  padding: '6px 0',
                  borderRadius: 6,
                  background: 'var(--bg-hover)',
                  color: 'var(--text-primary)',
                  fontSize: 11,
                  fontWeight: 500,
                  border: '1px solid var(--border-color)'
                }}
              >
                Tải bảng
              </button>
              <button
                onClick={onClearDb}
                style={{
                  padding: '6px 10px',
                  borderRadius: 6,
                  background: 'rgba(248, 81, 73, 0.1)',
                  color: 'var(--accent-red)',
                  fontSize: 11,
                  border: '1px solid rgba(248, 81, 73, 0.3)'
                }}
                title="Xóa toàn bộ database"
              >
                <Trash2 size={13} />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
