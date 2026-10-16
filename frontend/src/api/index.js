/**
 * API client module for Facebook Automation Suite Backend (FastAPI)
 */

export const api = {
  // Profiles & Auth
  async getProfiles() {
    const res = await fetch('/api/profiles');
    if (!res.ok) throw new Error('Không thể lấy danh sách Chrome profiles');
    return res.json();
  },

  async checkLogin(profilePath) {
    const res = await fetch('/api/auth/check', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ profile_path: profilePath })
    });
    return res.json();
  },

  // Database
  async getDbStats() {
    const res = await fetch('/api/database/stats');
    if (!res.ok) throw new Error('Không thể lấy thống kê SQLite');
    return res.json();
  },

  async getDbPosts() {
    const res = await fetch('/api/database/posts');
    if (!res.ok) throw new Error('Không thể tải bài viết');
    return res.json();
  },

  async clearDatabase() {
    const res = await fetch('/api/database/clear', { method: 'POST' });
    if (!res.ok) throw new Error('Không thể xóa dữ liệu');
    return res.json();
  },

  // Scraper
  async startScraper(params) {
    const res = await fetch('/api/scraper/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params)
    });
    return res.json();
  },

  async getScraperStatus() {
    const res = await fetch('/api/scraper/status');
    return res.json();
  },

  async stopScraper() {
    const res = await fetch('/api/scraper/stop', { method: 'POST' });
    return res.json();
  },

  // Interaction Bot
  async startBot(params) {
    const res = await fetch('/api/bot/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params)
    });
    return res.json();
  },

  async getBotStatus() {
    const res = await fetch('/api/bot/status');
    return res.json();
  },

  async stopBot() {
    const res = await fetch('/api/bot/stop', { method: 'POST' });
    return res.json();
  },

  // Group Auto-Friend Bot
  async startFriendBot(params) {
    const res = await fetch('/api/friend-bot/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params)
    });
    return res.json();
  },

  async getFriendBotStatus() {
    const res = await fetch('/api/friend-bot/status');
    return res.json();
  },

  async stopFriendBot() {
    const res = await fetch('/api/friend-bot/stop', { method: 'POST' });
    return res.json();
  },

  async getFriendHistory(limit = 200) {
    const res = await fetch(`/api/friend-bot/history?limit=${limit}`);
    return res.json();
  },

  async clearFriendHistory() {
    const res = await fetch('/api/friend-bot/history/clear', { method: 'POST' });
    return res.json();
  },

  // AI Copilot
  async batchAnalyze(forceReanalyze = false) {
    const res = await fetch('/api/ai/batch-analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ force_reanalyze: forceReanalyze })
    });
    return res.json();
  },

  async chatCopilot(message) {
    const res = await fetch('/api/ai/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message })
    });
    return res.json();
  },

  // MCP Configuration
  async getMcpConfig() {
    const res = await fetch('/api/mcp/config');
    return res.json();
  }
};
