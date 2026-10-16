import React, { useState, useEffect, useRef } from 'react';
import {
  UserPlus,
  Play,
  Square,
  ShieldCheck,
  Clock,
  ExternalLink,
  Trash2,
  RefreshCw,
  Search,
  Download,
  AlertTriangle,
  Users,
  CheckCircle2
} from 'lucide-react';
import { api } from '../api';

export default function FriendBotWorkspace({
  selectedProfile,
  friendGroupUrl,
  setFriendGroupUrl,
  friendMaxRequests,
  setFriendMaxRequests,
  friendDelayMin,
  setFriendDelayMin,
  friendDelayMax,
  setFriendDelayMax,
  friendFilterMode,
  setFriendFilterMode,
  friendSkipExisting,
  setFriendSkipExisting,
  friendHeadless,
  setFriendHeadless,
  friendBotRunning,
  onStartFriendBot,
  onStopFriendBot,
  friendBotLogs,
  friendBotStats
}) {
  const [history, setHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historySearch, setHistorySearch] = useState('');
  const logContainerRef = useRef(null);

  // Tự động cuộn xuống đáy terminal log khi có log mới
  useEffect(() => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [friendBotLogs]);

  // Tải danh sách lịch sử kết bạn
  const loadHistory = async () => {
    setHistoryLoading(true);
    try {
      const data = await api.getFriendHistory(300);
      setHistory(data.history || []);
    } catch (err) {
      console.error('Lỗi khi tải lịch sử kết bạn:', err);
    } finally {
      setHistoryLoading(false);
    }
  };

  useEffect(() => {
    loadHistory();
  }, []);

  // Tự động cập nhật bảng lịch sử mỗi khi có người mới được kết bạn thành công
  const sentCount = friendBotStats?.sent ?? 0;
  const skippedCount = friendBotStats?.skipped ?? 0;
  const targetCount = friendBotStats?.total_target ?? friendMaxRequests;

  useEffect(() => {
    if (sentCount > 0) {
      loadHistory();
    }
  }, [sentCount]);

  // Xóa lịch sử
  const handleClearHistory = async () => {
    if (window.confirm('Bạn có chắc chắn muốn xóa toàn bộ lịch sử gửi lời mời kết bạn trong cơ sở dữ liệu?')) {
      try {
        await api.clearFriendHistory();
        setHistory([]);
      } catch (err) {
        alert('Lỗi khi xóa lịch sử: ' + err.message);
      }
    }
  };

  // Xuất CSV
  const handleExportCSV = () => {
    if (!history.length) return;
    const headers = ['ID', 'Thời gian', 'Tên thành viên', 'Profile URL', 'Nhóm', 'Trạng thái'];
    const rows = history.map(item => [
      item.id,
      `"${item.created_at || ''}"`,
      `"${(item.user_name || '').replace(/"/g, '""')}"`,
      `"${item.profile_url || ''}"`,
      `"${item.group_url || ''}"`,
      item.status
    ]);
    const csvContent = 'data:text/csv;charset=utf-8,\uFEFF' + [headers.join(','), ...rows.map(e => e.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `fb_sent_friend_requests_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const filteredHistory = history.filter(item => {
    if (!historySearch.trim()) return true;
    const q = historySearch.toLowerCase();
    return (
      (item.user_name && item.user_name.toLowerCase().includes(q)) ||
      (item.profile_url && item.profile_url.toLowerCase().includes(q)) ||
      (item.group_url && item.group_url.toLowerCase().includes(q))
    );
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* Header Banner */}
      <div style={{
        background: 'linear-gradient(135deg, rgba(245, 158, 11, 0.12) 0%, rgba(30, 41, 59, 0.7) 100%)',
        border: '1px solid rgba(245, 158, 11, 0.3)',
        borderRadius: 10,
        padding: '16px 20px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: 14
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          <div style={{
            width: 44,
            height: 44,
            borderRadius: 10,
            background: 'rgba(245, 158, 11, 0.2)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            border: '1px solid rgba(245, 158, 11, 0.4)'
          }}>
            <UserPlus size={24} color="#f59e0b" />
          </div>
          <div>
            <h2 style={{ fontSize: 17, fontWeight: 700, margin: 0, color: 'var(--text-primary)' }}>
              Tự Động Kết Bạn Nhóm (Group Auto-Friend)
            </h2>
            <p style={{ fontSize: 12, color: 'var(--text-secondary)', margin: '4px 0 0' }}>
              Tự động truy cập trang danh sách thành viên nhóm, lọc đối tượng phù hợp và gửi lời mời kết bạn kèm thuật toán Safe-Pacing chống Checkpoint.
            </p>
          </div>
        </div>

        {/* Quick Metric Badges */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{
            background: 'var(--bg-primary)',
            border: '1px solid var(--border-color)',
            borderRadius: 8,
            padding: '6px 14px',
            textAlign: 'center'
          }}>
            <div style={{ fontSize: 10, color: 'var(--text-secondary)', textTransform: 'uppercase', fontWeight: 600 }}>Đã gửi</div>
            <div style={{ fontSize: 18, fontWeight: 700, color: '#10b981' }}>{sentCount}</div>
          </div>
          <div style={{
            background: 'var(--bg-primary)',
            border: '1px solid var(--border-color)',
            borderRadius: 8,
            padding: '6px 14px',
            textAlign: 'center'
          }}>
            <div style={{ fontSize: 10, color: 'var(--text-secondary)', textTransform: 'uppercase', fontWeight: 600 }}>Đã bỏ qua</div>
            <div style={{ fontSize: 18, fontWeight: 700, color: '#94a3b8' }}>{skippedCount}</div>
          </div>
          <div style={{
            background: 'var(--bg-primary)',
            border: '1px solid var(--border-color)',
            borderRadius: 8,
            padding: '6px 14px',
            textAlign: 'center'
          }}>
            <div style={{ fontSize: 10, color: 'var(--text-secondary)', textTransform: 'uppercase', fontWeight: 600 }}>Chỉ tiêu</div>
            <div style={{ fontSize: 18, fontWeight: 700, color: '#f59e0b' }}>{targetCount}</div>
          </div>
        </div>
      </div>

      {/* Main 2-Column Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(340px, 420px) 1fr', gap: 16 }}>
        {/* Left Column: Configuration Form */}
        <div style={{
          background: 'var(--bg-secondary)',
          border: '1px solid var(--border-color)',
          borderRadius: 10,
          padding: 18,
          display: 'flex',
          flexDirection: 'column',
          gap: 14
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, paddingBottom: 10, borderBottom: '1px solid var(--border-color)' }}>
            <Users size={16} color="#f59e0b" />
            <span style={{ fontSize: 13, fontWeight: 700 }}>Cấu hình phiên kết bạn</span>
          </div>

          {/* Source Selection & URL */}
          <div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
              <label style={{ fontSize: 12, fontWeight: 600 }}>
                Nguồn kết bạn mục tiêu: <span style={{ color: '#ef4444' }}>*</span>
              </label>
              <div style={{ display: 'flex', gap: 6 }}>
                <button
                  type="button"
                  onClick={() => setFriendGroupUrl('https://www.facebook.com/friends/suggestions')}
                  disabled={friendBotRunning}
                  style={{
                    padding: '3px 8px',
                    borderRadius: 4,
                    fontSize: 11,
                    fontWeight: 600,
                    background: friendGroupUrl.includes('friends') ? 'rgba(245, 158, 11, 0.25)' : 'var(--bg-primary)',
                    color: friendGroupUrl.includes('friends') ? '#f59e0b' : 'var(--text-secondary)',
                    border: '1px solid ' + (friendGroupUrl.includes('friends') ? '#f59e0b' : 'var(--border-color)'),
                    cursor: 'pointer'
                  }}
                >
                  🎯 Gợi ý kết bạn
                </button>
                <button
                  type="button"
                  onClick={() => {
                    if (friendGroupUrl.includes('friends')) setFriendGroupUrl('');
                  }}
                  disabled={friendBotRunning}
                  style={{
                    padding: '3px 8px',
                    borderRadius: 4,
                    fontSize: 11,
                    fontWeight: 600,
                    background: !friendGroupUrl.includes('friends') && friendGroupUrl ? 'rgba(59, 130, 246, 0.25)' : 'var(--bg-primary)',
                    color: !friendGroupUrl.includes('friends') && friendGroupUrl ? 'var(--accent-blue)' : 'var(--text-secondary)',
                    border: '1px solid ' + (!friendGroupUrl.includes('friends') && friendGroupUrl ? 'var(--accent-blue)' : 'var(--border-color)'),
                    cursor: 'pointer'
                  }}
                >
                  👥 Nhóm Facebook
                </button>
              </div>
            </div>

            <input
              type="text"
              placeholder="https://www.facebook.com/friends/suggestions hoặc https://www.facebook.com/groups/..."
              value={friendGroupUrl}
              onChange={e => setFriendGroupUrl(e.target.value)}
              disabled={friendBotRunning}
              style={{
                width: '100%',
                padding: '8px 12px',
                borderRadius: 6,
                background: 'var(--bg-primary)',
                color: 'var(--text-primary)',
                border: '1px solid var(--border-color)',
                fontSize: 12
              }}
            />
            <span style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 4, display: 'block' }}>
              {friendGroupUrl.includes('friends')
                ? '✨ Đang kết bạn từ trang Gợi ý kết bạn của Facebook (facebook.com/friends/suggestions)'
                : '💡 Hệ thống hỗ trợ cả trang Gợi ý kết bạn hoặc tự động vào trang thành viên nhóm (/members).'}
            </span>
          </div>

          {/* Member Filter Mode */}
          <div>
            <label style={{ fontSize: 12, fontWeight: 600, display: 'block', marginBottom: 6 }}>
              Khu vực thành viên mục tiêu:
            </label>
            <select
              value={friendFilterMode}
              onChange={e => setFriendFilterMode(e.target.value)}
              disabled={friendBotRunning}
              style={{
                width: '100%',
                padding: '8px 12px',
                borderRadius: 6,
                background: 'var(--bg-primary)',
                color: 'var(--text-primary)',
                border: '1px solid var(--border-color)',
                fontSize: 12
              }}
            >
              <option value="all">Tất cả thành viên (/members)</option>
              <option value="things_in_common">Thành viên có điểm chung / Bạn chung (/members_with_things_in_common)</option>
              <option value="new_members">Thành viên mới gia nhập nhóm (/new_members)</option>
            </select>
          </div>

          {/* Max Requests & Delays */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <div>
              <label style={{ fontSize: 12, fontWeight: 600, display: 'block', marginBottom: 6 }}>
                Số lời mời tối đa:
              </label>
              <input
                type="number"
                min="1"
                max="100"
                value={friendMaxRequests}
                onChange={e => setFriendMaxRequests(parseInt(e.target.value) || 20)}
                disabled={friendBotRunning}
                style={{
                  width: '100%',
                  padding: '8px 10px',
                  borderRadius: 6,
                  background: 'var(--bg-primary)',
                  color: 'var(--text-primary)',
                  border: '1px solid var(--border-color)',
                  fontSize: 12
                }}
              />
              <span style={{ fontSize: 10, color: 'var(--text-secondary)', display: 'block', marginTop: 2 }}>
                Khuyên dùng: 15-30/lần
              </span>
            </div>

            <div>
              <label style={{ fontSize: 12, fontWeight: 600, display: 'block', marginBottom: 6 }}>
                Delay an toàn (Giây):
              </label>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <input
                  type="number"
                  min="5"
                  max="60"
                  value={friendDelayMin}
                  onChange={e => setFriendDelayMin(parseFloat(e.target.value) || 10)}
                  disabled={friendBotRunning}
                  placeholder="Min"
                  style={{
                    width: '50%',
                    padding: '8px 8px',
                    borderRadius: 6,
                    background: 'var(--bg-primary)',
                    color: 'var(--text-primary)',
                    border: '1px solid var(--border-color)',
                    fontSize: 12
                  }}
                />
                <span>-</span>
                <input
                  type="number"
                  min="8"
                  max="120"
                  value={friendDelayMax}
                  onChange={e => setFriendDelayMax(parseFloat(e.target.value) || 25)}
                  disabled={friendBotRunning}
                  placeholder="Max"
                  style={{
                    width: '50%',
                    padding: '8px 8px',
                    borderRadius: 6,
                    background: 'var(--bg-primary)',
                    color: 'var(--text-primary)',
                    border: '1px solid var(--border-color)',
                    fontSize: 12
                  }}
                />
              </div>
              <span style={{ fontSize: 10, color: 'var(--text-secondary)', display: 'block', marginTop: 2 }}>
                Thời gian chờ ngẫu nhiên
              </span>
            </div>
          </div>

          {/* Checkboxes */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8, paddingTop: 4 }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={friendSkipExisting}
                onChange={e => setFriendSkipExisting(e.target.checked)}
                disabled={friendBotRunning}
              />
              <span>🛡️ Bỏ qua người đã gửi lời mời trong lịch sử SQLite</span>
            </label>

            <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={friendHeadless}
                onChange={e => setFriendHeadless(e.target.checked)}
                disabled={friendBotRunning}
              />
              <span>Chạy ẩn trình duyệt (Headless - khuyến khích tắt để quan sát)</span>
            </label>
          </div>

          {/* Action Buttons */}
          <div style={{ display: 'flex', gap: 10, marginTop: 10 }}>
            <button
              onClick={onStartFriendBot}
              disabled={friendBotRunning || !friendGroupUrl.trim()}
              style={{
                flex: 1,
                padding: '11px 16px',
                borderRadius: 8,
                backgroundColor: friendBotRunning ? '#4b5563' : '#f59e0b',
                color: '#fff',
                fontWeight: 700,
                fontSize: 13,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 8,
                cursor: friendBotRunning || !friendGroupUrl.trim() ? 'not-allowed' : 'pointer',
                boxShadow: friendBotRunning ? 'none' : '0 2px 8px rgba(245, 158, 11, 0.35)'
              }}
            >
              <Play size={15} className={friendBotRunning ? 'animate-spin' : ''} />
              <span>{friendBotRunning ? 'Bot đang kết bạn...' : '🚀 Bắt đầu kết bạn'}</span>
            </button>

            {friendBotRunning && (
              <button
                onClick={onStopFriendBot}
                style={{
                  padding: '11px 16px',
                  borderRadius: 8,
                  backgroundColor: '#ef4444',
                  color: '#fff',
                  fontWeight: 700,
                  fontSize: 13,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: 6,
                  cursor: 'pointer'
                }}
              >
                <Square size={14} fill="#fff" />
                <span>Dừng</span>
              </button>
            )}
          </div>

          {/* Safety Notice */}
          <div style={{
            background: 'rgba(239, 68, 68, 0.08)',
            border: '1px solid rgba(239, 68, 68, 0.25)',
            borderRadius: 8,
            padding: '10px 12px',
            display: 'flex',
            alignItems: 'flex-start',
            gap: 8
          }}>
            <ShieldCheck size={16} color="#10b981" style={{ flexShrink: 0, marginTop: 2 }} />
            <div style={{ fontSize: 11, color: 'var(--text-secondary)', lineHeight: 1.4 }}>
              <strong>Bảo vệ tài khoản an toàn:</strong> Tự động nhận diện cảnh báo checkpoint Facebook và dừng khẩn cấp. Nên kết bạn tối đa 30-50 người/ngày.
            </div>
          </div>
        </div>

        {/* Right Column: Terminal Logs */}
        <div style={{
          background: 'var(--bg-secondary)',
          border: '1px solid var(--border-color)',
          borderRadius: 10,
          padding: 16,
          display: 'flex',
          flexDirection: 'column',
          height: '100%',
          minHeight: 380
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10, paddingBottom: 8, borderBottom: '1px solid var(--border-color)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Clock size={16} color="#f59e0b" />
              <span style={{ fontSize: 13, fontWeight: 700 }}>Nhật ký thực thi Realtime</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{
                fontSize: 11,
                padding: '2px 8px',
                borderRadius: 12,
                background: friendBotRunning ? 'rgba(245, 158, 11, 0.2)' : 'rgba(148, 163, 184, 0.15)',
                color: friendBotRunning ? '#f59e0b' : 'var(--text-secondary)',
                fontWeight: 600
              }}>
                {friendBotRunning ? 'Đang chạy' : 'Sẵn sàng'}
              </span>
            </div>
          </div>

          {/* Terminal Box */}
          <div
            ref={logContainerRef}
            style={{
              flex: 1,
              background: '#090d16',
              borderRadius: 6,
              border: '1px solid rgba(255, 255, 255, 0.08)',
              padding: 12,
              fontFamily: 'SFMono-Regular, Consolas, "Liberation Mono", Menlo, Courier, monospace',
              fontSize: 12,
              lineHeight: 1.6,
              color: '#d1d5db',
              overflowY: 'auto',
              maxHeight: 340,
              display: 'flex',
              flexDirection: 'column',
              gap: 4
            }}
          >
            {friendBotLogs.length === 0 ? (
              <div style={{ color: '#6b7280', fontStyle: 'italic', padding: '20px 0', textAlign: 'center' }}>
                Chưa có thao tác nào. Nhập link nhóm và bấm "Bắt đầu kết bạn" để chạy.
              </div>
            ) : (
              friendBotLogs.map((log, idx) => {
                let color = '#d1d5db';
                if (log.includes('❌') || log.includes('🚨') || log.includes('CẢNH BÁO')) color = '#f87171';
                else if (log.includes('🤝') || log.includes('🎉') || log.includes('Thành công')) color = '#34d399';
                else if (log.includes('⏳') || log.includes('📜') || log.includes('🔍')) color = '#fbbf24';
                else if (log.includes('🛡️') || log.includes('⏩')) color = '#93c5fd';

                return (
                  <div key={idx} style={{ color, wordBreak: 'break-word' }}>
                    {log}
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>

      {/* History Section: Sent Friend Requests Table */}
      <div style={{
        background: 'var(--bg-secondary)',
        border: '1px solid var(--border-color)',
        borderRadius: 10,
        padding: 18,
        display: 'flex',
        flexDirection: 'column',
        gap: 14
      }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: 12,
          paddingBottom: 10,
          borderBottom: '1px solid var(--border-color)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <CheckCircle2 size={18} color="#10b981" />
            <h3 style={{ fontSize: 15, fontWeight: 700, margin: 0 }}>
              Lịch sử các thành viên đã gửi lời mời ({filteredHistory.length})
            </h3>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            {/* Search input */}
            <div style={{ position: 'relative', width: 220 }}>
              <Search size={14} style={{ position: 'absolute', left: 9, top: 8, color: 'var(--text-secondary)' }} />
              <input
                type="text"
                placeholder="Tìm theo tên/link..."
                value={historySearch}
                onChange={e => setHistorySearch(e.target.value)}
                style={{
                  width: '100%',
                  padding: '6px 10px 6px 28px',
                  borderRadius: 6,
                  background: 'var(--bg-primary)',
                  color: 'var(--text-primary)',
                  border: '1px solid var(--border-color)',
                  fontSize: 12
                }}
              />
            </div>

            <button
              onClick={loadHistory}
              disabled={historyLoading}
              title="Tải lại danh sách"
              style={{
                padding: '6px 10px',
                borderRadius: 6,
                background: 'var(--bg-primary)',
                border: '1px solid var(--border-color)',
                color: 'var(--text-primary)',
                display: 'flex',
                alignItems: 'center',
                gap: 5,
                fontSize: 12,
                cursor: 'pointer'
              }}
            >
              <RefreshCw size={13} className={historyLoading ? 'animate-spin' : ''} />
              <span>Tải lại</span>
            </button>

            <button
              onClick={handleExportCSV}
              disabled={!history.length}
              title="Xuất CSV"
              style={{
                padding: '6px 10px',
                borderRadius: 6,
                background: 'var(--bg-primary)',
                border: '1px solid var(--border-color)',
                color: 'var(--text-primary)',
                display: 'flex',
                alignItems: 'center',
                gap: 5,
                fontSize: 12,
                cursor: history.length ? 'pointer' : 'not-allowed'
              }}
            >
              <Download size={13} />
              <span>Xuất CSV</span>
            </button>

            <button
              onClick={handleClearHistory}
              disabled={!history.length}
              title="Xóa toàn bộ lịch sử"
              style={{
                padding: '6px 10px',
                borderRadius: 6,
                background: 'rgba(239, 68, 68, 0.1)',
                border: '1px solid rgba(239, 68, 68, 0.3)',
                color: '#ef4444',
                display: 'flex',
                alignItems: 'center',
                gap: 5,
                fontSize: 12,
                cursor: history.length ? 'pointer' : 'not-allowed'
              }}
            >
              <Trash2 size={13} />
              <span>Xóa</span>
            </button>
          </div>
        </div>

        {/* History Table */}
        <div style={{ overflowX: 'auto', maxHeight: 380 }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12, textAlign: 'left' }}>
            <thead>
              <tr style={{ background: 'var(--bg-primary)', borderBottom: '1px solid var(--border-color)' }}>
                <th style={{ padding: '8px 12px', fontWeight: 600, width: 60 }}>#</th>
                <th style={{ padding: '8px 12px', fontWeight: 600, width: 150 }}>Thời gian</th>
                <th style={{ padding: '8px 12px', fontWeight: 600 }}>Tên thành viên</th>
                <th style={{ padding: '8px 12px', fontWeight: 600 }}>Profile Facebook</th>
                <th style={{ padding: '8px 12px', fontWeight: 600 }}>Nhóm mục tiêu</th>
                <th style={{ padding: '8px 12px', fontWeight: 600, width: 100 }}>Trạng thái</th>
              </tr>
            </thead>
            <tbody>
              {filteredHistory.length === 0 ? (
                <tr>
                  <td colSpan="6" style={{ textAlign: 'center', padding: '30px 0', color: 'var(--text-secondary)' }}>
                    Chưa có lịch sử gửi lời mời kết bạn nào.
                  </td>
                </tr>
              ) : (
                filteredHistory.map((item, index) => (
                  <tr
                    key={item.id || index}
                    style={{
                      borderBottom: '1px solid var(--border-color)',
                      transition: 'background 0.15s ease'
                    }}
                    onMouseEnter={e => e.currentTarget.style.background = 'var(--bg-hover)'}
                    onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                  >
                    <td style={{ padding: '8px 12px', color: 'var(--text-secondary)' }}>{item.id}</td>
                    <td style={{ padding: '8px 12px', color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>
                      {item.created_at || '—'}
                    </td>
                    <td style={{ padding: '8px 12px', fontWeight: 600, color: 'var(--text-primary)' }}>
                      {item.user_name || 'Thành viên'}
                    </td>
                    <td style={{ padding: '8px 12px' }}>
                      {item.profile_url ? (
                        <a
                          href={item.profile_url}
                          target="_blank"
                          rel="noreferrer"
                          style={{
                            color: 'var(--accent-blue)',
                            textDecoration: 'none',
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: 4
                          }}
                        >
                          <span style={{ maxWidth: 220, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {item.profile_url}
                          </span>
                          <ExternalLink size={12} />
                        </a>
                      ) : (
                        <span style={{ color: 'var(--text-secondary)' }}>—</span>
                      )}
                    </td>
                    <td style={{ padding: '8px 12px', color: 'var(--text-secondary)' }}>
                      <span style={{ maxWidth: 220, display: 'inline-block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {item.group_url || '—'}
                      </span>
                    </td>
                    <td style={{ padding: '8px 12px' }}>
                      <span style={{
                        padding: '3px 8px',
                        borderRadius: 4,
                        fontSize: 11,
                        fontWeight: 600,
                        background: 'rgba(16, 185, 129, 0.15)',
                        color: '#10b981'
                      }}>
                        Đã gửi
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
