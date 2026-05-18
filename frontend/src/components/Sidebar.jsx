import React, { useState, useEffect } from 'react';
import { 
  Bot, Plus, MessageSquare, Folder, Activity, RefreshCw, 
  Smartphone, Briefcase, Trash2, CheckCircle, AlertCircle, Clock 
} from 'lucide-react';
import ViewModeSelector from './ViewModeSelector';

const API_BASE = 'http://localhost:3300/api';

export default function Sidebar({
  activeTab,
  setActiveTab,
  activeConversationId,
  setActiveConversationId,
  handleNewConversation,
  onActiveConversationDeleted,
  projects,
  setShowCreateProject,
  handleDeleteProject,
  tasks,
  taskFilter,
  setTaskFilter,
  fetchTasks,
  isFetchingTasks,
  conversationsTrigger
}) {
  const [conversations, setConversations] = useState([]);
  const [viewFilter, setViewFilter] = useState('all');

  const fetchConversations = async () => {
    try {
      const res = await fetch(`${API_BASE}/conversations`);
      const data = await res.json();
      setConversations(data);
    } catch (err) {
      console.error('Failed to fetch conversations', err);
    }
  };

  useEffect(() => {
    fetchConversations();
  }, [conversationsTrigger]);

  const handleDeleteConversation = async (e, convId) => {
    e.stopPropagation();
    if (!window.confirm('Are you sure you want to delete this conversation?')) return;
    try {
      const res = await fetch(`${API_BASE}/conversations/${convId}`, { method: 'DELETE' });
      if (res.ok) {
        if (activeConversationId === convId) {
          onActiveConversationDeleted();
        }
        setConversations(prev => prev.filter(c => c.id !== convId));
      }
    } catch (err) {
      console.error('Failed to delete conversation', err);
    }
  };

  const filteredConversations = conversations.filter(c => {
    if (viewFilter === 'all') return true;
    return c.source === viewFilter;
  });

  return (
    <div className="sidebar glass-panel" style={{ overflowY: 'hidden', display: 'flex', flexDirection: 'column', position: 'relative', zIndex: 1 }}>
      <div>
        <h2 style={{ fontSize: '1.25rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
          <Bot color="var(--accent-2)" />
          Orchestrator
        </h2>

        <div className="tab-switcher" style={{ display: 'flex', gap: '0.35rem', marginBottom: '1rem', background: 'rgba(0,0,0,0.2)', padding: '4px', borderRadius: '12px' }}>
          <button
            onClick={() => setActiveTab('chats')}
            style={{
              flex: 1, padding: '0.5rem 0.25rem', borderRadius: '8px', border: 'none',
              background: activeTab === 'chats' ? 'rgba(255,255,255,0.1)' : 'transparent',
              color: activeTab === 'chats' ? 'white' : 'var(--text-muted)', cursor: 'pointer',
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.3rem', fontSize: '0.8rem'
            }}
          >
            <MessageSquare size={14} /> Chats
          </button>
          <button
            onClick={() => setActiveTab('projects')}
            style={{
              flex: 1, padding: '0.5rem 0.25rem', borderRadius: '8px', border: 'none',
              background: activeTab === 'projects' ? 'rgba(255,255,255,0.1)' : 'transparent',
              color: activeTab === 'projects' ? 'white' : 'var(--text-muted)', cursor: 'pointer',
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.3rem', fontSize: '0.8rem'
            }}
          >
            <Folder size={14} /> Projects
          </button>
          <button
            onClick={() => setActiveTab('tasks')}
            style={{
              flex: 1, padding: '0.5rem 0.25rem', borderRadius: '8px', border: 'none',
              background: activeTab === 'tasks' ? 'rgba(255,255,255,0.1)' : 'transparent',
              color: activeTab === 'tasks' ? 'white' : 'var(--text-muted)', cursor: 'pointer',
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.3rem', fontSize: '0.8rem'
            }}
          >
            <Activity size={14} /> Tasks
          </button>
        </div>

        {activeTab === 'chats' && (
          <>
            <button
              onClick={handleNewConversation}
              style={{
                width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem',
                padding: '0.75rem', background: 'var(--accent-1)', color: 'white', border: 'none',
                borderRadius: '12px', cursor: 'pointer', fontWeight: 500, fontSize: '0.95rem', transition: 'background 0.2s'
              }}
            >
              <Plus size={18} />
              New Conversation
            </button>

            <ViewModeSelector
              currentFilter={viewFilter}
              onChange={setViewFilter}
            />
          </>
        )}

        {activeTab === 'projects' && (
          <button
            onClick={() => setShowCreateProject(true)}
            style={{
              width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem',
              padding: '0.75rem', background: 'var(--accent-2)', color: 'white', border: 'none',
              borderRadius: '12px', cursor: 'pointer', fontWeight: 500, fontSize: '0.95rem', transition: 'background 0.2s'
            }}
          >
            <Plus size={18} />
            Register Project
          </button>
        )}

        {activeTab === 'tasks' && (
          <>
            <button
              onClick={fetchTasks}
              disabled={isFetchingTasks}
              style={{
                width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem',
                padding: '0.75rem', background: 'var(--accent-1)', color: 'white', border: 'none',
                borderRadius: '12px', cursor: 'pointer', fontWeight: 500, fontSize: '0.95rem', transition: 'background 0.2s',
                opacity: isFetchingTasks ? 0.7 : 1
              }}
            >
              <RefreshCw size={16} className={isFetchingTasks ? 'spin-animation' : ''} />
              Refresh Tracker
            </button>

            <div style={{ marginTop: '1.5rem', marginBottom: '1rem' }}>
              <h3 style={{ fontSize: '0.85rem', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '0.75rem', letterSpacing: '0.05em' }}>Status Filter</h3>
              <div className="toggle-group">
                <button className={`toggle-btn ${taskFilter === 'all' ? 'active' : ''}`} onClick={() => setTaskFilter('all')}>All</button>
                <button className={`toggle-btn ${taskFilter === 'PENDING' ? 'active' : ''}`} onClick={() => setTaskFilter('PENDING')}>Pending</button>
                <button className={`toggle-btn ${taskFilter === 'COMPLETED' ? 'active' : ''}`} onClick={() => setTaskFilter('COMPLETED')}>Done</button>
              </div>
            </div>
          </>
        )}
      </div>

      <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '0.5rem' }} className="chat-messages">
        {activeTab === 'chats' && filteredConversations.map(conv => (
          <div
            key={conv.id}
            onClick={() => setActiveConversationId(conv.id)}
            className="conversation-item"
            style={{
              padding: '0.75rem 1rem', borderRadius: '12px',
              background: activeConversationId === conv.id ? 'rgba(59, 130, 246, 0.2)' : 'transparent',
              border: activeConversationId === conv.id ? '1px solid rgba(59, 130, 246, 0.4)' : '1px solid transparent',
              cursor: 'pointer', transition: 'all 0.2s', display: 'flex', alignItems: 'center', gap: '0.75rem',
              position: 'relative'
            }}
          >
            {conv.source === 'WHATSAPP' ? <Smartphone size={18} color="#22c55e" /> : conv.source === 'JIRA' ? <Briefcase size={18} color="#3b82f6" /> : <MessageSquare size={18} color="var(--accent-2)" />}
            <div style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden', flex: 1 }}>
              <span style={{ fontSize: '0.9rem', fontWeight: 500, whiteSpace: 'nowrap', textOverflow: 'ellipsis', overflow: 'hidden' }}>
                {conv.source === 'WHATSAPP' ? conv.number : conv.source === 'JIRA' ? 'Jira Task' : 'Web Session'}
              </span>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                {conv.id.substring(0, 8)}...
              </span>
            </div>
            <button
              onClick={(e) => handleDeleteConversation(e, conv.id)}
              className="delete-conv-btn"
              style={{
                background: 'none', border: 'none', color: 'var(--text-muted)',
                cursor: 'pointer', padding: '4px', borderRadius: '4px',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                transition: 'color 0.2s, background 0.2s'
              }}
            >
              <Trash2 size={16} />
            </button>
          </div>
        ))}

        {activeTab === 'projects' && projects.map(proj => (
          <div
            key={proj.id}
            className="conversation-item"
            style={{
              padding: '0.75rem 1rem', borderRadius: '12px',
              background: 'rgba(255,255,255,0.03)',
              border: '1px solid var(--glass-border)',
              cursor: 'default', transition: 'all 0.2s', display: 'flex', alignItems: 'center', gap: '0.75rem',
              position: 'relative'
            }}
          >
            <Folder size={18} color="var(--accent-2)" />
            <div style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden', flex: 1 }}>
              <span style={{ fontSize: '0.9rem', fontWeight: 500, whiteSpace: 'nowrap', textOverflow: 'ellipsis', overflow: 'hidden' }}>
                {proj.name}
              </span>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', whiteSpace: 'nowrap', textOverflow: 'ellipsis', overflow: 'hidden' }}>
                {proj.folder_path}
              </span>
            </div>
            <button
              onClick={(e) => handleDeleteProject(e, proj.id)}
              className="delete-conv-btn"
              style={{
                background: 'none', border: 'none', color: 'var(--text-muted)',
                cursor: 'pointer', padding: '4px', borderRadius: '4px',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                transition: 'color 0.2s, background 0.2s'
              }}
            >
              <Trash2 size={16} />
            </button>
          </div>
        ))}

        {activeTab === 'tasks' && tasks
          .filter(t => {
            if (taskFilter === 'all') return true;
            if (taskFilter === 'PENDING') return t.status === 'PENDING' || t.status === 'PROCESSING';
            if (taskFilter === 'COMPLETED') return t.status === 'COMPLETED' || t.status === 'FAILED';
            return t.status === taskFilter;
          })
          .map(task => {
            const isDone = task.status === 'COMPLETED' || task.status === 'FAILED';
            return (
              <div
                key={task.task_id}
                className="conversation-item"
                style={{
                  padding: '0.75rem 1rem', borderRadius: '12px',
                  background: 'rgba(255,255,255,0.03)',
                  border: '1px solid var(--glass-border)',
                  cursor: 'default', display: 'flex', alignItems: 'center', gap: '0.75rem',
                }}
              >
                {task.status === 'COMPLETED' && <CheckCircle size={16} color="#10b981" />}
                {task.status === 'FAILED' && <AlertCircle size={16} color="#ef4444" />}
                {task.status === 'PENDING' && <Clock size={16} color="#3b82f6" />}
                {task.status === 'PROCESSING' && <RefreshCw size={16} color="#f59e0b" className="spin-animation" />}

                <div style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden', flex: 1 }}>
                  <span style={{ fontSize: '0.85rem', fontWeight: 500, whiteSpace: 'nowrap', textOverflow: 'ellipsis', overflow: 'hidden', color: isDone ? '#94a3b8' : '#f8fafc' }}>
                    {task.user_query}
                  </span>
                  <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                    {new Date(task.arrival_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} &middot; <span style={{ textTransform: 'uppercase', fontSize: '0.65rem', color: task.status === 'COMPLETED' ? '#10b981' : task.status === 'FAILED' ? '#ef4444' : '#3b82f6' }}>{task.status}</span>
                  </span>
                </div>
              </div>
            );
          })
        }
      </div>
    </div>
  );
}
