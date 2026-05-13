import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Bot, User, Code, FileText, Send, X, Smartphone, Plus, MessageSquare, Trash2, Folder, ChevronDown, ChevronRight, Layout, Activity, CheckCircle, Clock, AlertCircle, RefreshCw, ListTodo } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import MarkdownRenderer from './MarkdownRenderer';
import TasksView from './TasksView';

const API_BASE = 'http://localhost:3300/api';
const WS_BASE = 'ws://localhost:3300/ws';

export default function ChatInterface() {
  const [activeTab, setActiveTab] = useState('chats');
  const [conversations, setConversations] = useState([]);
  const [activeConversationId, setActiveConversationId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [viewFilter, setViewFilter] = useState('all');
  const [selectedChange, setSelectedChange] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [expandedResponses, setExpandedResponses] = useState({}); // map of msg.id -> bool

  const [projects, setProjects] = useState([]);
  const [showCreateProject, setShowCreateProject] = useState(false);
  const [newProject, setNewProject] = useState({ name: '', description: '', keywords: '', folder_path: '' });

  const [tasks, setTasks] = useState([]);
  const [taskFilter, setTaskFilter] = useState('all'); // all, PENDING, PROCESSING, COMPLETED, FAILED
  const [isFetchingTasks, setIsFetchingTasks] = useState(false);
  const [expandedTasks, setExpandedTasks] = useState({}); // map of task.task_id -> bool

  const messagesEndRef = useRef(null);
  const wsRef = useRef(null);

  const toggleResponse = (msgId) => {
    setExpandedResponses(prev => ({
      ...prev,
      [msgId]: !prev[msgId]
    }));
  };

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  const fetchConversations = async () => {
    try {
      const res = await fetch(`${API_BASE}/conversations`);
      const data = await res.json();
      setConversations(data);
    } catch (err) {
      console.error('Failed to fetch conversations', err);
    }
  };

  const fetchProjects = async () => {
    try {
      const res = await fetch(`${API_BASE}/projects`);
      const data = await res.json();
      setProjects(data);
    } catch (err) {
      console.error('Failed to fetch projects', err);
    }
  };

  const fetchHistory = async (convId) => {
    if (!convId) return;
    try {
      const res = await fetch(`${API_BASE}/conversations/${convId}/history`);
      const data = await res.json();
      setMessages(data);
    } catch (err) {
      console.error('Failed to fetch history', err);
    }
  };

  const fetchTasks = async () => {
    setIsFetchingTasks(true);
    try {
      const res = await fetch(`${API_BASE}/tasks`);
      const data = await res.json();
      setTasks(data);
    } catch (err) {
      console.error('Failed to fetch tasks', err);
    } finally {
      setIsFetchingTasks(false);
    }
  };

  useEffect(() => {
    fetchConversations();
    fetchProjects();
  }, []);

  useEffect(() => {
    if (activeTab === 'tasks') {
      fetchTasks();
    }
  }, [activeTab]);

  const toggleTaskExpand = (taskId) => {
    setExpandedTasks(prev => ({
      ...prev,
      [taskId]: !prev[taskId]
    }));
  };

  useEffect(() => {
    if (!activeConversationId) {
      setMessages([]);
      return;
    }

    fetchHistory(activeConversationId);

    const ws = new WebSocket(`${WS_BASE}/conversations/${activeConversationId}`);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'new_message') {
          setMessages(prev => {
            if (prev.some(m => m.id === data.message.id)) return prev;
            const cleaned = prev.filter(m => {
              if (m.id.startsWith('temp-') && m.message === data.message.message && !m.is_from_agent && !data.message.is_from_agent) {
                return false;
              }
              return true;
            });
            return [...cleaned, data.message];
          });
        }
      } catch (e) {
        console.error('WebSocket message parse error', e);
      }
    };

    return () => {
      ws.close();
      wsRef.current = null;
    };
  }, [activeConversationId]);

  const handleSend = async () => {
    if (!inputValue.trim() || isSubmitting) return;
    const query = inputValue;
    setInputValue('');
    setIsSubmitting(true);

    const tempMsg = {
      id: `temp-${Date.now()}`,
      is_from_agent: false,
      source: 'web',
      message: query,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      file_changes: []
    };
    setMessages(prev => [...prev, tempMsg]);

    try {
      const payload = {
        query: query,
        source_id: 'web-user',
        source: 'HTTP',
        metadata: {}
      };
      if (activeConversationId) {
        payload.conversation_id = activeConversationId;
      }

      const res = await fetch(`${API_BASE}/tasks`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (res.ok) {
        const taskData = await res.json();
        if (!activeConversationId && taskData.metadata?.conversation_id) {
          await fetchConversations();
          setActiveConversationId(taskData.metadata.conversation_id);
        }
      }
    } catch (err) {
      console.error('Failed to submit task', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleNewConversation = () => {
    setActiveConversationId(null);
    setMessages([]);
    setActiveTab('chats');
  };

  const handleDeleteConversation = async (e, convId) => {
    e.stopPropagation();
    if (!window.confirm('Are you sure you want to delete this conversation?')) return;
    try {
      const res = await fetch(`${API_BASE}/conversations/${convId}`, { method: 'DELETE' });
      if (res.ok) {
        if (activeConversationId === convId) {
          setActiveConversationId(null);
          setMessages([]);
        }
        setConversations(prev => prev.filter(c => c.id !== convId));
      }
    } catch (err) {
      console.error('Failed to delete conversation', err);
    }
  };

  const handleCreateProject = async () => {
    if (!newProject.name || !newProject.folder_path) return;
    try {
      const res = await fetch(`${API_BASE}/projects/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newProject)
      });
      if (res.ok) {
        await fetchProjects();
        setNewProject({ name: '', description: '', keywords: '', folder_path: '' });
        setShowCreateProject(false);
      } else {
        const err = await res.json();
        alert(err.detail || 'Failed to create project');
      }
    } catch (err) {
      console.error('Failed to create project', err);
    }
  };

  const handleDeleteProject = async (e, projectId) => {
    e.stopPropagation();
    if (!window.confirm('Are you sure you want to delete this project?')) return;
    try {
      const res = await fetch(`${API_BASE}/projects/${projectId}`, { method: 'DELETE' });
      if (res.ok) {
        setProjects(prev => prev.filter(p => p.id !== projectId));
      }
    } catch (err) {
      console.error('Failed to delete project', err);
    }
  };

  const filteredConversations = conversations.filter(c => {
    if (viewFilter === 'all') return true;
    return c.source === viewFilter;
  });

  const BackgroundOrbs = () => {
    const orbs = [
      { size: 600, color: '#3b82f6', x: [0, 300, -200, 0], y: [0, -300, 200, 0], delay: 0, duration: 20 },
      { size: 500, color: '#8b5cf6', x: [0, -250, 150, 0], y: [0, 300, -150, 0], delay: 2, duration: 25 },
      { size: 450, color: '#ec4899', x: [0, 200, -300, 0], y: [0, 150, -250, 0], delay: 5, duration: 22 },
      { size: 700, color: '#10b981', x: [0, -300, 250, 0], y: [0, -200, 150, 0], delay: 1, duration: 30 },
      { size: 400, color: '#f59e0b', x: [0, 150, -150, 0], y: [0, 200, -200, 0], delay: 3, duration: 18 }
    ];

    return (
      <div style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, overflow: 'hidden', zIndex: 0, pointerEvents: 'none' }}>
        <div className="liquid-bg" style={{ position: 'absolute', width: '100%', height: '100%' }}></div>
        {orbs.map((orb, i) => (
          <motion.div
            key={i}
            animate={{ x: orb.x, y: orb.y, scale: [1, 1.2, 0.9, 1] }}
            transition={{ duration: orb.duration, repeat: Infinity, repeatType: 'mirror', ease: 'easeInOut', delay: orb.delay }}
            style={{
              position: 'absolute', top: '50%', left: '50%',
              marginTop: -(orb.size / 2), marginLeft: -(orb.size / 2),
              width: orb.size, height: orb.size, borderRadius: '50%',
              background: orb.color, filter: 'blur(120px)', opacity: 0.45, mixBlendMode: 'screen'
            }}
          />
        ))}
      </div>
    );
  };


  return (
    <div className="app-container" style={{ position: 'relative', background: '#0a0f1d' }}>
      <BackgroundOrbs />

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

              <div style={{ marginTop: '1.5rem', marginBottom: '1rem' }}>
                <h3 style={{ fontSize: '0.85rem', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '0.75rem', letterSpacing: '0.05em' }}>View Mode</h3>
                <div className="toggle-group">
                  <button className={`toggle-btn ${viewFilter === 'all' ? 'active' : ''}`} onClick={() => setViewFilter('all')}>All</button>
                  <button className={`toggle-btn ${viewFilter === 'HTTP' ? 'active' : ''}`} onClick={() => setViewFilter('HTTP')}>Web</button>
                  <button className={`toggle-btn ${viewFilter === 'WHATSAPP' ? 'active' : ''}`} onClick={() => setViewFilter('WHATSAPP')}>WhatsApp</button>
                </div>
              </div>
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
              {conv.source === 'WHATSAPP' ? <Smartphone size={18} color="#22c55e" /> : <MessageSquare size={18} color="var(--accent-2)" />}
              <div style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden', flex: 1 }}>
                <span style={{ fontSize: '0.9rem', fontWeight: 500, whiteSpace: 'nowrap', textOverflow: 'ellipsis', overflow: 'hidden' }}>
                  {conv.source === 'WHATSAPP' ? conv.number : 'Web Session'}
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

      <div className="chat-area glass-panel" style={{ position: 'relative', zIndex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        <div className="chat-header">
          <div>
            <h1 style={{ fontSize: '1.25rem', fontWeight: 600 }}>
              {activeTab === 'projects' && 'Project Management'}
              {activeTab === 'chats' && (activeConversationId ? 'Project Chat' : 'New Conversation')}
              {activeTab === 'tasks' && 'Redis Task Monitor'}
            </h1>
            <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
              {activeTab === 'projects' && `${projects.length} registered projects`}
              {activeTab === 'chats' && `${messages.length} messages`}
              {activeTab === 'tasks' && `${tasks.length} total tasks tracked`}
            </span>
          </div>
        </div>

        {activeTab === 'chats' && (
          <>
            <div className="chat-messages">
              {messages.map((msg) => (
                <div key={msg.id} className={`message-wrapper ${msg.is_from_agent ? 'agent' : 'user'} ${msg.source === 'WHATSAPP' ? 'whatsapp' : ''}`}>
                  <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem' }}>
                    {msg.is_from_agent && (
                      <div style={{ marginTop: '0.25rem', color: 'var(--accent-1)' }}>
                        <Bot size={24} />
                      </div>
                    )}
                    <div style={{ display: 'flex', flexDirection: 'column', maxWidth: '100%' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                        <span>{msg.is_from_agent ? 'Agent' : 'You'}</span>
                        <span>&bull;</span>
                        <span>{msg.timestamp}</span>
                      </div>
                      <div className="message-bubble">
                        <MarkdownRenderer content={msg.message} />
                        
                        {msg.is_from_agent && msg.all_agent_responses && Object.keys(msg.all_agent_responses).length > 0 && (
                          <div style={{ marginTop: '1rem', borderTop: '1px solid rgba(255,255,255,0.1)', paddingTop: '0.75rem' }}>
                            <button 
                              onClick={() => toggleResponse(msg.id)}
                              style={{ 
                                background: 'rgba(255,255,255,0.05)', border: 'none', color: 'var(--text-muted)', 
                                padding: '0.5rem 0.75rem', borderRadius: '8px', cursor: 'pointer', fontSize: '0.8rem',
                                display: 'flex', alignItems: 'center', gap: '0.5rem', transition: 'all 0.2s'
                              }}
                            >
                              <Layout size={14} />
                              {expandedResponses[msg.id] ? 'Hide Agent Breakdown' : 'Show Agent Breakdown'}
                              {expandedResponses[msg.id] ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                            </button>

                            <AnimatePresence>
                              {expandedResponses[msg.id] && (
                                <motion.div 
                                  initial={{ height: 0, opacity: 0 }}
                                  animate={{ height: 'auto', opacity: 1 }}
                                  exit={{ height: 0, opacity: 0 }}
                                  style={{ overflow: 'hidden', marginTop: '0.75rem' }}
                                >
                                  <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', padding: '1rem', background: 'rgba(0,0,0,0.2)', borderRadius: '12px' }}>
                                    {Object.entries(msg.all_agent_responses).map(([agent, response], i) => (
                                      <div key={i} style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                                        <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--accent-2)', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                                          <Bot size={12} /> {agent}
                                        </div>
                                        <div style={{ fontSize: '0.85rem', color: '#cbd5e1', lineHeight: '1.6' }}>
                                          <MarkdownRenderer content={response} />
                                        </div>
                                      </div>
                                    ))}
                                  </div>
                                </motion.div>
                              )}
                            </AnimatePresence>
                          </div>
                        )}
                      </div>

                      {msg.file_changes && msg.file_changes.length > 0 && (
                        <button
                          className="review-change-btn"
                          onClick={() => setSelectedChange(msg.file_changes)}
                        >
                          <Code />
                          Review {msg.file_changes.length} Change{msg.file_changes.length !== 1 ? 's' : ''}
                        </button>
                      )}
                    </div>
                    {!msg.is_from_agent && (
                      <div style={{ marginTop: '0.25rem', color: msg.source === 'WHATSAPP' ? '#22c55e' : 'var(--text-muted)' }}>
                        <User size={24} />
                      </div>
                    )}
                  </div>
                </div>
              ))}
              {messages.length === 0 && (
                <div style={{ textAlign: 'center', marginTop: '4rem', color: 'var(--text-muted)' }}>
                  <Bot size={48} style={{ margin: '0 auto', marginBottom: '1rem', opacity: 0.5 }} />
                  <p>No messages yet. Send a task to start!</p>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            <div className="input-area">
              <textarea
                className="chat-input"
                placeholder="Type your task here..."
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSend();
                  }
                }}
                disabled={isSubmitting}
              />
              <button className="send-btn" onClick={handleSend} disabled={!inputValue.trim() || isSubmitting}>
                <Send size={18} />
              </button>
            </div>
          </>
        )}

        {activeTab === 'projects' && (
          <div className="project-grid" style={{ padding: '2rem', display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '1.5rem', overflowY: 'auto' }}>
            {projects.map(proj => (
              <div key={proj.id} className="project-card glass-panel" style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1rem', background: 'rgba(255,255,255,0.02)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div style={{ background: 'rgba(139, 92, 246, 0.1)', padding: '0.75rem', borderRadius: '12px' }}>
                    <Folder color="var(--accent-2)" size={24} />
                  </div>
                  <button onClick={(e) => handleDeleteProject(e, proj.id)} style={{ background: 'none', border: 'none', color: '#ef4444', cursor: 'pointer', padding: '0.5rem', borderRadius: '8px' }}>
                    <Trash2 size={20} />
                  </button>
                </div>
                <div>
                  <h3 style={{ fontSize: '1.1rem', fontWeight: 600, marginBottom: '0.5rem' }}>{proj.name}</h3>
                  <p style={{ fontSize: '0.9rem', color: 'var(--text-muted)', marginBottom: '1rem', lineHeight: 1.5 }}>
                    {proj.description || 'No description provided.'}
                  </p>
                </div>
                <div style={{ marginTop: 'auto', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.8rem', color: 'var(--text-muted)', background: 'rgba(0,0,0,0.2)', padding: '0.5rem 0.75rem', borderRadius: '8px' }}>
                    <Code size={14} />
                    <span style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>{proj.folder_path}</span>
                  </div>
                  {proj.keywords && (
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                      {proj.keywords.split(',').map((k, i) => (
                        <span key={i} style={{ fontSize: '0.7rem', background: 'rgba(59, 130, 246, 0.1)', color: 'var(--accent-1)', padding: '0.2rem 0.5rem', borderRadius: '4px' }}>
                          {k.trim()}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
            {projects.length === 0 && (
              <div style={{ gridColumn: '1/-1', textAlign: 'center', marginTop: '4rem', color: 'var(--text-muted)' }}>
                <Folder size={48} style={{ margin: '0 auto', marginBottom: '1rem', opacity: 0.5 }} />
                <p>No projects registered yet. Add one to get started!</p>
              </div>
            )}
          </div>
        )}

        {activeTab === 'tasks' && (
          <TasksView 
            tasks={tasks} 
            taskFilter={taskFilter} 
            expandedTasks={expandedTasks} 
            toggleTaskExpand={toggleTaskExpand} 
          />
        )}
      </div>

      <AnimatePresence>
        {selectedChange && (
          <motion.div className="modal-overlay" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={() => setSelectedChange(null)}>
            <motion.div className="modal-content" initial={{ scale: 0.95, y: 20 }} animate={{ scale: 1, y: 0 }} exit={{ scale: 0.95, y: 20 }} onClick={e => e.stopPropagation()}>
              <div className="modal-header">
                <div className="modal-title"><FileText color="var(--accent-1)" /> File Changes Meta Review</div>
                <button className="close-btn" onClick={() => setSelectedChange(null)}><X size={20} /></button>
              </div>
              <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', padding: '1.5rem', overflowY: 'auto' }}>
                <p style={{ marginBottom: '1.5rem', color: 'var(--text-muted)' }}>The agent updated these files. Look at the filesystem to review exact line changes.</p>
                <div style={{ display: 'grid', gap: '1rem' }}>
                  {selectedChange.map((change, idx) => (
                    <div key={idx} style={{ background: 'rgba(0,0,0,0.2)', padding: '1rem', borderRadius: '12px', border: '1px solid var(--glass-border)' }}>
                      <div style={{ fontWeight: 600, color: 'var(--accent-1)', marginBottom: '0.25rem' }}>{change.file_name}</div>
                      <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontFamily: 'monospace' }}>Hash: {change.hash}</div>
                    </div>
                  ))}
                </div>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {showCreateProject && (
          <motion.div className="modal-overlay" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={() => setShowCreateProject(false)}>
            <motion.div className="modal-content" style={{ maxWidth: '500px', height: 'auto' }} initial={{ scale: 0.95, y: 20 }} animate={{ scale: 1, y: 0 }} exit={{ scale: 0.95, y: 20 }} onClick={e => e.stopPropagation()}>
              <div className="modal-header">
                <div className="modal-title"><Plus color="var(--accent-2)" /> Register New Project</div>
                <button className="close-btn" onClick={() => setShowCreateProject(false)}><X size={20} /></button>
              </div>
              <div className="modal-body" style={{ padding: '2rem', display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  <label style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Project Name *</label>
                  <input 
                    type="text" 
                    value={newProject.name} 
                    onChange={e => setNewProject({...newProject, name: e.target.value})}
                    placeholder="e.g., frontend-client"
                    style={{ background: 'rgba(0,0,0,0.2)', border: '1px solid var(--glass-border)', padding: '0.75rem', borderRadius: '10px', color: 'white', outline: 'none' }}
                  />
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  <label style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Folder Path * (Absolute Path)</label>
                  <input 
                    type="text" 
                    value={newProject.folder_path} 
                    onChange={e => setNewProject({...newProject, folder_path: e.target.value})}
                    placeholder="/home/user/project"
                    style={{ background: 'rgba(0,0,0,0.2)', border: '1px solid var(--glass-border)', padding: '0.75rem', borderRadius: '10px', color: 'white', outline: 'none' }}
                  />
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  <label style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Description</label>
                  <textarea 
                    value={newProject.description} 
                    onChange={e => setNewProject({...newProject, description: e.target.value})}
                    placeholder="A brief summary of what this project does..."
                    style={{ background: 'rgba(0,0,0,0.2)', border: '1px solid var(--glass-border)', padding: '0.75rem', borderRadius: '10px', color: 'white', outline: 'none', resize: 'none', minHeight: '80px' }}
                  />
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  <label style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Keywords (Comma separated)</label>
                  <input 
                    type="text" 
                    value={newProject.keywords} 
                    onChange={e => setNewProject({...newProject, keywords: e.target.value})}
                    placeholder="react, tailwind, auth"
                    style={{ background: 'rgba(0,0,0,0.2)', border: '1px solid var(--glass-border)', padding: '0.75rem', borderRadius: '10px', color: 'white', outline: 'none' }}
                  />
                </div>
                <button 
                  onClick={handleCreateProject}
                  style={{ 
                    marginTop: '1rem', padding: '1rem', background: 'var(--accent-2)', color: 'white', 
                    border: 'none', borderRadius: '12px', fontWeight: 600, cursor: 'pointer'
                  }}
                >
                  Confirm Registration
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
