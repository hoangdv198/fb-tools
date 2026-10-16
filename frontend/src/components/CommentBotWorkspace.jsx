import React, { useState, useEffect, useRef } from 'react';
import {
  MessageSquareQuote,
  MessageCircle,
  Play,
  Square,
  ShieldCheck,
  Sparkles,
  Clock,
  ExternalLink,
  Trash2,
  RefreshCw,
  Search,
  Download,
  AlertTriangle,
  CheckCircle2,
  ThumbsUp,
  Sliders,
  FileText
} from 'lucide-react';
import { api } from '../api';

export default function CommentBotWorkspace({
  selectedProfile,
  commentGroupUrls,
  setCommentGroupUrls,
  commentMaxPosts,
  setCommentMaxPosts,
  commentDelayMin,
  setCommentDelayMin,
  commentDelayMax,
  setCommentDelayMax,
  commentMode,
  setCommentMode,
  commentAIPersona,
  setCommentAIPersona,
  commentAICustomPrompt,
  setCommentAICustomPrompt,
  commentTemplates,
  setCommentTemplates,
  commentKeywords,
  setCommentKeywords,
  commentAutoLike,
  setCommentAutoLike,
  commentFilterScam,
  setCommentFilterScam,
  commentSkipExisting,
  setCommentSkipExisting,
  commentHeadless,
  setCommentHeadless,
  commentBotRunning,
  onStartCommentBot,
  onStopCommentBot,
  commentBotLogs,
  commentBotStats
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
  }, [commentBotLogs]);

  // Tải danh sách lịch sử comment
  const loadHistory = async () => {
    setHistoryLoading(true);
    try {
      const data = await api.getCommentHistory(300);
      setHistory(data.history || []);
    } catch (err) {
      console.error('Lỗi khi tải lịch sử comment:', err);
    } finally {
      setHistoryLoading(false);
    }
  };

  useEffect(() => {
    loadHistory();
  }, []);

  // Tự động cập nhật bảng lịch sử mỗi khi có bài mới comment thành công
  const commentedCount = commentBotStats?.commented ?? 0;
  const likedCount = commentBotStats?.liked ?? 0;
  const skippedCount = commentBotStats?.skipped ?? 0;
  const targetCount = commentBotStats?.total_target ?? commentMaxPosts;

  useEffect(() => {
    if (commentedCount > 0) {
      loadHistory();
    }
  }, [commentedCount]);

  // Xóa lịch sử comment
  const handleClearHistory = async () => {
    if (window.confirm('Bạn có chắc chắn muốn xóa toàn bộ lịch sử comment trong cơ sở dữ liệu?')) {
      try {
        await api.clearCommentHistory();
        setHistory([]);
      } catch (err) {
        alert('Lỗi khi xóa lịch sử: ' + err.message);
      }
    }
  };

  // Xuất CSV lịch sử comment
  const handleExportCSV = () => {
    if (!history.length) return;
    const headers = ['ID', 'Thời gian', 'Nhóm', 'Người đăng', 'Link bài viết', 'Nội dung bình luận', 'Trạng thái'];
    const rows = history.map(item => [
      item.id,
      `"${item.created_at || ''}"`,
      `"${(item.group_name || item.group_url || '').replace(/"/g, '""')}"`,
      `"${(item.author_name || '').replace(/"/g, '""')}"`,
      `"${item.post_url || ''}"`,
      `"${(item.comment_text || '').replace(/"/g, '""')}"`,
      `"${item.status || 'posted'}"`
    ]);

    const csvContent = '\uFEFF' + [headers.join(','), ...rows.map(e => e.join(','))].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `lich_su_comment_fb_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const filteredHistory = history.filter(item => {
    if (!historySearch.trim()) return true;
    const q = historySearch.toLowerCase();
    return (
      (item.author_name && item.author_name.toLowerCase().includes(q)) ||
      (item.group_name && item.group_name.toLowerCase().includes(q)) ||
      (item.comment_text && item.comment_text.toLowerCase().includes(q)) ||
      (item.content_snippet && item.content_snippet.toLowerCase().includes(q))
    );
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* Banner Tiêu đề & Giới thiệu */}
      <div style={{
        background: 'linear-gradient(135deg, rgba(59, 130, 246, 0.08) 0%, rgba(16, 185, 129, 0.08) 100%)',
        border: '1px solid rgba(59, 130, 246, 0.25)',
        borderRadius: 12,
        padding: '18px 24px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: 20
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <div style={{
            width: 48,
            height: 48,
            borderRadius: 12,
            background: 'linear-gradient(135deg, #2563eb, #10b981)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#fff',
            boxShadow: '0 4px 14px rgba(37, 99, 235, 0.35)'
          }}>
            <MessageSquareQuote size={26} />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <h2 style={{ fontSize: 18, fontWeight: 700, margin: 0, color: 'var(--text-primary)' }}>
                Tự Động Bình Luận Bài Viết Trong Nhóm (Group Auto-Comment)
              </h2>
              <span style={{
                background: 'rgba(16, 185, 129, 0.15)',
                color: '#10b981',
                padding: '2px 8px',
                borderRadius: 12,
                fontSize: 11,
                fontWeight: 600
              }}>
                Smart AI & Spintax
              </span>
            </div>
            <p style={{ fontSize: 13, color: 'var(--text-secondary)', margin: '4px 0 0 0' }}>
              Quét bài viết mới nhất trong các nhóm Facebook, tự động Like bài, đọc nội dung và viết bình luận thông minh bằng AI hoặc mẫu Spintax chống spam an toàn.
            </p>
          </div>
        </div>

        {/* Trạng thái hoạt động */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          background: 'var(--bg-secondary)',
          border: '1px solid var(--border-color)',
          padding: '8px 14px',
          borderRadius: 8,
          whiteSpace: 'nowrap'
        }}>
          <span style={{
            width: 9,
            height: 9,
            borderRadius: '50%',
            backgroundColor: commentBotRunning ? '#10b981' : '#64748b',
            boxShadow: commentBotRunning ? '0 0 10px #10b981' : 'none',
            display: 'inline-block'
          }} />
          <span style={{ fontSize: 12, fontWeight: 600 }}>
            {commentBotRunning ? 'Bot đang bình luận...' : 'Bot đang nghỉ'}
          </span>
        </div>
      </div>

      {/* Thẻ Thống kê nhanh (Stats Cards) */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 14 }}>
        <div style={{
          background: 'var(--bg-secondary)',
          border: '1px solid var(--border-color)',
          borderRadius: 10,
          padding: '14px 16px',
          display: 'flex',
          alignItems: 'center',
          gap: 14
        }}>
          <div style={{
            width: 40,
            height: 40,
            borderRadius: 8,
            background: 'rgba(59, 130, 246, 0.15)',
            color: '#3b82f6',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}>
            <MessageCircle size={20} />
          </div>
          <div>
            <div style={{ fontSize: 11, color: 'var(--text-secondary)', fontWeight: 500 }}>ĐÃ BÌNH LUẬN</div>
            <div style={{ fontSize: 20, fontWeight: 700, color: '#3b82f6' }}>
              {commentedCount} <span style={{ fontSize: 13, color: 'var(--text-secondary)', fontWeight: 400 }}>/ {targetCount}</span>
            </div>
          </div>
        </div>

        <div style={{
          background: 'var(--bg-secondary)',
          border: '1px solid var(--border-color)',
          borderRadius: 10,
          padding: '14px 16px',
          display: 'flex',
          alignItems: 'center',
          gap: 14
        }}>
          <div style={{
            width: 40,
            height: 40,
            borderRadius: 8,
            background: 'rgba(16, 185, 129, 0.15)',
            color: '#10b981',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}>
            <ThumbsUp size={20} />
          </div>
          <div>
            <div style={{ fontSize: 11, color: 'var(--text-secondary)', fontWeight: 500 }}>ĐÃ THẢ LIKE</div>
            <div style={{ fontSize: 20, fontWeight: 700, color: '#10b981' }}>{likedCount}</div>
          </div>
        </div>

        <div style={{
          background: 'var(--bg-secondary)',
          border: '1px solid var(--border-color)',
          borderRadius: 10,
          padding: '14px 16px',
          display: 'flex',
          alignItems: 'center',
          gap: 14
        }}>
          <div style={{
            width: 40,
            height: 40,
            borderRadius: 8,
            background: 'rgba(245, 158, 11, 0.15)',
            color: '#f59e0b',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}>
            <ShieldCheck size={20} />
          </div>
          <div>
            <div style={{ fontSize: 11, color: 'var(--text-secondary)', fontWeight: 500 }}>ĐÃ BỎ QUA (SCAM / TRÙNG)</div>
            <div style={{ fontSize: 20, fontWeight: 700, color: '#f59e0b' }}>{skippedCount}</div>
          </div>
        </div>

        <div style={{
          background: 'var(--bg-secondary)',
          border: '1px solid var(--border-color)',
          borderRadius: 10,
          padding: '14px 16px',
          display: 'flex',
          alignItems: 'center',
          gap: 14
        }}>
          <div style={{
            width: 40,
            height: 40,
            borderRadius: 8,
            background: 'rgba(139, 92, 246, 0.15)',
            color: '#8b5cf6',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}>
            <Clock size={20} />
          </div>
          <div>
            <div style={{ fontSize: 11, color: 'var(--text-secondary)', fontWeight: 500 }}>GIÃN CÁCH AN TOÀN</div>
            <div style={{ fontSize: 18, fontWeight: 700, color: '#8b5cf6' }}>
              {commentDelayMin}s - {commentDelayMax}s
            </div>
          </div>
        </div>
      </div>

      {/* Khối Cấu hình Bot & Terminal Console */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: 20 }}>
        {/* Cột Trái: Form Cấu hình */}
        <div style={{
          background: 'var(--bg-secondary)',
          border: '1px solid var(--border-color)',
          borderRadius: 10,
          padding: 20,
          display: 'flex',
          flexDirection: 'column',
          gap: 16
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, borderBottom: '1px solid var(--border-color)', paddingBottom: 10 }}>
            <Sliders size={18} color="var(--accent-blue)" />
            <span style={{ fontSize: 14, fontWeight: 700 }}>Thiết lập chiến dịch bình luận</span>
          </div>

          {/* Danh sách link nhóm */}
          <div>
            <label style={{ fontSize: 12, fontWeight: 600, display: 'block', marginBottom: 6 }}>
              Danh sách Link Nhóm Facebook (Group URLs - mỗi dòng 1 link):
            </label>
            <textarea
              rows={3}
              value={commentGroupUrls}
              onChange={e => setCommentGroupUrls(e.target.value)}
              placeholder="https://www.facebook.com/groups/vieclamit&#10;https://www.facebook.com/groups/tuyendungdanang"
              style={{
                width: '100%',
                padding: '9px 12px',
                borderRadius: 6,
                background: 'var(--bg-primary)',
                color: 'var(--text-primary)',
                border: '1px solid var(--border-color)',
                fontSize: 12,
                fontFamily: 'monospace'
              }}
            />
            <span style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 4, display: 'block' }}>
              💡 Có thể nhập nhiều nhóm. Bot sẽ lần lượt quét bài mới nhất và bình luận theo thứ tự an toàn.
            </span>
          </div>

          {/* Chế độ bình luận (AI vs Templates) */}
          <div>
            <label style={{ fontSize: 12, fontWeight: 600, display: 'block', marginBottom: 6 }}>
              Chế độ tạo nội dung bình luận:
            </label>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
              <button
                type="button"
                onClick={() => setCommentMode('ai')}
                style={{
                  padding: '9px 12px',
                  borderRadius: 6,
                  border: commentMode === 'ai' ? '2px solid var(--accent-blue)' : '1px solid var(--border-color)',
                  background: commentMode === 'ai' ? 'rgba(59, 130, 246, 0.12)' : 'var(--bg-primary)',
                  color: commentMode === 'ai' ? 'var(--accent-blue)' : 'var(--text-primary)',
                  fontWeight: 600,
                  fontSize: 12,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: 8,
                  cursor: 'pointer'
                }}
              >
                <Sparkles size={16} />
                <span>🧠 AI Thông Minh (Smart AI)</span>
              </button>

              <button
                type="button"
                onClick={() => setCommentMode('template')}
                style={{
                  padding: '9px 12px',
                  borderRadius: 6,
                  border: commentMode === 'template' ? '2px solid var(--accent-green)' : '1px solid var(--border-color)',
                  background: commentMode === 'template' ? 'rgba(16, 185, 129, 0.12)' : 'var(--bg-primary)',
                  color: commentMode === 'template' ? 'var(--accent-green)' : 'var(--text-primary)',
                  fontWeight: 600,
                  fontSize: 12,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: 8,
                  cursor: 'pointer'
                }}
              >
                <FileText size={16} />
                <span>📝 Mẫu Bình Luận / Spintax</span>
              </button>
            </div>
          </div>

          {/* Cấu hình chi tiết theo chế độ */}
          {commentMode === 'ai' ? (
            <div style={{
              background: 'rgba(59, 130, 246, 0.05)',
              border: '1px solid rgba(59, 130, 246, 0.2)',
              borderRadius: 8,
              padding: 12,
              display: 'flex',
              flexDirection: 'column',
              gap: 10
            }}>
              <div>
                <label style={{ fontSize: 11, fontWeight: 600, display: 'block', marginBottom: 4 }}>
                  Phong cách AI (Persona):
                </label>
                <select
                  value={commentAIPersona}
                  onChange={e => setCommentAIPersona(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '7px 10px',
                    borderRadius: 6,
                    background: 'var(--bg-primary)',
                    color: 'var(--text-primary)',
                    border: '1px solid var(--border-color)',
                    fontSize: 12
                  }}
                >
                  <option value="ứng viên xin việc chuyên nghiệp">Ứng viên xin việc chuyên nghiệp (hỏi JD, xin liên hệ)</option>
                  <option value="người tìm việc thân thiện và nhiệt tình">Người tìm việc thân thiện & nhiệt tình</option>
                  <option value="đồng nghiệp trao đổi chuyên môn">Đồng nghiệp trao đổi chuyên môn & kết nối</option>
                  <option value="thành viên tích cực của nhóm">Thành viên tích cực của nhóm (up bài, tương tác)</option>
                  <option value="khách hàng quan tâm dịch vụ">Khách hàng quan tâm sản phẩm / dịch vụ</option>
                </select>
              </div>

              <div>
                <label style={{ fontSize: 11, fontWeight: 600, display: 'block', marginBottom: 4 }}>
                  Gợi ý thêm cho AI (Tùy chọn Prompt riêng):
                </label>
                <input
                  type="text"
                  value={commentAICustomPrompt}
                  onChange={e => setCommentAICustomPrompt(e.target.value)}
                  placeholder="Vd: Luôn kết thúc bằng việc xin phép gửi CV qua inbox..."
                  style={{
                    width: '100%',
                    padding: '7px 10px',
                    borderRadius: 6,
                    background: 'var(--bg-primary)',
                    color: 'var(--text-primary)',
                    border: '1px solid var(--border-color)',
                    fontSize: 12
                  }}
                />
              </div>
            </div>
          ) : (
            <div style={{
              background: 'rgba(16, 185, 129, 0.05)',
              border: '1px solid rgba(16, 185, 129, 0.2)',
              borderRadius: 8,
              padding: 12,
              display: 'flex',
              flexDirection: 'column',
              gap: 8
            }}>
              <label style={{ fontSize: 11, fontWeight: 600, display: 'block' }}>
                Mẫu bình luận (mỗi dòng 1 câu, hỗ trợ cú pháp Spintax {'{A|B|C}'}):
              </label>
              <textarea
                rows={4}
                value={commentTemplates}
                onChange={e => setCommentTemplates(e.target.value)}
                placeholder="{Chào bạn|Hi bạn|Chào ad}, {mình quan tâm|cho mình xin thêm thông tin|inbox trao đổi thêm nhé} ạ!"
                style={{
                  width: '100%',
                  padding: '7px 10px',
                  borderRadius: 6,
                  background: 'var(--bg-primary)',
                  color: 'var(--text-primary)',
                  border: '1px solid var(--border-color)',
                  fontSize: 12,
                  fontFamily: 'monospace'
                }}
              />
              <span style={{ fontSize: 11, color: 'var(--accent-green)' }}>
                ✨ Cú pháp Spintax: {'{Chào bạn|Hi bạn}'} sẽ được chọn ngẫu nhiên mỗi lần comment để tránh lặp nội dung.
              </span>
            </div>
          )}

          {/* Lọc theo từ khóa */}
          <div>
            <label style={{ fontSize: 12, fontWeight: 600, display: 'block', marginBottom: 4 }}>
              Lọc theo từ khóa (phân cách bởi dấu phẩy, để trống để comment mọi bài viết mới):
            </label>
            <input
              type="text"
              value={commentKeywords}
              onChange={e => setCommentKeywords(e.target.value)}
              placeholder="vd: tuyển dụng, gia sư, cần người, tìm việc, remote"
              style={{
                width: '100%',
                padding: '7px 10px',
                borderRadius: 6,
                background: 'var(--bg-primary)',
                color: 'var(--text-primary)',
                border: '1px solid var(--border-color)',
                fontSize: 12
              }}
            />
          </div>

          {/* Thông số số lượng & Delay */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10 }}>
            <div>
              <label style={{ fontSize: 11, fontWeight: 600, display: 'block', marginBottom: 4 }}>
                Số bài comment tối đa:
              </label>
              <input
                type="number"
                min={1}
                max={50}
                value={commentMaxPosts}
                onChange={e => setCommentMaxPosts(e.target.value)}
                style={{
                  width: '100%',
                  padding: '7px 10px',
                  borderRadius: 6,
                  background: 'var(--bg-primary)',
                  color: 'var(--text-primary)',
                  border: '1px solid var(--border-color)',
                  fontSize: 12
                }}
              />
            </div>

            <div>
              <label style={{ fontSize: 11, fontWeight: 600, display: 'block', marginBottom: 4 }}>
                Nghỉ tối thiểu (s):
              </label>
              <input
                type="number"
                min={5}
                max={120}
                value={commentDelayMin}
                onChange={e => setCommentDelayMin(e.target.value)}
                style={{
                  width: '100%',
                  padding: '7px 10px',
                  borderRadius: 6,
                  background: 'var(--bg-primary)',
                  color: 'var(--text-primary)',
                  border: '1px solid var(--border-color)',
                  fontSize: 12
                }}
              />
            </div>

            <div>
              <label style={{ fontSize: 11, fontWeight: 600, display: 'block', marginBottom: 4 }}>
                Nghỉ tối đa (s):
              </label>
              <input
                type="number"
                min={10}
                max={180}
                value={commentDelayMax}
                onChange={e => setCommentDelayMax(e.target.value)}
                style={{
                  width: '100%',
                  padding: '7px 10px',
                  borderRadius: 6,
                  background: 'var(--bg-primary)',
                  color: 'var(--text-primary)',
                  border: '1px solid var(--border-color)',
                  fontSize: 12
                }}
              />
            </div>
          </div>

          {/* Tùy chọn an toàn Checkbox */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, paddingTop: 4 }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={commentAutoLike}
                onChange={e => setCommentAutoLike(e.target.checked)}
              />
              <span>👍 Thả Like trước khi comment</span>
            </label>

            <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={commentFilterScam}
                onChange={e => setCommentFilterScam(e.target.checked)}
              />
              <span>🚨 AI lọc bỏ bài lừa đảo/cọc tiền</span>
            </label>

            <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={commentSkipExisting}
                onChange={e => setCommentSkipExisting(e.target.checked)}
              />
              <span>🛡️ Bỏ qua bài đã từng comment</span>
            </label>

            <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={commentHeadless}
                onChange={e => setCommentHeadless(e.target.checked)}
              />
              <span>👁️ Chạy ẩn trình duyệt (Headless)</span>
            </label>
          </div>

          {/* Nút Khởi động / Dừng */}
          <div style={{ display: 'flex', gap: 10, marginTop: 8 }}>
            {!commentBotRunning ? (
              <button
                type="button"
                onClick={onStartCommentBot}
                style={{
                  flex: 1,
                  padding: '11px 16px',
                  borderRadius: 8,
                  backgroundColor: '#2563eb',
                  color: '#fff',
                  fontWeight: 700,
                  fontSize: 13,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: 8,
                  cursor: 'pointer',
                  border: 'none',
                  boxShadow: '0 4px 12px rgba(37, 99, 235, 0.3)'
                }}
              >
                <Play size={16} />
                <span>🚀 Bắt đầu Auto-Comment Nhóm</span>
              </button>
            ) : (
              <button
                type="button"
                onClick={onStopCommentBot}
                style={{
                  flex: 1,
                  padding: '11px 16px',
                  borderRadius: 8,
                  backgroundColor: '#ef4444',
                  color: '#fff',
                  fontWeight: 700,
                  fontSize: 13,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: 8,
                  cursor: 'pointer',
                  border: 'none',
                  boxShadow: '0 4px 12px rgba(239, 68, 68, 0.3)'
                }}
              >
                <Square size={16} />
                <span>🛑 Dừng bot ngay lập tức</span>
              </button>
            )}
          </div>
        </div>

        {/* Cột Phải: Terminal Console */}
        <div style={{
          background: '#0d1117',
          border: '1px solid var(--border-color)',
          borderRadius: 10,
          padding: 16,
          display: 'flex',
          flexDirection: 'column',
          height: 600
        }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            borderBottom: '1px solid #21262d',
            paddingBottom: 10,
            marginBottom: 10
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <div style={{ width: 10, height: 10, borderRadius: '50%', background: '#ff5f56' }} />
              <div style={{ width: 10, height: 10, borderRadius: '50%', background: '#ffbd2e' }} />
              <div style={{ width: 10, height: 10, borderRadius: '50%', background: '#27c93f' }} />
              <span style={{ fontSize: 12, fontWeight: 600, color: '#8b949e', marginLeft: 6 }}>
                Live Terminal Console
              </span>
            </div>
            <span style={{ fontSize: 11, color: '#58a6ff', fontFamily: 'monospace' }}>
              {commentBotRunning ? '● RUNNING' : '○ IDLE'}
            </span>
          </div>

          <div
            ref={logContainerRef}
            style={{
              flex: 1,
              overflowY: 'auto',
              fontFamily: 'SFMono-Regular, Consolas, "Liberation Mono", Menlo, monospace',
              fontSize: 11.5,
              lineHeight: 1.6,
              color: '#c9d1d9',
              paddingRight: 6
            }}
          >
            {commentBotLogs.length === 0 ? (
              <div style={{ color: '#6e7681', padding: '40px 20px', textAlign: 'center' }}>
                <Clock size={32} style={{ margin: '0 auto 12px', opacity: 0.4 }} />
                <div>Chưa có nhật ký hoạt động.</div>
                <div style={{ fontSize: 11, marginTop: 4 }}>
                  Chọn link nhóm và bấm <b>"Bắt đầu Auto-Comment Nhóm"</b> để chạy bot.
                </div>
              </div>
            ) : (
              commentBotLogs.map((log, idx) => (
                <div
                  key={idx}
                  style={{
                    padding: '2px 0',
                    color: log.includes('❌') || log.includes('🚨')
                      ? '#f85149'
                      : log.includes('💬') || log.includes('Thành công')
                      ? '#3fb950'
                      : log.includes('👍')
                      ? '#58a6ff'
                      : log.includes('⏳') || log.includes('Nghỉ')
                      ? '#e3b341'
                      : '#c9d1d9'
                  }}
                >
                  {log}
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Phần Dưới: Lịch sử Bình Luận (History Table) */}
      <div style={{
        background: 'var(--bg-secondary)',
        border: '1px solid var(--border-color)',
        borderRadius: 10,
        padding: 20
      }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: 16,
          flexWrap: 'wrap',
          gap: 12
        }}>
          <div>
            <h3 style={{ fontSize: 15, fontWeight: 700, margin: 0 }}>
              📜 Lịch Sử Đã Bình Luận ({filteredHistory.length}/{history.length})
            </h3>
            <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
              Danh sách tất cả bài viết đã được bot bình luận thành công và lưu trong cơ sở dữ liệu SQLite.
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            {/* Thanh tìm kiếm */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              background: 'var(--bg-primary)',
              border: '1px solid var(--border-color)',
              borderRadius: 6,
              padding: '6px 12px'
            }}>
              <Search size={14} color="var(--text-secondary)" />
              <input
                type="text"
                value={historySearch}
                onChange={e => setHistorySearch(e.target.value)}
                placeholder="Tìm tác giả, nội dung, nhóm..."
                style={{
                  border: 'none',
                  outline: 'none',
                  background: 'transparent',
                  color: 'var(--text-primary)',
                  fontSize: 12,
                  width: 200
                }}
              />
            </div>

            <button
              onClick={loadHistory}
              disabled={historyLoading}
              title="Làm mới bảng"
              style={{
                padding: '7px 12px',
                borderRadius: 6,
                background: 'var(--bg-primary)',
                border: '1px solid var(--border-color)',
                color: 'var(--text-primary)',
                fontSize: 12,
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                cursor: 'pointer'
              }}
            >
              <RefreshCw size={13} className={historyLoading ? 'animate-spin' : ''} />
              <span>Làm mới</span>
            </button>

            <button
              onClick={handleExportCSV}
              disabled={!history.length}
              style={{
                padding: '7px 12px',
                borderRadius: 6,
                background: 'var(--bg-primary)',
                border: '1px solid var(--border-color)',
                color: 'var(--accent-green)',
                fontSize: 12,
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                cursor: history.length ? 'pointer' : 'not-allowed',
                opacity: history.length ? 1 : 0.5
              }}
            >
              <Download size={13} />
              <span>Xuất CSV</span>
            </button>

            <button
              onClick={handleClearHistory}
              disabled={!history.length}
              style={{
                padding: '7px 12px',
                borderRadius: 6,
                background: 'rgba(239, 68, 68, 0.1)',
                border: '1px solid rgba(239, 68, 68, 0.3)',
                color: '#ef4444',
                fontSize: 12,
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                cursor: history.length ? 'pointer' : 'not-allowed',
                opacity: history.length ? 1 : 0.5
              }}
            >
              <Trash2 size={13} />
              <span>Xóa lịch sử</span>
            </button>
          </div>
        </div>

        {/* Bảng Dữ liệu */}
        <div style={{
          maxHeight: 380,
          overflowY: 'auto',
          border: '1px solid var(--border-color)',
          borderRadius: 8
        }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12, textAlign: 'left' }}>
            <thead>
              <tr style={{ background: 'var(--bg-primary)', borderBottom: '1px solid var(--border-color)', color: 'var(--text-secondary)' }}>
                <th style={{ padding: '10px 14px', width: 60 }}>#</th>
                <th style={{ padding: '10px 14px', width: 140 }}>Thời gian</th>
                <th style={{ padding: '10px 14px', width: 180 }}>Người đăng / Nhóm</th>
                <th style={{ padding: '10px 14px', minWidth: 240 }}>Bình luận đã gửi</th>
                <th style={{ padding: '10px 14px', minWidth: 200 }}>Trích đoạn bài viết</th>
                <th style={{ padding: '10px 14px', width: 110 }}>Trạng thái</th>
                <th style={{ padding: '10px 14px', width: 70, textAlign: 'center' }}>Link</th>
              </tr>
            </thead>
            <tbody>
              {filteredHistory.length === 0 ? (
                <tr>
                  <td colSpan={7} style={{ textAlign: 'center', padding: '30px 0', color: 'var(--text-secondary)' }}>
                    {historyLoading ? 'Đang tải dữ liệu...' : 'Chưa có lịch sử bình luận nào.'}
                  </td>
                </tr>
              ) : (
                filteredHistory.map((item, i) => (
                  <tr
                    key={item.id || i}
                    style={{
                      borderBottom: '1px solid var(--border-color)',
                      backgroundColor: i % 2 === 0 ? 'transparent' : 'rgba(255, 255, 255, 0.02)'
                    }}
                  >
                    <td style={{ padding: '10px 14px', color: 'var(--text-secondary)' }}>{item.id}</td>
                    <td style={{ padding: '10px 14px', whiteSpace: 'nowrap' }}>
                      {item.created_at || 'Vừa xong'}
                    </td>
                    <td style={{ padding: '10px 14px' }}>
                      <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                        {item.author_name || 'Người dùng FB'}
                      </div>
                      <div style={{ fontSize: 11, color: 'var(--text-secondary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 180 }}>
                        {item.group_url ? (
                          <a
                            href={item.group_url}
                            target="_blank"
                            rel="noreferrer"
                            style={{ color: 'inherit', textDecoration: 'underline', textUnderlineOffset: 2 }}
                            title={item.group_url}
                          >
                            {item.group_name || 'Nhóm FB'}
                          </a>
                        ) : (
                          item.group_name || 'Nhóm FB'
                        )}
                      </div>
                    </td>
                    <td style={{ padding: '10px 14px', color: 'var(--accent-blue)', fontWeight: 500 }}>
                      💬 "{item.comment_text}"
                    </td>
                    <td style={{ padding: '10px 14px', color: 'var(--text-secondary)', fontSize: 11 }}>
                      {item.content_snippet ? (
                        item.content_snippet.length > 80 ? item.content_snippet.slice(0, 80) + '...' : item.content_snippet
                      ) : (
                        '—'
                      )}
                    </td>
                    <td style={{ padding: '10px 14px' }}>
                      <span style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: 4,
                        padding: '2px 8px',
                        borderRadius: 12,
                        fontSize: 11,
                        fontWeight: 600,
                        background: 'rgba(16, 185, 129, 0.15)',
                        color: '#10b981'
                      }}>
                        <CheckCircle2 size={12} />
                        <span>Đã đăng</span>
                      </span>
                    </td>
                    <td style={{ padding: '10px 14px', textAlign: 'center' }}>
                      {(() => {
                        const targetUrl = item.post_url || item.group_url || (item.post_id && !String(item.post_id).startsWith('-') ? `https://www.facebook.com/${item.post_id}` : null);
                        if (!targetUrl) return <span style={{ color: 'var(--text-secondary)' }}>—</span>;
                        const isPost = targetUrl.includes('/posts/') || targetUrl.includes('/permalink/') || (item.post_id && !String(item.post_id).startsWith('-'));
                        return (
                          <a
                            href={targetUrl}
                            target="_blank"
                            rel="noreferrer"
                            title={isPost ? "Mở bài viết này trên Facebook" : "Mở nhóm Facebook"}
                            style={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: 4,
                              padding: '5px 10px',
                              borderRadius: 6,
                              fontSize: 12,
                              fontWeight: 600,
                              color: '#60a5fa',
                              background: 'rgba(59, 130, 246, 0.12)',
                              border: '1px solid rgba(59, 130, 246, 0.3)',
                              textDecoration: 'none',
                              whiteSpace: 'nowrap',
                              cursor: 'pointer'
                            }}
                          >
                            <span>{isPost ? 'Xem bài' : 'Mở link'}</span>
                            <ExternalLink size={12} />
                          </a>
                        );
                      })()}
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
