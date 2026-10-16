import React, { useState, useEffect, useRef } from 'react';
import { api } from './api';
import { useLocalStorage } from './utils/useLocalStorage';
import ActivityBar from './components/ActivityBar';
import SystemSidebar from './components/SystemSidebar';
import ScraperWorkspace from './components/ScraperWorkspace';
import BotWorkspace from './components/BotWorkspace';
import FriendBotWorkspace from './components/FriendBotWorkspace';
import McpWorkspace from './components/McpWorkspace';
import CopilotDrawer from './components/CopilotDrawer';
import PostDetailModal from './components/PostDetailModal';
import { Globe, Bot, UserPlus, Cpu, Sparkles } from 'lucide-react';

export default function App() {
  // Navigation & Panels (Cached in localStorage)
  const [activeTab, setActiveTab] = useLocalStorage('fb_activeTab', 'scraper');
  const [leftSidebarOpen, setLeftSidebarOpen] = useLocalStorage('fb_leftSidebarOpen', true);
  const [rightSidebarOpen, setRightSidebarOpen] = useLocalStorage('fb_rightSidebarOpen', true);

  // Chrome Profiles & Auth (Profile selection cached in localStorage)
  const [profiles, setProfiles] = useState([]);
  const [selectedProfile, setSelectedProfile] = useLocalStorage('fb_selectedProfile', '');
  const [loginStatus, setLoginStatus] = useState(null);

  // Database State
  const [dbStats, setDbStats] = useState({ size_human: '0 KB', total_posts: 0, analyzed_posts: 0, scam_posts: 0 });
  const [posts, setPosts] = useState([]);
  const [filterScamOnly, setFilterScamOnly] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedPost, setSelectedPost] = useState(null);
  const [aiFilter, setAiFilter] = useState(null); // { name: string, postIds: string[] } | null

  // Scraper State (Cached in localStorage)
  const [groupUrls, setGroupUrls] = useLocalStorage('fb_groupUrls', 'https://www.facebook.com/groups/tieuhochanoi');
  const [scrapeAll, setScrapeAll] = useLocalStorage('fb_scrapeAll', true);
  const [maxPosts, setMaxPosts] = useLocalStorage('fb_maxPosts', 25);
  const [skipExisting, setSkipExisting] = useLocalStorage('fb_skipExisting', true);
  const [scraperHeadless, setScraperHeadless] = useLocalStorage('fb_scraperHeadless', false);
  const [scraperRunning, setScraperRunning] = useState(false);
  const [scraperLogs, setScraperLogs] = useState([]);
  const [scraperProgress, setScraperProgress] = useState(0);

  // Bot State (Cached in localStorage)
  const [botTargetMode, setBotTargetMode] = useLocalStorage('fb_botTargetMode', 'Newfeed');
  const [botTargetUrl, setBotTargetUrl] = useLocalStorage('fb_botTargetUrl', 'https://www.facebook.com/');
  const [botScrolls, setBotScrolls] = useLocalStorage('fb_botScrolls', 8);
  const [botAutoLike, setBotAutoLike] = useLocalStorage('fb_botAutoLike', true);
  const [botAutoComment, setBotAutoComment] = useLocalStorage('fb_botAutoComment', true);
  const [botAutoFriend, setBotAutoFriend] = useLocalStorage('fb_botAutoFriend', false);
  const [botAIPersona, setBotAIPersona] = useLocalStorage('fb_botAIPersona', 'ứng viên xin việc chuyên nghiệp');
  const [botHeadless, setBotHeadless] = useLocalStorage('fb_botHeadless', false);
  const [botRunning, setBotRunning] = useState(false);
  const [botLogs, setBotLogs] = useState([]);

  // Group Auto-Friend Bot State (Cached in localStorage)
  const [friendGroupUrl, setFriendGroupUrl] = useLocalStorage('fb_friendGroupUrl', '');
  const [friendMaxRequests, setFriendMaxRequests] = useLocalStorage('fb_friendMaxRequests', 20);
  const [friendDelayMin, setFriendDelayMin] = useLocalStorage('fb_friendDelayMin', 12);
  const [friendDelayMax, setFriendDelayMax] = useLocalStorage('fb_friendDelayMax', 25);
  const [friendFilterMode, setFriendFilterMode] = useLocalStorage('fb_friendFilterMode', 'all');
  const [friendSkipExisting, setFriendSkipExisting] = useLocalStorage('fb_friendSkipExisting', true);
  const [friendHeadless, setFriendHeadless] = useLocalStorage('fb_friendHeadless', false);
  const [friendBotRunning, setFriendBotRunning] = useState(false);
  const [friendBotLogs, setFriendBotLogs] = useState([]);
  const [friendBotStats, setFriendBotStats] = useState({ sent: 0, skipped: 0, errors: 0, total_target: 20 });

  // Copilot State
  const [chatMessages, setChatMessages] = useState([
    {
      role: 'assistant',
      content: '👋 **Chào bạn! Tôi là AI Agent Copilot.**\n\nTôi chạy trên Local Model bảo mật (cổng 20128). Bạn có thể chat trực tiếp với tôi hoặc chọn tác vụ nhanh:\n- ⚡ Bấm nút **\'Thẩm định toàn bộ\'** ở trên để bóc tách toàn bộ bài.\n- 🚨 Hỏi: *\'Bài nào có dấu hiệu lừa đảo?\'*\n- 💰 Hỏi: *\'Tìm các công việc lương cao nhất?\'*\n- 🔍 Hoặc dán bài viết bất kỳ vào khung chat để tôi thẩm định tức thì.'
    }
  ]);
  const [chatInput, setChatInput] = useState('');
  const [chatLoading, setChatLoading] = useState(false);
  const chatScrollRef = useRef(null);

  // MCP Info
  const [mcpConfig, setMcpConfig] = useState(null);

  // Initial Data Fetching
  useEffect(() => {
    loadProfiles();
    loadDbStats();
    loadPosts();
    loadMcp();
  }, []);

  // Poll running jobs
  useEffect(() => {
    let interval = null;
    if (scraperRunning || botRunning || friendBotRunning) {
      interval = setInterval(async () => {
        if (scraperRunning) {
          const res = await api.getScraperStatus();
          setScraperLogs(res.logs || []);
          setScraperProgress(res.progress || 0);
          if (!res.running) {
            setScraperRunning(false);
            loadDbStats();
            loadPosts();
          }
        }
        if (botRunning) {
          const res = await api.getBotStatus();
          setBotLogs(res.logs || []);
          if (!res.running) setBotRunning(false);
        }
        if (friendBotRunning) {
          const res = await api.getFriendBotStatus();
          setFriendBotLogs(res.logs || []);
          setFriendBotStats(res.stats || { sent: 0, skipped: 0, errors: 0, total_target: friendMaxRequests });
          if (!res.running) {
            setFriendBotRunning(false);
          }
        }
      }, 1500);
    }
    return () => clearInterval(interval);
  }, [scraperRunning, botRunning, friendBotRunning, friendMaxRequests]);

  // Chat auto-scroll
  useEffect(() => {
    if (chatScrollRef.current) {
      chatScrollRef.current.scrollTop = chatScrollRef.current.scrollHeight;
    }
  }, [chatMessages, chatLoading]);

  // Load Chrome profiles and preserve cached selection
  const loadProfiles = async () => {
    try {
      const data = await api.getProfiles();
      const list = data.profiles || [];
      setProfiles(list);
      if (list.length > 0) {
        setSelectedProfile(prev => {
          // If cached selection is still valid in profile list, keep it
          if (prev && list.some(p => p.path === prev)) {
            return prev;
          }
          // Otherwise default to the first profile
          return list[0].path;
        });
      }
    } catch (e) {
      console.error('Lỗi khi tải Chrome profiles:', e);
    }
  };

  const loadDbStats = async () => {
    try {
      const data = await api.getDbStats();
      setDbStats(data);
    } catch (e) { console.error(e); }
  };

  const loadPosts = async () => {
    try {
      const data = await api.getDbPosts();
      setPosts(data.posts || []);
    } catch (e) { console.error(e); }
  };

  const loadMcp = async () => {
    try {
      const data = await api.getMcpConfig();
      setMcpConfig(data);
    } catch (e) { console.error(e); }
  };

  const handleCheckLogin = async () => {
    setLoginStatus('checking');
    try {
      const data = await api.checkLogin(selectedProfile);
      setLoginStatus(data.logged_in ? 'logged_in' : 'not_logged_in');
    } catch {
      setLoginStatus('not_logged_in');
    }
  };

  const handleClearDb = async () => {
    if (!window.confirm('Bạn có chắc chắn muốn xóa sạch toàn bộ bài viết trong Database không?')) return;
    try {
      await api.clearDatabase();
      loadDbStats();
      setPosts([]);
    } catch (e) { console.error(e); }
  };

  const handleStartScraper = async () => {
    setScraperRunning(true);
    setScraperLogs([]);
    setScraperProgress(0);
    try {
      const urls = groupUrls.split('\n').map(u => u.trim()).filter(Boolean);
      await api.startScraper({
        profile_path: selectedProfile,
        group_urls: urls,
        keywords: [],
        scrape_all: scrapeAll,
        max_posts: parseInt(maxPosts),
        skip_existing: skipExisting,
        headless: scraperHeadless
      });
    } catch (e) {
      console.error(e);
      setScraperRunning(false);
    }
  };

  const handleStopScraper = async () => {
    try {
      await api.stopScraper();
      setScraperRunning(false);
    } catch (e) {
      console.error(e);
    }
  };

  const handleStartBot = async () => {
    setBotRunning(true);
    setBotLogs([]);
    try {
      await api.startBot({
        profile_path: selectedProfile,
        target_mode: botTargetMode === 'Newfeed' ? 'Bảng tin trang chủ (Newfeed)' : 'Nhóm Facebook cụ thể',
        target_url: botTargetUrl,
        total_scrolls: parseInt(botScrolls),
        auto_like: botAutoLike,
        like_ratio: 0.6,
        auto_comment: botAutoComment,
        use_ai_comment: true,
        ai_persona: botAIPersona,
        max_comments: 3,
        auto_add_friend: botAutoFriend,
        headless: botHeadless
      });
    } catch (e) {
      console.error(e);
      setBotRunning(false);
    }
  };

  const handleStartFriendBot = async () => {
    if (!friendGroupUrl.trim()) return;
    setFriendBotRunning(true);
    setFriendBotLogs([]);
    setFriendBotStats({ sent: 0, skipped: 0, errors: 0, total_target: parseInt(friendMaxRequests) || 20 });
    try {
      await api.startFriendBot({
        profile_path: selectedProfile,
        group_url: friendGroupUrl,
        max_requests: parseInt(friendMaxRequests) || 20,
        delay_min: parseFloat(friendDelayMin) || 12,
        delay_max: parseFloat(friendDelayMax) || 25,
        filter_mode: friendFilterMode,
        skip_already_sent: friendSkipExisting,
        headless: friendHeadless
      });
    } catch (e) {
      console.error(e);
      setFriendBotRunning(false);
    }
  };

  const handleStopFriendBot = async () => {
    try {
      await api.stopFriendBot();
    } catch (e) {
      console.error(e);
    }
  };

  const handleBatchAI = async () => {
    setChatLoading(true);
    setChatMessages(prev => [...prev, { role: 'user', content: '🚀 Yêu cầu thẩm định toàn bộ bài viết trong cơ sở dữ liệu.' }]);
    try {
      const data = await api.batchAnalyze(false);
      loadDbStats();
      loadPosts();
      setChatMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content: `✅ **Hoàn tất thẩm định AI!**\n\n- Đã phân tích mới: **${data.analyzed} bài**\n- Tổng số bài có thẩm định AI: **${data.total_analyzed} bài**\n\n*Các cột Vị trí, Mức lương, Độ uy tín đã được cập nhật trực tiếp vào bảng danh sách.*`
        }
      ]);
    } catch (e) {
      setChatMessages(prev => [...prev, { role: 'assistant', content: `❌ Lỗi khi phân tích: ${e.message}` }]);
    } finally {
      setChatLoading(false);
    }
  };

  const handleSendMessage = async (customText) => {
    const textToSend = (typeof customText === 'string' ? customText : chatInput).trim();
    if (!textToSend || chatLoading) return;
    setChatMessages(prev => [...prev, { role: 'user', content: textToSend }]);
    setChatInput('');
    setChatLoading(true);

    try {
      const data = await api.chatCopilot(textToSend);
      setChatMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content: data.reply,
          action: data.action
        }
      ]);

      // Phản hồi hành động từ AI Agent (Filter / Reset)
      if (data.action) {
        if (data.action.type === 'FILTER_POSTS') {
          setAiFilter({
            name: data.action.filter_name || 'Bộ lọc AI',
            postIds: data.action.post_ids || []
          });
          setActiveTab('scraper'); // Tự động chuyển tab sang cào tin để thấy bảng được lọc
        } else if (data.action.type === 'RESET_FILTER') {
          setAiFilter(null);
        }
      }
    } catch (e) {
      setChatMessages(prev => [...prev, { role: 'assistant', content: `❌ Lỗi kết nối AI: ${e.message}` }]);
    } finally {
      setChatLoading(false);
    }
  };

  // Filter posts (Tích hợp AI Filter + Scam Filter + Search Box)
  const filteredPosts = posts.filter(p => {
    const pid = String(p.post_id || p.id || '');

    // 1. Bộ lọc AI điều khiển
    if (aiFilter && aiFilter.postIds) {
      if (!aiFilter.postIds.includes(pid)) {
        return false;
      }
    }

    // 2. Lọc bài Scam
    if (filterScamOnly) {
      const scamNotice = String(p.ai_scam_reason || '');
      const trustScore = parseInt(p.ai_trust_score) || 100;
      if (!scamNotice.includes('⚠️') && !scamNotice.includes('🚨') && trustScore >= 60) {
        return false;
      }
    }

    // 3. Tìm kiếm từ khoá thủ công
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const content = String(p.content || '').toLowerCase();
      const title = String(p.ai_title || '').toLowerCase();
      const group = String(p.group_name || '').toLowerCase();
      return content.includes(q) || title.includes(q) || group.includes(q);
    }
    return true;
  });

  return (
    <div style={{ display: 'flex', height: '100vh', width: '100vw', overflow: 'hidden', backgroundColor: 'var(--bg-primary)' }}>
      {/* Activity Bar */}
      <ActivityBar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        leftSidebarOpen={leftSidebarOpen}
        setLeftSidebarOpen={setLeftSidebarOpen}
        rightSidebarOpen={rightSidebarOpen}
        setRightSidebarOpen={setRightSidebarOpen}
      />

      {/* Collapsible Left System Sidebar */}
      <SystemSidebar
        isOpen={leftSidebarOpen}
        onClose={() => setLeftSidebarOpen(false)}
        profiles={profiles}
        selectedProfile={selectedProfile}
        setSelectedProfile={setSelectedProfile}
        loginStatus={loginStatus}
        onCheckLogin={handleCheckLogin}
        dbStats={dbStats}
        onRefreshDbStats={loadDbStats}
        onLoadPosts={loadPosts}
        onClearDb={handleClearDb}
      />

      {/* Main Workspace */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', backgroundColor: 'var(--bg-primary)' }}>
        {/* Workspace Tab Bar */}
        <div style={{
          height: 40,
          backgroundColor: 'var(--bg-secondary)',
          borderBottom: '1px solid var(--border-color)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 12px'
        }}>
          <div style={{ display: 'flex', height: '100%', alignItems: 'flex-end', gap: 2 }}>
            <button
              onClick={() => setActiveTab('scraper')}
              style={{
                height: 34,
                padding: '0 14px',
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                fontSize: 12,
                fontWeight: 600,
                color: activeTab === 'scraper' ? 'var(--text-primary)' : 'var(--text-secondary)',
                backgroundColor: activeTab === 'scraper' ? 'var(--bg-primary)' : 'transparent',
                borderTop: activeTab === 'scraper' ? '2px solid var(--accent-blue)' : '2px solid transparent',
                borderLeft: activeTab === 'scraper' ? '1px solid var(--border-color)' : '1px solid transparent',
                borderRight: activeTab === 'scraper' ? '1px solid var(--border-color)' : '1px solid transparent',
                borderBottom: 'none',
                borderRadius: '4px 4px 0 0'
              }}
            >
              <Globe size={14} color="var(--accent-blue)" />
              <span>📊 Cào tin tuyển dụng</span>
            </button>

            <button
              onClick={() => setActiveTab('bot')}
              style={{
                height: 34,
                padding: '0 14px',
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                fontSize: 12,
                fontWeight: 600,
                color: activeTab === 'bot' ? 'var(--text-primary)' : 'var(--text-secondary)',
                backgroundColor: activeTab === 'bot' ? 'var(--bg-primary)' : 'transparent',
                borderTop: activeTab === 'bot' ? '2px solid var(--accent-green)' : '2px solid transparent',
                borderLeft: activeTab === 'bot' ? '1px solid var(--border-color)' : '1px solid transparent',
                borderRight: activeTab === 'bot' ? '1px solid var(--border-color)' : '1px solid transparent',
                borderBottom: 'none',
                borderRadius: '4px 4px 0 0'
              }}
            >
              <Bot size={14} color="var(--accent-green)" />
              <span>🤖 Tương tác Feed</span>
            </button>

            <button
              onClick={() => setActiveTab('friend_bot')}
              style={{
                height: 34,
                padding: '0 14px',
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                fontSize: 12,
                fontWeight: 600,
                color: activeTab === 'friend_bot' ? 'var(--text-primary)' : 'var(--text-secondary)',
                backgroundColor: activeTab === 'friend_bot' ? 'var(--bg-primary)' : 'transparent',
                borderTop: activeTab === 'friend_bot' ? '2px solid #f59e0b' : '2px solid transparent',
                borderLeft: activeTab === 'friend_bot' ? '1px solid var(--border-color)' : '1px solid transparent',
                borderRight: activeTab === 'friend_bot' ? '1px solid var(--border-color)' : '1px solid transparent',
                borderBottom: 'none',
                borderRadius: '4px 4px 0 0'
              }}
            >
              <UserPlus size={14} color="#f59e0b" />
              <span>🤝 Kết bạn nhóm</span>
            </button>

            <button
              onClick={() => setActiveTab('mcp')}
              style={{
                height: 34,
                padding: '0 14px',
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                fontSize: 12,
                fontWeight: 600,
                color: activeTab === 'mcp' ? 'var(--text-primary)' : 'var(--text-secondary)',
                backgroundColor: activeTab === 'mcp' ? 'var(--bg-primary)' : 'transparent',
                borderTop: activeTab === 'mcp' ? '2px solid var(--accent-purple)' : '2px solid transparent',
                borderLeft: activeTab === 'mcp' ? '1px solid var(--border-color)' : '1px solid transparent',
                borderRight: activeTab === 'mcp' ? '1px solid var(--border-color)' : '1px solid transparent',
                borderBottom: 'none',
                borderRadius: '4px 4px 0 0'
              }}
            >
              <Cpu size={14} color="var(--accent-purple)" />
              <span>🔌 MCP Server</span>
            </button>
          </div>

          {!rightSidebarOpen && (
            <button
              onClick={() => setRightSidebarOpen(true)}
              style={{
                padding: '4px 10px',
                borderRadius: 4,
                backgroundColor: 'var(--bg-hover)',
                color: 'var(--accent-blue)',
                fontSize: 11,
                fontWeight: 600,
                display: 'flex',
                alignItems: 'center',
                gap: 6
              }}
            >
              <Sparkles size={13} />
              <span>Mở AI Copilot</span>
            </button>
          )}
        </div>

        {/* Tab Body */}
        <div style={{ flex: 1, overflow: activeTab === 'scraper' ? 'hidden' : 'auto', padding: '14px 16px', display: 'flex', flexDirection: 'column', minHeight: 0 }}>
          {activeTab === 'scraper' && (
            <ScraperWorkspace
              groupUrls={groupUrls}
              setGroupUrls={setGroupUrls}
              scrapeAll={scrapeAll}
              setScrapeAll={setScrapeAll}
              skipExisting={skipExisting}
              setSkipExisting={setSkipExisting}
              maxPosts={maxPosts}
              setMaxPosts={setMaxPosts}
              scraperHeadless={scraperHeadless}
              setScraperHeadless={setScraperHeadless}
              scraperRunning={scraperRunning}
              onStartScraper={handleStartScraper}
              onStopScraper={handleStopScraper}
              scraperProgress={scraperProgress}
              scraperLogs={scraperLogs}
              posts={posts}
              filteredPosts={filteredPosts}
              filterScamOnly={filterScamOnly}
              setFilterScamOnly={setFilterScamOnly}
              aiFilter={aiFilter}
              onClearAiFilter={() => setAiFilter(null)}
              searchQuery={searchQuery}
              setSearchQuery={setSearchQuery}
              onSelectPost={setSelectedPost}
            />
          )}

          {activeTab === 'bot' && (
            <BotWorkspace
              botTargetMode={botTargetMode}
              setBotTargetMode={setBotTargetMode}
              botTargetUrl={botTargetUrl}
              setBotTargetUrl={setBotTargetUrl}
              botScrolls={botScrolls}
              setBotScrolls={setBotScrolls}
              botAutoLike={botAutoLike}
              setBotAutoLike={setBotAutoLike}
              botAutoComment={botAutoComment}
              setBotAutoComment={setBotAutoComment}
              botAutoFriend={botAutoFriend}
              setBotAutoFriend={setBotAutoFriend}
              botAIPersona={botAIPersona}
              setBotAIPersona={setBotAIPersona}
              botHeadless={botHeadless}
              setBotHeadless={setBotHeadless}
              botRunning={botRunning}
              onStartBot={handleStartBot}
              botLogs={botLogs}
            />
          )}

          {activeTab === 'friend_bot' && (
            <FriendBotWorkspace
              selectedProfile={selectedProfile}
              friendGroupUrl={friendGroupUrl}
              setFriendGroupUrl={setFriendGroupUrl}
              friendMaxRequests={friendMaxRequests}
              setFriendMaxRequests={setFriendMaxRequests}
              friendDelayMin={friendDelayMin}
              setFriendDelayMin={setFriendDelayMin}
              friendDelayMax={friendDelayMax}
              setFriendDelayMax={setFriendDelayMax}
              friendFilterMode={friendFilterMode}
              setFriendFilterMode={setFriendFilterMode}
              friendSkipExisting={friendSkipExisting}
              setFriendSkipExisting={setFriendSkipExisting}
              friendHeadless={friendHeadless}
              setFriendHeadless={setFriendHeadless}
              friendBotRunning={friendBotRunning}
              onStartFriendBot={handleStartFriendBot}
              onStopFriendBot={handleStopFriendBot}
              friendBotLogs={friendBotLogs}
              friendBotStats={friendBotStats}
            />
          )}

          {activeTab === 'mcp' && (
            <McpWorkspace mcpConfig={mcpConfig} />
          )}
        </div>
      </div>

      {/* Right AI Copilot Drawer (Full-Height 100vh) */}
      <CopilotDrawer
        isOpen={rightSidebarOpen}
        onClose={() => setRightSidebarOpen(false)}
        totalPosts={posts.length}
        analyzedPosts={dbStats.analyzed_posts}
        scamPosts={dbStats.scam_posts}
        filterScamOnly={filterScamOnly}
        onToggleFilterScam={() => setFilterScamOnly(!filterScamOnly)}
        chatMessages={chatMessages}
        onClearChat={() => setChatMessages([])}
        chatInput={chatInput}
        setChatInput={setChatInput}
        chatLoading={chatLoading}
        onSendMessage={handleSendMessage}
        onBatchAnalyze={handleBatchAI}
        chatScrollRef={chatScrollRef}
      />

      {/* Post Detail Modal */}
      <PostDetailModal post={selectedPost} onClose={() => setSelectedPost(null)} />
    </div>
  );
}
