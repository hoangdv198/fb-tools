import React, { useState, useRef, useEffect } from 'react';
import { Play, Search, AlertTriangle, Square, Terminal, ChevronDown, ChevronUp, Sparkles, Clock, ExternalLink } from 'lucide-react';

export default function ScraperWorkspace({
  groupUrls,
  setGroupUrls,
  scrapeAll,
  setScrapeAll,
  skipExisting,
  setSkipExisting,
  maxPosts,
  setMaxPosts,
  scraperHeadless,
  setScraperHeadless,
  scraperRunning,
  onStartScraper,
  onStopScraper,
  scraperProgress,
  scraperLogs,
  posts,
  filteredPosts,
  filterScamOnly,
  setFilterScamOnly,
  aiFilter,
  onClearAiFilter,
  searchQuery,
  setSearchQuery,
  onSelectPost
}) {
  const termRef = useRef(null);
  const [formCollapsed, setFormCollapsed] = useState(false);

  useEffect(() => {
    if (termRef.current) {
      termRef.current.scrollTop = termRef.current.scrollHeight;
    }
  }, [scraperLogs]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12, height: '100%', flex: 1, minHeight: 0, overflow: 'hidden' }}>
      {/* Form Input Card (Collapsible) */}
      <div style={{
        background: 'var(--bg-secondary)',
        border: '1px solid var(--border-color)',
        borderRadius: 8,
        padding: formCollapsed ? '10px 14px' : '14px 16px',
        flexShrink: 0,
        transition: 'all 0.2s ease'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: formCollapsed ? 0 : 12 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontWeight: 700, fontSize: 13, color: 'var(--text-primary)' }}>⚙️ Cấu hình cào tin tuyển dụng</span>
            {formCollapsed && (
              <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                ({maxPosts} bài/nhóm • {groupUrls.split('\n').filter(Boolean).length} nhóm • {scraperHeadless ? 'Ẩn duyệt' : 'Hiện duyệt'})
              </span>
            )}
          </div>
          <button
            onClick={() => setFormCollapsed(!formCollapsed)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 4,
              fontSize: 11,
              color: 'var(--text-secondary)',
              background: 'var(--bg-tertiary)',
              border: '1px solid var(--border-color)',
              padding: '3px 8px',
              borderRadius: 4
            }}
          >
            {formCollapsed ? <ChevronDown size={13} /> : <ChevronUp size={13} />}
            <span>{formCollapsed ? 'Mở rộng cấu hình' : 'Thu gọn'}</span>
          </button>
        </div>

        {!formCollapsed && (
          <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr', gap: 16 }}>
            <div>
              <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: 6 }}>
                Danh sách link Group Facebook (mỗi dòng 1 link):
              </label>
              <textarea
                value={groupUrls}
                onChange={e => setGroupUrls(e.target.value)}
                rows={3}
                style={{
                  width: '100%',
                  padding: 8,
                  borderRadius: 6,
                  backgroundColor: 'var(--bg-primary)',
                  color: 'var(--text-primary)',
                  border: '1px solid var(--border-color)',
                  fontSize: 12,
                  fontFamily: 'monospace'
                }}
              />

              <div style={{ display: 'flex', gap: 16, marginTop: 8 }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, cursor: 'pointer' }}>
                  <input type="checkbox" checked={scrapeAll} onChange={e => setScrapeAll(e.target.checked)} />
                  <span>Quét TẤT CẢ bài viết (Mới nhất)</span>
                </label>
                <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, cursor: 'pointer' }}>
                  <input type="checkbox" checked={skipExisting} onChange={e => setSkipExisting(e.target.checked)} />
                  <span>🛡️ Bỏ qua bài đã có trong DB</span>
                </label>
              </div>
            </div>

            <div>
              <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: 6 }}>
                Số bài tối đa mỗi nhóm:
              </label>
              <input
                type="number"
                value={maxPosts}
                onChange={e => setMaxPosts(e.target.value)}
                style={{
                  width: '100%',
                  padding: '6px 10px',
                  borderRadius: 6,
                  backgroundColor: 'var(--bg-primary)',
                  color: 'var(--text-primary)',
                  border: '1px solid var(--border-color)',
                  fontSize: 12,
                  marginBottom: 10
                }}
              />

              <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, cursor: 'pointer', marginBottom: 12 }}>
                <input type="checkbox" checked={scraperHeadless} onChange={e => setScraperHeadless(e.target.checked)} />
                <span>Chạy ẩn trình duyệt (Headless)</span>
              </label>

              <div style={{ display: 'flex', gap: 8 }}>
                <button
                  onClick={onStartScraper}
                  disabled={scraperRunning}
                  style={{
                    flex: 1,
                    padding: '8px 14px',
                    borderRadius: 6,
                    backgroundColor: scraperRunning ? 'var(--bg-hover)' : 'var(--accent-blue)',
                    color: '#fff',
                    fontWeight: 600,
                    fontSize: 13,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: 8
                  }}
                >
                  <Play size={14} className={scraperRunning ? 'animate-spin' : ''} />
                  <span>{scraperRunning ? 'Đang cào bài viết...' : '🚀 Bắt đầu cào dữ liệu'}</span>
                </button>

                {scraperRunning && onStopScraper && (
                  <button
                    onClick={onStopScraper}
                    style={{
                      padding: '8px 14px',
                      borderRadius: 6,
                      backgroundColor: 'rgba(248, 81, 73, 0.2)',
                      color: 'var(--accent-red)',
                      border: '1px solid var(--accent-red)',
                      fontWeight: 600,
                      fontSize: 12,
                      display: 'flex',
                      alignItems: 'center',
                      gap: 6
                    }}
                  >
                    <Square size={13} />
                    <span>Dừng</span>
                  </button>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Progress & Live Log Terminal */}
        {scraperLogs.length > 0 && (
          <div style={{ marginTop: 14 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, fontWeight: 600, color: 'var(--text-secondary)' }}>
                <Terminal size={13} color="var(--accent-blue)" />
                <span>PLAYWRIGHT TERMINAL LOG</span>
              </div>
              <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{scraperProgress}%</span>
            </div>
            <div style={{ height: 4, background: 'var(--bg-hover)', borderRadius: 2, overflow: 'hidden', marginBottom: 8 }}>
              <div style={{ height: '100%', width: `${scraperProgress}%`, background: 'var(--accent-blue)', transition: 'width 0.3s' }} />
            </div>
            <div
              ref={termRef}
              style={{
                background: '#05070a',
                border: '1px solid var(--border-color)',
                borderRadius: 6,
                padding: '10px 12px',
                maxHeight: 110,
                overflowY: 'auto',
                fontSize: 11,
                fontFamily: 'monospace',
                color: '#7ee787',
                display: 'flex',
                flexDirection: 'column',
                gap: 4
              }}
            >
              {scraperLogs.map((log, i) => (
                <div key={i}>{log}</div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Data Table Section (Takes 100% of remaining vertical height) */}
      <div style={{
        background: 'var(--bg-secondary)',
        border: '1px solid var(--border-color)',
        borderRadius: 8,
        padding: '14px 14px 6px 14px',
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        minHeight: 0,
        overflow: 'hidden'
      }}>
        {/* Table Toolbar */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10, flexShrink: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={{ fontWeight: 700, fontSize: 14 }}>Bảng dữ liệu</span>
            <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>({filteredPosts.length} bài)</span>

            {aiFilter && (
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                background: 'rgba(56, 139, 253, 0.15)',
                border: '1px solid var(--accent-blue)',
                padding: '3px 8px',
                borderRadius: 6,
                fontSize: 11,
                color: 'var(--accent-blue)',
                fontWeight: 600
              }}>
                <Sparkles size={12} />
                <span>🎯 Lọc bởi AI: {aiFilter.name}</span>
                <button
                  onClick={onClearAiFilter}
                  title="Xóa bộ lọc AI"
                  style={{
                    color: 'var(--text-muted)',
                    marginLeft: 4,
                    cursor: 'pointer',
                    background: 'transparent',
                    border: 'none',
                    padding: '0 2px',
                    fontSize: 12
                  }}
                >
                  ✕
                </button>
              </div>
            )}

            <button
              onClick={() => setFilterScamOnly(!filterScamOnly)}
              style={{
                padding: '4px 10px',
                borderRadius: 6,
                background: filterScamOnly ? 'rgba(248, 81, 73, 0.2)' : 'var(--bg-tertiary)',
                border: filterScamOnly ? '1px solid var(--accent-red)' : '1px solid var(--border-color)',
                color: filterScamOnly ? 'var(--accent-red)' : 'var(--text-secondary)',
                fontSize: 11,
                fontWeight: 600,
                display: 'flex',
                alignItems: 'center',
                gap: 6
              }}
            >
              <AlertTriangle size={12} />
              <span>{filterScamOnly ? 'Đang lọc Scam (Bật)' : 'Lọc bài Scam'}</span>
            </button>
          </div>

          <div style={{ position: 'relative' }}>
            <Search size={14} style={{ position: 'absolute', left: 8, top: 7, color: 'var(--text-muted)' }} />
            <input
              type="text"
              placeholder="Tìm bài viết, tiêu đề..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              style={{
                padding: '5px 10px 5px 28px',
                borderRadius: 6,
                backgroundColor: 'var(--bg-primary)',
                border: '1px solid var(--border-color)',
                color: 'var(--text-primary)',
                fontSize: 12,
                width: 220
              }}
            />
          </div>
        </div>

        {/* Full-Height Scrollable Table View */}
        <div style={{ flex: 1, overflow: 'auto', minHeight: 0, borderRadius: 6, border: '1px solid var(--border-subtle)' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12, textAlign: 'left' }}>
            <thead style={{ position: 'sticky', top: 0, zIndex: 10, background: 'var(--bg-tertiary)' }}>
              <tr style={{ borderBottom: '1px solid var(--border-color)', color: 'var(--text-secondary)' }}>
                <th style={{ padding: '9px 12px', background: 'var(--bg-tertiary)' }}>Vị trí (AI)</th>
                <th style={{ padding: '9px 12px', background: 'var(--bg-tertiary)', whiteSpace: 'nowrap' }}>⏰ Thời gian đăng</th>
                <th style={{ padding: '9px 12px', background: 'var(--bg-tertiary)' }}>Mức lương</th>
                <th style={{ padding: '9px 12px', background: 'var(--bg-tertiary)' }}>Độ uy tín</th>
                <th style={{ padding: '9px 12px', background: 'var(--bg-tertiary)' }}>Cảnh báo Scam</th>
                <th style={{ padding: '9px 12px', background: 'var(--bg-tertiary)' }}>Nhóm</th>
                <th style={{ padding: '9px 12px', background: 'var(--bg-tertiary)' }}>Liên hệ</th>
                <th style={{ padding: '9px 12px', background: 'var(--bg-tertiary)' }}>Thao tác</th>
              </tr>
            </thead>
            <tbody>
              {filteredPosts.length === 0 ? (
                <tr>
                  <td colSpan={8} style={{ padding: 36, textAlign: 'center', color: 'var(--text-muted)' }}>
                    Chưa có dữ liệu bài viết. Hãy cào bài hoặc bấm 'Tải bảng' từ DB ở thanh bên trái!
                  </td>
                </tr>
              ) : (
                filteredPosts.map((p, idx) => {
                  const isScam = String(p.ai_scam_reason || '').includes('⚠️') || String(p.ai_scam_reason || '').includes('🚨');
                  const score = parseInt(p.ai_trust_score) || 70;
                  const exactTime = p.exact_posted_time || p.posted_time || 'Không rõ';
                  const rawTime = p.posted_time || '';
                  
                  // Chỉ hiển thị link FB nếu có permalink bài viết thật sự (không phải link trang chủ group)
                  const hasLink = Boolean(
                    p.post_url &&
                    p.post_url.startsWith('http') &&
                    p.post_url !== p.group_url &&
                    (p.post_url.includes('/posts/') || p.post_url.includes('/permalink/') || p.post_url.includes('story_fbid'))
                  );

                  return (
                    <tr
                      key={p.post_id || idx}
                      style={{
                        borderBottom: '1px solid var(--border-subtle)',
                        background: idx % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.015)'
                      }}
                    >
                      {/* Vị trí AI - Bấm vào xem chi tiết bài viết ngay trên Web */}
                      <td
                        onClick={() => onSelectPost(p)}
                        style={{
                          padding: '9px 12px',
                          fontWeight: 600,
                          color: 'var(--accent-blue)',
                          maxWidth: 180,
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                          cursor: 'pointer'
                        }}
                        title="Bấm để xem toàn bộ chi tiết bài viết"
                      >
                        <span style={{ textDecoration: 'underline', textUnderlineOffset: 3 }}>
                          {p.ai_title || 'Việc làm'}
                        </span>
                      </td>

                      {/* Thời gian đăng chính xác (Giờ:phút ngày/tháng/năm) */}
                      <td style={{ padding: '9px 12px', whiteSpace: 'nowrap' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 5, color: 'var(--text-primary)', fontWeight: 600 }}>
                          <Clock size={12} color="var(--accent-blue)" />
                          <span>{exactTime}</span>
                        </div>
                        {rawTime && rawTime !== exactTime && (
                          <div style={{ fontSize: 10, color: 'var(--text-muted)', marginLeft: 17, marginTop: 2 }}>
                            ({rawTime})
                          </div>
                        )}
                      </td>

                      <td style={{ padding: '9px 12px', color: 'var(--accent-yellow)', fontWeight: 500, whiteSpace: 'nowrap' }}>
                        {p.ai_salary || 'Thoả thuận'}
                      </td>
                      <td style={{ padding: '9px 12px' }}>
                        <span style={{
                          padding: '2px 8px',
                          borderRadius: 999,
                          fontSize: 10,
                          fontWeight: 700,
                          background: score >= 70 ? 'rgba(63, 185, 80, 0.15)' : 'rgba(248, 81, 73, 0.15)',
                          color: score >= 70 ? 'var(--accent-green)' : 'var(--accent-red)'
                        }}>
                          {score}/100
                        </span>
                      </td>
                      <td style={{ padding: '9px 12px' }}>
                        {isScam ? (
                          <span style={{ color: 'var(--accent-red)', fontSize: 11, fontWeight: 600 }}>
                            🚨 {p.ai_scam_reason}
                          </span>
                        ) : (
                          <span style={{ color: 'var(--accent-green)', fontSize: 11 }}>🟢 An toàn</span>
                        )}
                      </td>
                      <td style={{ padding: '9px 12px', color: 'var(--text-secondary)', maxWidth: 130, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {p.group_name}
                      </td>
                      <td style={{ padding: '9px 12px', color: 'var(--text-muted)', fontSize: 11, whiteSpace: 'nowrap' }}>
                        {p.phones ? `📞 ${p.phones}` : (p.emails ? `✉️ ${p.emails}` : '-')}
                      </td>

                      {/* Thao tác (Chi tiết + Mở bài Facebook nếu có permalink) */}
                      <td style={{ padding: '9px 12px', whiteSpace: 'nowrap' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                          <button
                            onClick={() => onSelectPost(p)}
                            style={{
                              padding: '4px 9px',
                              borderRadius: 5,
                              background: 'var(--bg-tertiary)',
                              border: '1px solid var(--border-color)',
                              color: 'var(--text-primary)',
                              fontSize: 11,
                              fontWeight: 600,
                              cursor: 'pointer'
                            }}
                          >
                            Chi tiết
                          </button>

                          {hasLink ? (
                            <a
                              href={p.post_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              title={`Mở bài viết trực tiếp: ${p.post_url}`}
                              style={{
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: 4,
                                padding: '4px 9px',
                                borderRadius: 5,
                                background: 'rgba(31, 111, 235, 0.12)',
                                border: '1px solid rgba(31, 111, 235, 0.35)',
                                color: 'var(--accent-blue)',
                                fontSize: 11,
                                fontWeight: 600,
                                textDecoration: 'none'
                              }}
                            >
                              <ExternalLink size={11} />
                              <span>Mở FB</span>
                            </a>
                          ) : (
                            <span style={{ fontSize: 10, color: 'var(--text-muted)', fontStyle: 'italic' }}>
                              (Chưa có link FB)
                            </span>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
