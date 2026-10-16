import React from 'react';
import { Bot, Play } from 'lucide-react';

export default function BotWorkspace({
  botTargetMode,
  setBotTargetMode,
  botTargetUrl,
  setBotTargetUrl,
  botScrolls,
  setBotScrolls,
  botAutoLike,
  setBotAutoLike,
  botAutoComment,
  setBotAutoComment,
  botAutoFriend,
  setBotAutoFriend,
  botAIPersona,
  setBotAIPersona,
  botHeadless,
  setBotHeadless,
  botRunning,
  onStartBot,
  botLogs
}) {
  return (
    <div style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', borderRadius: 8, padding: 18 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
        <Bot size={22} color="var(--accent-green)" />
        <h3 style={{ fontSize: 16, fontWeight: 700 }}>Tự Động Lướt Feed, Thả Like, Bình Luận & Kết Bạn</h3>
      </div>
      <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 20 }}>
        Mô phỏng hành vi người dùng thật với thời gian chờ ngẫu nhiên để bảo vệ tài khoản tối đa.
      </p>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
        <div>
          <label style={{ fontSize: 12, fontWeight: 600, display: 'block', marginBottom: 6 }}>Khu vực tương tác:</label>
          <select
            value={botTargetMode}
            onChange={e => setBotTargetMode(e.target.value)}
            style={{ width: '100%', padding: '7px 10px', borderRadius: 6, background: 'var(--bg-primary)', color: 'var(--text-primary)', border: '1px solid var(--border-color)', fontSize: 12, marginBottom: 12 }}
          >
            <option value="Newfeed">Bảng tin trang chủ (Newfeed)</option>
            <option value="Group">Nhóm Facebook cụ thể</option>
          </select>

          {botTargetMode === 'Group' && (
            <>
              <label style={{ fontSize: 12, fontWeight: 600, display: 'block', marginBottom: 6 }}>Link Nhóm Facebook:</label>
              <input
                type="text"
                value={botTargetUrl}
                onChange={e => setBotTargetUrl(e.target.value)}
                style={{ width: '100%', padding: '7px 10px', borderRadius: 6, background: 'var(--bg-primary)', color: 'var(--text-primary)', border: '1px solid var(--border-color)', fontSize: 12, marginBottom: 12 }}
              />
            </>
          )}

          <label style={{ fontSize: 12, fontWeight: 600, display: 'block', marginBottom: 6 }}>Số lượt cuộn trang (Scrolls):</label>
          <input
            type="number"
            value={botScrolls}
            onChange={e => setBotScrolls(e.target.value)}
            style={{ width: '100%', padding: '7px 10px', borderRadius: 6, background: 'var(--bg-primary)', color: 'var(--text-primary)', border: '1px solid var(--border-color)', fontSize: 12, marginBottom: 16 }}
          />

          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, cursor: 'pointer' }}>
              <input type="checkbox" checked={botAutoLike} onChange={e => setBotAutoLike(e.target.checked)} />
              <span>👍 Tự động thả cảm xúc (Like)</span>
            </label>
            <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, cursor: 'pointer' }}>
              <input type="checkbox" checked={botAutoComment} onChange={e => setBotAutoComment(e.target.checked)} />
              <span>💬 Tự động bình luận (Comment thông minh)</span>
            </label>
            <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, cursor: 'pointer' }}>
              <input type="checkbox" checked={botAutoFriend} onChange={e => setBotAutoFriend(e.target.checked)} />
              <span>🤝 Tự động gửi lời mời kết bạn</span>
            </label>
          </div>
        </div>

        <div>
          <label style={{ fontSize: 12, fontWeight: 600, display: 'block', marginBottom: 6 }}>Phong cách AI Comment (Persona):</label>
          <select
            value={botAIPersona}
            onChange={e => setBotAIPersona(e.target.value)}
            style={{ width: '100%', padding: '7px 10px', borderRadius: 6, background: 'var(--bg-primary)', color: 'var(--text-primary)', border: '1px solid var(--border-color)', fontSize: 12, marginBottom: 12 }}
          >
            <option value="ứng viên xin việc chuyên nghiệp">Ứng viên xin việc chuyên nghiệp</option>
            <option value="người tìm việc thân thiện và nhiệt tình">Người tìm việc thân thiện & nhiệt tình</option>
            <option value="đồng nghiệp trao đổi chuyên môn">Đồng nghiệp trao đổi chuyên môn</option>
          </select>

          <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, cursor: 'pointer', marginBottom: 16 }}>
            <input type="checkbox" checked={botHeadless} onChange={e => setBotHeadless(e.target.checked)} />
            <span>Chạy ẩn trình duyệt (Headless)</span>
          </label>

          <button
            onClick={onStartBot}
            disabled={botRunning}
            style={{
              width: '100%',
              padding: '10px 14px',
              borderRadius: 6,
              backgroundColor: botRunning ? 'var(--bg-hover)' : 'var(--accent-green)',
              color: '#fff',
              fontWeight: 600,
              fontSize: 13,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 8
            }}
          >
            <Play size={14} className={botRunning ? 'animate-spin' : ''} />
            <span>{botRunning ? 'Bot đang chạy...' : '🚀 Bắt đầu tương tác tự động'}</span>
          </button>

          {/* Terminal Log */}
          {botLogs.length > 0 && (
            <div style={{ marginTop: 14, background: '#05070a', border: '1px solid var(--border-color)', borderRadius: 6, padding: '8px 12px', maxHeight: 130, overflowY: 'auto', fontSize: 11, fontFamily: 'monospace', color: '#58a6ff' }}>
              {botLogs.slice(-8).map((log, i) => (
                <div key={i}>{log}</div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
