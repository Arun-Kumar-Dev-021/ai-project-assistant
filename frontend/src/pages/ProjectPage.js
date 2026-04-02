import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  getProject, sendMessage, getConversations, getChatHistory,
  deleteConversation, getProjectImages, getMemory, deleteMemory,
  triggerAgent, getAgentStatus, getAgentJobs
} from '../lib/api';

// ── Toast ──────────────────────────────────────────────────
function Toast({ msg, type, onClose }) {
  useEffect(() => { const t = setTimeout(onClose, 3000); return () => clearTimeout(t); }, [onClose]);
  return <div className={`toast ${type}`}>{msg}</div>;
}

// ── Chat Tab ───────────────────────────────────────────────
function ChatTab({ project }) {
  const [conversations, setConversations] = useState([]);
  const [activeConv, setActiveConv] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => { loadConvs(); }, [project.id]);
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages, sending]);

  async function loadConvs() {
    try { setConversations(await getConversations(project.id)); } catch (e) {}
  }

  async function openConv(conv) {
    setActiveConv(conv);
    try {
      const hist = await getChatHistory(conv.id);
      setMessages(hist);
    } catch (e) {}
  }

  async function newConv() { setActiveConv(null); setMessages([]); }

  async function deleteConv(convId, e) {
    e.stopPropagation();
    await deleteConversation(convId);
    if (activeConv?.id === convId) { setActiveConv(null); setMessages([]); }
    loadConvs();
  }

  async function send() {
    if (!input.trim() || sending) return;
    const text = input.trim();
    setInput('');
    setSending(true);
    setMessages(m => [...m, { role: 'user', content: text, id: 'tmp-' + Date.now() }]);
    try {
      const res = await sendMessage({ project_id: project.id, conversation_id: activeConv?.id || null, message: text });
      if (!activeConv) {
        setActiveConv({ id: res.conversation_id, title: text.slice(0, 50) });
        loadConvs();
      }
      setMessages(m => [
        ...m.filter(x => !x.id?.startsWith('tmp-')),
        { role: 'assistant', content: res.message, tool_calls: res.tool_calls, id: 'ai-' + Date.now() }
      ]);
    } catch (e) {
      setMessages(m => m.filter(x => !x.id?.startsWith('tmp-')));
      alert('Error: ' + (e.response?.data?.detail || e.message));
    } finally { setSending(false); }
  }

  function handleKey(e) { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); } }

  return (
    <div style={{ display: 'flex', height: '100%', gap: 0 }}>
      {/* Conversation sidebar */}
      <div style={{ width: 200, minWidth: 200, borderRight: '1px solid var(--border)', padding: '12px 8px', display: 'flex', flexDirection: 'column', gap: 8, overflow: 'hidden' }}>
        <button className="btn btn-secondary btn-sm" style={{ width: '100%' }} onClick={newConv}>+ New Chat</button>
        <div style={{ overflowY: 'auto', flex: 1 }}>
          <div className="conv-list">
            {conversations.map(c => (
              <div key={c.id} className={`conv-item ${activeConv?.id === c.id ? 'active' : ''}`} onClick={() => openConv(c)}>
                <span title={c.title}>{c.title || 'Chat'}</span>
                <button className="conv-delete" onClick={e => deleteConv(c.id, e)}>×</button>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Chat main */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', padding: '16px 20px 16px' }}>
        {messages.length === 0 && !sending ? (
          <div className="empty" style={{ flex: 1 }}>
            <div className="empty-icon">💬</div>
            <h3>Start a conversation</h3>
            <p>Ask Claude anything about your project. Try: "What should I work on first?" or "Generate a logo image"</p>
          </div>
        ) : (
          <div className="messages">
            {messages.map((m, i) => (
              <MessageBubble key={m.id || i} msg={m} />
            ))}
            {sending && (
              <div className="msg assistant">
                <div className="msg-avatar">🤖</div>
                <div className="typing-indicator">
                  <div className="typing-dot" /><div className="typing-dot" /><div className="typing-dot" />
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>
        )}
        <div className="chat-input-area">
          <div className="chat-input-row">
            <textarea
              className="chat-textarea"
              placeholder="Message Claude... (Enter to send, Shift+Enter for new line)"
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKey}
              rows={1}
            />
            <button className="send-btn" onClick={send} disabled={!input.trim() || sending}>
              {sending ? <div className="spinner" style={{ width: 18, height: 18, borderWidth: 2 }} /> : '↑'}
            </button>
          </div>
          <div style={{ fontSize: 11, color: 'var(--text3)', marginTop: 8, paddingLeft: 2 }}>
            Claude can generate images, analyze them, search the web, and remember your project context
          </div>
        </div>
      </div>
    </div>
  );
}

function MessageBubble({ msg }) {
  const isUser = msg.role === 'user';
  const toolCalls = msg.tool_calls || [];

  // Extract image from tool results
  let generatedImageUrl = null;
  if (msg.tool_results) {
    for (const tr of msg.tool_results) {
      try {
        const parsed = JSON.parse(tr.content || '{}');
        if (parsed.url) { generatedImageUrl = parsed.url; break; }
      } catch {}
    }
  }

  return (
    <div className={`msg ${isUser ? 'user' : 'assistant'}`}>
      <div className="msg-avatar">{isUser ? '👤' : '🤖'}</div>
      <div>
        {toolCalls.length > 0 && (
          <div style={{ marginBottom: 8 }}>
            {toolCalls.map((tc, i) => (
              <span key={i} className="tool-badge done">⚡ {tc.name}</span>
            ))}
          </div>
        )}
        {msg.content && (
          <div className="msg-bubble">
            {isUser ? msg.content : <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>}
          </div>
        )}
        {generatedImageUrl && (
          <div className="msg-image" style={{ marginTop: 8 }}>
            <img src={generatedImageUrl} alt="Generated" style={{ maxWidth: 280, borderRadius: 8, border: '1px solid var(--border)' }} />
          </div>
        )}
      </div>
    </div>
  );
}

// ── Images Tab ─────────────────────────────────────────────
function ImagesTab({ project }) {
  const [images, setImages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState(null);

  useEffect(() => { load(); }, [project.id]);

  async function load() {
    try { setImages(await getProjectImages(project.id)); } catch (e) {}
    finally { setLoading(false); }
  }

  if (loading) return <div className="empty"><div className="spinner" /></div>;

  return (
    <div>
      <div className="section-header">
        <div className="section-title">Project Images ({images.length})</div>
        <span style={{ fontSize: 12, color: 'var(--text3)' }}>Generate images by asking Claude in the chat</span>
      </div>
      {images.length === 0 ? (
        <div className="empty">
          <div className="empty-icon">🎨</div>
          <h3>No images yet</h3>
          <p>Ask Claude to "generate an image of..." in the chat</p>
        </div>
      ) : (
        <div className="img-grid">
          {images.map(img => (
            <div key={img.id} className="img-card" onClick={() => setSelected(img)}>
              <img src={img.url} alt={img.prompt} onError={e => { e.target.src = `https://picsum.photos/seed/${img.id}/300/300`; }} />
              <div className="img-card-info">
                <div className="img-card-prompt">{img.prompt}</div>
                <div style={{ fontSize: 10, color: 'var(--text3)', marginTop: 3 }}>{new Date(img.created_at).toLocaleDateString()}</div>
              </div>
            </div>
          ))}
        </div>
      )}

      {selected && (
        <div className="modal-overlay" onClick={e => e.target === e.currentTarget && setSelected(null)}>
          <div className="modal" style={{ width: 560 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
              <div className="modal-title" style={{ marginBottom: 0 }}>Image Details</div>
              <button className="btn btn-secondary btn-sm" onClick={() => setSelected(null)}>Close</button>
            </div>
            <img src={selected.url} alt={selected.prompt} style={{ width: '100%', borderRadius: 8, marginBottom: 12 }} onError={e => { e.target.src = `https://picsum.photos/seed/${selected.id}/500/500`; }} />
            <div style={{ fontSize: 13, color: 'var(--text2)', marginBottom: 8 }}><strong>Prompt:</strong> {selected.prompt}</div>
            {selected.analysis && <div style={{ fontSize: 13, color: 'var(--text2)', background: 'var(--bg3)', padding: 10, borderRadius: 8 }}><strong>Analysis:</strong> {selected.analysis}</div>}
            <div style={{ fontSize: 11, color: 'var(--text3)', marginTop: 8 }}>ID: {selected.id}</div>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Memory Tab ─────────────────────────────────────────────
function MemoryTab({ project }) {
  const [memory, setMemory] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => { load(); }, [project.id]);

  async function load() {
    try { setMemory(await getMemory(project.id)); } catch (e) {}
    finally { setLoading(false); }
  }

  async function del(id) {
    if (!window.confirm('Delete this memory?')) return;
    await deleteMemory(id);
    load();
  }

  const grouped = memory.reduce((acc, m) => { (acc[m.category] = acc[m.category] || []).push(m); return acc; }, {});

  if (loading) return <div className="empty"><div className="spinner" /></div>;

  return (
    <div>
      <div className="section-header">
        <div className="section-title">Project Memory ({memory.length} entries)</div>
        <span style={{ fontSize: 12, color: 'var(--text3)' }}>Claude automatically saves important context here</span>
      </div>
      {memory.length === 0 ? (
        <div className="empty">
          <div className="empty-icon">🧠</div>
          <h3>No memories yet</h3>
          <p>Claude will save important project knowledge as you chat</p>
        </div>
      ) : (
        Object.entries(grouped).map(([cat, items]) => (
          <div key={cat} style={{ marginBottom: 20 }}>
            <div style={{ fontSize: 11, fontWeight: 600, textTransform: 'uppercase', letterSpacing: 1, color: 'var(--text3)', marginBottom: 8 }}>{cat}</div>
            <div className="memory-list">
              {items.map(m => (
                <div key={m.id} className="memory-item">
                  <span className="memory-cat">{m.category}</span>
                  <div style={{ flex: 1 }}>
                    <div className="memory-key">{m.key}</div>
                    <div className="memory-val">{m.value}</div>
                    <div style={{ fontSize: 10, color: 'var(--text3)', marginTop: 4 }}>source: {m.source} · {new Date(m.updated_at).toLocaleString()}</div>
                  </div>
                  <button className="btn btn-danger btn-sm" onClick={() => del(m.id)}>×</button>
                </div>
              ))}
            </div>
          </div>
        ))
      )}
    </div>
  );
}

// ── Agent Tab ──────────────────────────────────────────────
function AgentTab({ project, showToast }) {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [triggering, setTriggering] = useState(false);
  const pollRef = useRef(null);

  useEffect(() => { load(); return () => clearInterval(pollRef.current); }, [project.id]);

  async function load() {
    try { setJobs(await getAgentJobs(project.id)); } catch (e) {}
    finally { setLoading(false); }
  }

  async function trigger() {
    setTriggering(true);
    try {
      const res = await triggerAgent(project.id);
      showToast('Agent started! Organizing your project knowledge...', 'success');
      load();
      // Poll for updates
      pollRef.current = setInterval(async () => {
        try {
          const status = await getAgentStatus(res.job_id);
          if (status.status === 'completed' || status.status === 'failed') {
            clearInterval(pollRef.current);
            load();
            showToast(status.status === 'completed' ? `✅ Agent done! Created ${status.result?.memories_created || 0} memory entries.` : `❌ Agent failed: ${status.error}`, status.status === 'completed' ? 'success' : 'error');
          }
        } catch {}
      }, 2000);
    } catch (e) {
      showToast('Error: ' + (e.response?.data?.detail || e.message), 'error');
    } finally { setTriggering(false); }
  }

  const statusColor = { pending: 'yellow', running: 'yellow', completed: 'green', failed: 'red' };

  return (
    <div>
      <div className="section-header">
        <div className="section-title">Background Agent</div>
      </div>
      <div className="card" style={{ marginBottom: 20 }}>
        <div style={{ fontWeight: 600, marginBottom: 8 }}>🤖 Knowledge Organization Agent</div>
        <p style={{ fontSize: 13, color: 'var(--text2)', marginBottom: 16, lineHeight: 1.6 }}>
          This agent reads all your project data — conversations, brief, images — and organizes everything into structured memory entries.
          Run it after a long chat session to make Claude smarter about your project.
        </p>
        <button className="btn btn-primary" onClick={trigger} disabled={triggering}>
          {triggering ? <><div className="spinner" style={{ width: 14, height: 14 }} />Starting...</> : '▶ Run Organization Agent'}
        </button>
      </div>

      <div className="section-header"><div className="section-title">Job History</div></div>
      {loading ? <div className="empty"><div className="spinner" /></div>
        : jobs.length === 0 ? <div style={{ color: 'var(--text3)', fontSize: 13 }}>No jobs run yet.</div>
        : jobs.map(j => (
          <div key={j.id} className="agent-card">
            <div className={`agent-status-dot ${j.status}`} />
            <div style={{ flex: 1 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ fontSize: 13, fontWeight: 500 }}>{j.status.charAt(0).toUpperCase() + j.status.slice(1)}</span>
                <span className={`badge badge-${statusColor[j.status]}`}>{j.status}</span>
              </div>
              {j.result && (
                <div style={{ fontSize: 12, color: 'var(--text2)', marginTop: 4 }}>
                  {j.result.memories_created} memories created · {j.result.messages_processed} messages processed
                </div>
              )}
              {j.error && <div style={{ fontSize: 12, color: 'var(--red)', marginTop: 4 }}>{j.error}</div>}
              <div style={{ fontSize: 11, color: 'var(--text3)', marginTop: 4 }}>{new Date(j.created_at).toLocaleString()}</div>
            </div>
          </div>
        ))}
    </div>
  );
}

// ── Overview Tab ───────────────────────────────────────────
function OverviewTab({ project }) {
  const brief = project.brief || {};
  const fields = [
    ['Name', project.name], ['Status', project.status],
    ['Description', project.description], ['Goals', project.goals],
    ['Tech Stack', brief.tech_stack], ['Deadline', brief.deadline],
    ...Object.entries(brief).filter(([k]) => !['tech_stack', 'deadline'].includes(k))
  ].filter(([, v]) => v);

  return (
    <div>
      <div className="section-header"><div className="section-title">Project Brief</div></div>
      <div className="card" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        {fields.map(([k, v]) => (
          <div key={k}>
            <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text3)', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 4 }}>{k}</div>
            <div style={{ fontSize: 14, color: 'var(--text)' }}>{String(v)}</div>
          </div>
        ))}
      </div>
      <div style={{ marginTop: 20, padding: 16, background: 'var(--bg3)', borderRadius: 10, border: '1px solid var(--border)' }}>
        <div style={{ fontSize: 12, color: 'var(--text3)', marginBottom: 8 }}>Project ID (for API calls)</div>
        <code style={{ fontSize: 12, color: 'var(--accent2)', fontFamily: 'JetBrains Mono, monospace' }}>{project.id}</code>
      </div>
    </div>
  );
}

// ── Main Page ──────────────────────────────────────────────
export default function ProjectPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [project, setProject] = useState(null);
  const [tab, setTab] = useState('chat');
  const [toast, setToast] = useState(null);

  useEffect(() => {
    getProject(id).then(setProject).catch(() => navigate('/'));
  }, [id]);

  function showToast(msg, type = 'success') {
    setToast({ msg, type });
  }

  if (!project) return <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh' }}><div className="spinner" /></div>;

  const tabs = [
    { id: 'chat', label: '💬 Chat' },
    { id: 'overview', label: '📋 Brief' },
    { id: 'images', label: '🎨 Images' },
    { id: 'memory', label: '🧠 Memory' },
    { id: 'agent', label: '🤖 Agent' },
  ];

  return (
    <div className="app-shell">
      <div className="main">
        <div className="topbar">
          <button onClick={() => navigate('/')} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text3)', fontSize: 18, marginRight: 4 }}>←</button>
          <h2>{project.name}</h2>
          <span className={`badge badge-${project.status === 'active' ? 'green' : 'yellow'}`}>{project.status}</span>
          <div className="topbar-tabs">
            {tabs.map(t => (
              <button key={t.id} className={`tab-btn ${tab === t.id ? 'active' : ''}`} onClick={() => setTab(t.id)}>{t.label}</button>
            ))}
          </div>
        </div>

        <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
          {tab === 'chat' ? (
            <div style={{ flex: 1, overflow: 'hidden' }}>
              <ChatTab project={project} />
            </div>
          ) : (
            <div className="content">
              {tab === 'overview' && <OverviewTab project={project} />}
              {tab === 'images' && <ImagesTab project={project} />}
              {tab === 'memory' && <MemoryTab project={project} />}
              {tab === 'agent' && <AgentTab project={project} showToast={showToast} />}
            </div>
          )}
        </div>
      </div>

      {toast && <Toast msg={toast.msg} type={toast.type} onClose={() => setToast(null)} />}
    </div>
  );
}
