import React, { useState } from 'react';
import { Cpu, Check, Copy } from 'lucide-react';

export default function McpWorkspace({ mcpConfig }) {
  const [copiedCmd, setCopiedCmd] = useState(false);
  const [copiedJson, setCopiedJson] = useState(false);

  if (!mcpConfig) return null;

  return (
    <div style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', borderRadius: 8, padding: 18 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
        <Cpu size={22} color="var(--accent-purple)" />
        <h3 style={{ fontSize: 16, fontWeight: 700 }}>Kết Nối MCP Server Cho AI IDE (Cursor, Claude Desktop, Antigravity)</h3>
      </div>
      <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 20 }}>
        Cho phép Claude Desktop, Cursor hoặc Antigravity trực tiếp gọi công cụ cào bài và phân tích Facebook.
      </p>

      <div style={{ marginBottom: 18 }}>
        <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: 6 }}>
          Lệnh kết nối Antigravity CLI (AGY):
        </label>
        <div style={{ display: 'flex', gap: 8 }}>
          <input
            type="text"
            readOnly
            value={mcpConfig.agy_cmd}
            style={{ flex: 1, padding: '7px 10px', borderRadius: 6, background: '#05070a', border: '1px solid var(--border-color)', color: '#7ee787', fontFamily: 'monospace', fontSize: 12 }}
          />
          <button
            onClick={() => {
              navigator.clipboard.writeText(mcpConfig.agy_cmd);
              setCopiedCmd(true);
              setTimeout(() => setCopiedCmd(false), 2000);
            }}
            style={{ padding: '0 12px', borderRadius: 6, background: 'var(--bg-hover)', color: 'var(--text-primary)', fontSize: 12, display: 'flex', alignItems: 'center', gap: 6, border: '1px solid var(--border-color)' }}
          >
            {copiedCmd ? <Check size={14} color="var(--accent-green)" /> : <Copy size={14} />}
            <span>{copiedCmd ? 'Đã chép' : 'Sao chép'}</span>
          </button>
        </div>
      </div>

      <div>
        <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: 6 }}>
          Cấu hình Claude Desktop / Cursor (mcp_config.json):
        </label>
        <div style={{ position: 'relative' }}>
          <pre style={{ background: '#05070a', border: '1px solid var(--border-color)', borderRadius: 6, padding: 12, color: '#f0f6fc', fontSize: 12, overflowX: 'auto' }}>
            {JSON.stringify(mcpConfig.claude_config, null, 2)}
          </pre>
          <button
            onClick={() => {
              navigator.clipboard.writeText(JSON.stringify(mcpConfig.claude_config, null, 2));
              setCopiedJson(true);
              setTimeout(() => setCopiedJson(false), 2000);
            }}
            style={{ position: 'absolute', right: 10, top: 10, padding: '4px 8px', borderRadius: 4, background: 'var(--bg-hover)', color: 'var(--text-primary)', fontSize: 11, display: 'flex', alignItems: 'center', gap: 4, border: '1px solid var(--border-color)' }}
          >
            {copiedJson ? <Check size={12} color="var(--accent-green)" /> : <Copy size={12} />}
            <span>{copiedJson ? 'Đã chép' : 'Copy JSON'}</span>
          </button>
        </div>
      </div>
    </div>
  );
}
