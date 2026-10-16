import React from 'react';
import { Layers, Globe, Bot, UserPlus, Cpu, Sparkles } from 'lucide-react';

export default function ActivityBar({
  activeTab,
  setActiveTab,
  leftSidebarOpen,
  setLeftSidebarOpen,
  rightSidebarOpen,
  setRightSidebarOpen
}) {
  return (
    <div style={{
      width: 48,
      backgroundColor: 'var(--bg-primary)',
      borderRight: '1px solid var(--border-color)',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      padding: '12px 0',
      gap: 16,
      zIndex: 50
    }}>
      <button
        onClick={() => setLeftSidebarOpen(!leftSidebarOpen)}
        title={leftSidebarOpen ? "Thu gọn Sidebar" : "Mở Sidebar"}
        style={{
          color: leftSidebarOpen ? 'var(--accent-blue)' : 'var(--text-secondary)',
          padding: 8,
          borderRadius: 6,
          background: leftSidebarOpen ? 'var(--bg-hover)' : 'transparent'
        }}
      >
        <Layers size={20} />
      </button>

      <div style={{ width: 28, height: 1, backgroundColor: 'var(--border-color)' }} />

      <button
        onClick={() => setActiveTab('scraper')}
        title="Cào tin tuyển dụng"
        style={{
          color: activeTab === 'scraper' ? 'var(--accent-blue)' : 'var(--text-secondary)',
          padding: 8,
          borderRadius: 6,
          background: activeTab === 'scraper' ? 'var(--bg-hover)' : 'transparent'
        }}
      >
        <Globe size={20} />
      </button>

      <button
        onClick={() => setActiveTab('bot')}
        title="Bot tương tác tự động (Feed/Bài viết)"
        style={{
          color: activeTab === 'bot' ? 'var(--accent-green)' : 'var(--text-secondary)',
          padding: 8,
          borderRadius: 6,
          background: activeTab === 'bot' ? 'var(--bg-hover)' : 'transparent'
        }}
      >
        <Bot size={20} />
      </button>

      <button
        onClick={() => setActiveTab('friend_bot')}
        title="Tự động kết bạn nhóm (Group Auto-Friend)"
        style={{
          color: activeTab === 'friend_bot' ? '#f59e0b' : 'var(--text-secondary)',
          padding: 8,
          borderRadius: 6,
          background: activeTab === 'friend_bot' ? 'var(--bg-hover)' : 'transparent'
        }}
      >
        <UserPlus size={20} />
      </button>

      <button
        onClick={() => setActiveTab('mcp')}
        title="Cấu hình MCP Server"
        style={{
          color: activeTab === 'mcp' ? 'var(--accent-purple)' : 'var(--text-secondary)',
          padding: 8,
          borderRadius: 6,
          background: activeTab === 'mcp' ? 'var(--bg-hover)' : 'transparent'
        }}
      >
        <Cpu size={20} />
      </button>

      <div style={{ marginTop: 'auto' }}>
        <button
          onClick={() => setRightSidebarOpen(!rightSidebarOpen)}
          title={rightSidebarOpen ? "Thu gọn AI Copilot" : "Mở AI Copilot"}
          style={{
            color: rightSidebarOpen ? 'var(--accent-blue)' : 'var(--text-secondary)',
            padding: 8,
            borderRadius: 6,
            background: rightSidebarOpen ? 'var(--bg-hover)' : 'transparent'
          }}
        >
          <Sparkles size={20} />
        </button>
      </div>
    </div>
  );
}
