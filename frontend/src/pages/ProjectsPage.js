import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getProjects, createProject } from '../lib/api';

export default function ProjectsPage() {
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState({ name: '', description: '', goals: '', tech_stack: '', deadline: '' });
  const [creating, setCreating] = useState(false);
  const navigate = useNavigate();

  useEffect(() => { load(); }, []);

  async function load() {
    try { setProjects(await getProjects()); }
    catch (e) { console.error(e); }
    finally { setLoading(false); }
  }

  async function handleCreate(e) {
    e.preventDefault();
    if (!form.name.trim()) return;
    setCreating(true);
    try {
      const proj = await createProject({
        name: form.name, description: form.description, goals: form.goals,
        brief: { tech_stack: form.tech_stack, deadline: form.deadline }
      });
      setShowModal(false);
      setForm({ name: '', description: '', goals: '', tech_stack: '', deadline: '' });
      navigate(`/project/${proj.id}`);
    } catch (e) { alert('Error: ' + (e.response?.data?.detail || e.message)); }
    finally { setCreating(false); }
  }

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)' }}>
      <div style={{ borderBottom: '1px solid var(--border)', background: 'var(--bg2)', padding: '0 32px' }}>
        <div style={{ maxWidth: 900, margin: '0 auto', height: 64, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{ width: 36, height: 36, background: 'linear-gradient(135deg, #6c63ff, #a855f7)', borderRadius: 10, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 18 }}>🤖</div>
            <div>
              <div style={{ fontSize: 16, fontWeight: 700 }}>AI Project Assistant</div>
              <div style={{ fontSize: 11, color: 'var(--text3)' }}>Powered by Claude + Gemini</div>
            </div>
          </div>
          <button className="btn btn-primary" onClick={() => setShowModal(true)}>+ New Project</button>
        </div>
      </div>
      <div className="projects-page">
        <div className="page-header">
          <div>
            <div className="page-title">Your Projects</div>
            <div className="page-subtitle">{projects.length} project{projects.length !== 1 ? 's' : ''}</div>
          </div>
        </div>
        {loading ? <div className="empty"><div className="spinner" /></div>
          : projects.length === 0 ? (
            <div className="empty">
              <div className="empty-icon">🚀</div>
              <h3>No projects yet</h3>
              <p>Create your first project to start chatting with your AI assistant</p>
              <button className="btn btn-primary" style={{ marginTop: 8 }} onClick={() => setShowModal(true)}>Create Project</button>
            </div>
          ) : (
            <div className="card-grid">
              {projects.map(p => (
                <div key={p.id} className="project-card" onClick={() => navigate(`/project/${p.id}`)}>
                  <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 8 }}>
                    <h3>{p.name}</h3>
                    <span className={`badge badge-${p.status === 'active' ? 'green' : p.status === 'completed' ? 'purple' : 'yellow'}`}>{p.status}</span>
                  </div>
                  {p.description && <p>{p.description}</p>}
                  {p.goals && <p style={{ color: 'var(--text3)', fontSize: 12 }}>🎯 {p.goals}</p>}
                  <div className="project-card-meta">
                    {p.brief?.tech_stack && <span style={{ fontSize: 11, color: 'var(--text3)', background: 'var(--bg3)', padding: '2px 8px', borderRadius: 10 }}>{p.brief.tech_stack}</span>}
                    {p.brief?.deadline && <span style={{ fontSize: 11, color: 'var(--text3)' }}>📅 {p.brief.deadline}</span>}
                    <span style={{ fontSize: 11, color: 'var(--text3)', marginLeft: 'auto' }}>{new Date(p.created_at).toLocaleDateString()}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
      </div>
      {showModal && (
        <div className="modal-overlay" onClick={e => e.target === e.currentTarget && setShowModal(false)}>
          <div className="modal">
            <div className="modal-title">✨ Create New Project</div>
            <form onSubmit={handleCreate}>
              <div className="form-group">
                <label className="form-label">Project Name *</label>
                <input className="input" placeholder="My Awesome Project" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} autoFocus />
              </div>
              <div className="form-group">
                <label className="form-label">Description</label>
                <textarea className="textarea" placeholder="What is this project about?" value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} style={{ minHeight: 70 }} />
              </div>
              <div className="form-group">
                <label className="form-label">Goals</label>
                <input className="input" placeholder="What do you want to achieve?" value={form.goals} onChange={e => setForm(f => ({ ...f, goals: e.target.value }))} />
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                <div className="form-group">
                  <label className="form-label">Tech Stack</label>
                  <input className="input" placeholder="React, Python..." value={form.tech_stack} onChange={e => setForm(f => ({ ...f, tech_stack: e.target.value }))} />
                </div>
                <div className="form-group">
                  <label className="form-label">Deadline</label>
                  <input className="input" type="date" value={form.deadline} onChange={e => setForm(f => ({ ...f, deadline: e.target.value }))} />
                </div>
              </div>
              <div className="modal-actions">
                <button type="button" className="btn btn-secondary" onClick={() => setShowModal(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary" disabled={creating || !form.name.trim()}>
                  {creating ? <><div className="spinner" style={{ width: 14, height: 14 }} />Creating...</> : 'Create Project'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
