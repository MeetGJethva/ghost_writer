import React, { useState, useEffect, useRef, useCallback, useImperativeHandle, forwardRef } from 'react';
import { 
  Bot, FileText, X, Paperclip, Send, User, Briefcase, 
  ChevronDown, ChevronRight, Layout, Code, Folder, Trash2, RefreshCw
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import MarkdownRenderer from './MarkdownRenderer';
import TasksView from './TasksView';

const API_BASE = 'http://localhost:3300/api';
const WS_BASE = 'ws://localhost:3300/ws';

const ChatArea = forwardRef(({
  activeTab,
  activeConversationId,
  setActiveConversationId,
  projects,
  handleDeleteProject,
  tasks,
  taskFilter,
  setSelectedChange,
  onConversationCreated
}, ref) => {
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [expandedResponses, setExpandedResponses] = useState({});
  const [attachedFile, setAttachedFile] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [expandedTasks, setExpandedTasks] = useState({});

  const messagesEndRef = useRef(null);
  const wsRef = useRef(null);
  const fileInputRef = useRef(null);

  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    setIsUploading(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch(`${API_BASE}/upload`, {
        method: 'POST',
        body: formData
      });
      if (res.ok) {
        const data = await res.json();
        setAttachedFile({
          path: data.file_path,
          name: data.file_name
        });
      } else {
        console.error('Failed to upload file');
        alert('Failed to upload file');
      }
    } catch (err) {
      console.error('Error uploading file:', err);
      alert('Error uploading file: ' + err.message);
    } finally {
      setIsUploading(false);
      if (event.target) {
        event.target.value = ''; // clear file input
      }
    }
  };

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

  const toggleTaskExpand = (taskId) => {
    setExpandedTasks(prev => ({
      ...prev,
      [taskId]: !prev[taskId]
    }));
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

  const handleSend = async (customQuery = null, customSource = 'HTTP', forceNewConversation = false) => {
    let query = customQuery !== null ? customQuery : inputValue;
    if (!query.trim() && !attachedFile) return;
    if (isSubmitting) return;

    if (!query.trim() && attachedFile) {
      query = "Analyze the attached file.";
    }

    if (customQuery === null) setInputValue('');
    setIsSubmitting(true);

    // Format local temporary message to show attachment if present
    let localMsgText = query;
    if (attachedFile && customSource !== 'JIRA') {
      localMsgText = `📎 **[Attached File: ${attachedFile.name}]**\n\n${query}`;
    }

    const tempMsg = {
      id: `temp-${Date.now()}`,
      is_from_agent: false,
      source: customSource === 'JIRA' ? 'jira' : (customSource === 'WHATSAPP' ? 'whatsapp' : 'web'),
      message: localMsgText,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      file_changes: []
    };

    if (forceNewConversation) {
      setMessages([tempMsg]);
    } else {
      setMessages(prev => [...prev, tempMsg]);
    }

    try {
      const payload = {
        query: query,
        source_id: customSource === 'JIRA' ? 'jira-system' : 'web-user',
        source: customSource,
        metadata: attachedFile ? {
          file_path: attachedFile.path,
          file_name: attachedFile.name
        } : {}
      };

      const effectiveConvId = forceNewConversation ? null : activeConversationId;
      if (effectiveConvId) {
        payload.conversation_id = effectiveConvId;
      }

      const res = await fetch(`${API_BASE}/tasks`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (res.ok) {
        const taskData = await res.json();
        setAttachedFile(null); // Clear attached file on success
        if (onConversationCreated) {
          onConversationCreated();
        }
        if (taskData.metadata?.conversation_id) {
          setActiveConversationId(taskData.metadata.conversation_id);
        }
      }
    } catch (err) {
      console.error('Failed to submit task', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  useImperativeHandle(ref, () => ({
    handleSend: (customQuery = null, customSource = 'HTTP', forceNewConversation = false) => {
      handleSend(customQuery, customSource, forceNewConversation);
    },
    clearMessages: () => {
      setMessages([]);
    }
  }));

  return (
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
              <div key={msg.id} className={`message-wrapper ${msg.is_from_agent ? 'agent' : 'user'} ${msg.source === 'WHATSAPP' || msg.source === 'whatsapp' ? 'whatsapp' : (msg.source === 'JIRA' || msg.source === 'jira' ? 'jira' : '')}`}>
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
                    <div style={{ marginTop: '0.25rem', color: (msg.source === 'WHATSAPP' || msg.source === 'whatsapp') ? '#22c55e' : (msg.source === 'JIRA' || msg.source === 'jira' ? '#3b82f6' : 'var(--text-muted)') }}>
                      {msg.source === 'JIRA' || msg.source === 'jira' ? <Briefcase size={24} /> : <User size={24} />}
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

          {attachedFile && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', background: 'rgba(255,255,255,0.05)', border: '1px solid var(--glass-border)', padding: '0.6rem 1rem', borderRadius: '12px', marginBottom: '0.75rem', backdropFilter: 'blur(10px)' }}>
              <FileText size={18} color="var(--accent-1)" />
              <span style={{ fontSize: '0.85rem', color: 'white', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontWeight: 500 }}>
                {attachedFile.name}
              </span>
              <button onClick={() => setAttachedFile(null)} style={{ background: 'rgba(255,255,255,0.1)', border: 'none', color: '#cbd5e1', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', width: '24px', height: '24px', borderRadius: '50%', transition: 'all 0.2s' }} title="Remove attachment">
                <X size={14} />
              </button>
            </div>
          )}

          {isUploading && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.5rem', fontSize: '0.8rem', color: 'var(--accent-1)', marginBottom: '0.5rem' }}>
              <RefreshCw size={14} className="spin-animation" />
              <span style={{ fontWeight: 500 }}>Uploading file...</span>
            </div>
          )}

          <div className="input-area" style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', background: 'rgba(255,255,255,0.02)', padding: '0.5rem', borderRadius: '16px', border: '1px solid var(--glass-border)' }}>
            <input
              type="file"
              ref={fileInputRef}
              style={{ display: 'none' }}
              onChange={handleFileUpload}
              accept=".pdf,.png,.jpg,.jpeg"
            />
            <button
              type="button"
              className="send-btn"
              onClick={() => fileInputRef.current?.click()}
              disabled={isUploading || isSubmitting}
              style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid var(--glass-border)', color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center', width: '42px', height: '42px', minWidth: '42px', borderRadius: '12px', cursor: 'pointer', transition: 'all 0.2s' }}
              title="Attach PDF or image"
            >
              <Paperclip size={18} />
            </button>
            <textarea
              className="chat-input"
              placeholder="Type your task or instructions here..."
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
              disabled={isSubmitting || isUploading}
              style={{ flex: 1, border: 'none', background: 'transparent', outline: 'none', color: 'white', resize: 'none', minHeight: '42px', maxHeight: '120px', padding: '0.5rem 0.25rem', fontSize: '0.95rem' }}
            />
            <button className="send-btn" onClick={handleSend} disabled={(!inputValue.trim() && !attachedFile) || isSubmitting || isUploading} style={{ width: '42px', height: '42px', minWidth: '42px', borderRadius: '12px' }}>
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
  );
});

export default ChatArea;
