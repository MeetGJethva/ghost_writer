import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Bot, User, Code, FileText, Send, X, Smartphone, Plus, MessageSquare } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const API_BASE = 'http://localhost:3300/api';
const WS_BASE = 'ws://localhost:3300/ws';

export default function ChatInterface() {
  const [conversations, setConversations] = useState([]);
  const [activeConversationId, setActiveConversationId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [viewFilter, setViewFilter] = useState('all');
  const [selectedChange, setSelectedChange] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const messagesEndRef = useRef(null);
  const wsRef = useRef(null);

  // Auto-scroll to bottom when messages change
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  // Fetch conversations list (one-time + on new conversation creation)
  const fetchConversations = async () => {
    try {
      const res = await fetch(`${API_BASE}/conversations`);
      const data = await res.json();
      setConversations(data);
    } catch (err) {
      console.error('Failed to fetch conversations', err);
    }
  };

  // Fetch full history once when switching conversations
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

  // Load conversations on mount
  useEffect(() => {
    fetchConversations();
  }, []);

  // When active conversation changes: fetch history once + open WebSocket
  useEffect(() => {
    if (!activeConversationId) {
      setMessages([]);
      return;
    }

    fetchHistory(activeConversationId);

    // Open WebSocket connection
    const ws = new WebSocket(`${WS_BASE}/conversations/${activeConversationId}`);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      console.log("event", event)
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'new_message') {
          setMessages(prev => {
            // Avoid duplicates (check id)
            if (prev.some(m => m.id === data.message.id)) return prev;
            // Remove any temp messages that match the content (optimistic update cleanup)
            const cleaned = prev.filter(m => {
              if (m.id.startsWith('temp-') && m.message === data.message.message && !m.is_from_agent && !data.message.is_from_agent) {
                return false;
              }
              return true;
            });
            return [...cleaned, data.message];
          });
        } else if (data.type === 'new_conversation') {
          fetchConversations();
        }
      } catch (e) {
        console.error('WebSocket message parse error', e);
      }
    };

    ws.onclose = () => {
      console.log('WebSocket closed for conversation', activeConversationId);
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

    // Optimistically add the user message (will be cleaned up when WS confirms)
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
        // If this was a brand-new conversation, update our state
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

      {/* Sidebar */}
      <div className="sidebar glass-panel" style={{ overflowY: 'hidden', display: 'flex', flexDirection: 'column', position: 'relative', zIndex: 1 }}>
        <div>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Bot color="var(--accent-2)" />
            Orchestrator
          </h2>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginBottom: '1rem' }}>
            Manage your AI tasks and review code changes seamlessly.
          </p>

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
              <button className={`toggle-btn ${viewFilter === 'http' ? 'active' : ''}`} onClick={() => setViewFilter('http')}>Web</button>
              <button className={`toggle-btn ${viewFilter === 'whatsapp' ? 'active' : ''}`} onClick={() => setViewFilter('whatsapp')}>WhatsApp</button>
            </div>
          </div>
        </div>

        {/* Conversation List */}
        <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '0.5rem' }} className="chat-messages">
          {filteredConversations.map(conv => (
            <div
              key={conv.id}
              onClick={() => setActiveConversationId(conv.id)}
              style={{
                padding: '0.75rem 1rem', borderRadius: '12px',
                background: activeConversationId === conv.id ? 'rgba(59, 130, 246, 0.2)' : 'transparent',
                border: activeConversationId === conv.id ? '1px solid rgba(59, 130, 246, 0.4)' : '1px solid transparent',
                cursor: 'pointer', transition: 'all 0.2s', display: 'flex', alignItems: 'center', gap: '0.75rem'
              }}
            >
              {conv.source === 'whatsapp' ? <Smartphone size={18} color="#22c55e" /> : <MessageSquare size={18} color="var(--accent-2)" />}
              <div style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
                <span style={{ fontSize: '0.9rem', fontWeight: 500, whiteSpace: 'nowrap', textOverflow: 'ellipsis', overflow: 'hidden' }}>
                  {conv.source === 'whatsapp' ? conv.number : 'Web Session'}
                </span>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  {conv.id.substring(0, 8)}...
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="chat-area glass-panel" style={{ position: 'relative', zIndex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        <div className="chat-header">
          <div>
            <h1 style={{ fontSize: '1.25rem', fontWeight: 600 }}>
              {activeConversationId ? 'Project Chat' : 'New Conversation'}
            </h1>
            <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
              {messages.length} messages
            </span>
          </div>
        </div>

        <div className="chat-messages">
          {messages.map((msg) => (
            <div key={msg.id} className={`message-wrapper ${msg.is_from_agent ? 'agent' : 'user'} ${msg.source === 'whatsapp' ? 'whatsapp' : ''}`}>
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem' }}>
                {msg.is_from_agent && (
                  <div style={{ marginTop: '0.25rem', color: 'var(--accent-1)' }}>
                    <Bot size={24} />
                  </div>
                )}
                <div style={{ display: 'flex', flexDirection: 'column' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                    <span>{msg.is_from_agent ? 'Agent' : 'You'}</span>
                    <span>&bull;</span>
                    <span>{msg.timestamp}</span>
                    {msg.source === 'whatsapp' && (
                      <>
                        <span>&bull;</span>
                        <Smartphone size={12} color="#22c55e" />
                        <span style={{ color: '#22c55e' }}>WhatsApp</span>
                      </>
                    )}
                  </div>
                  <div className="message-bubble" style={{ whiteSpace: 'pre-wrap' }}>
                    {msg.message}
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
                  <div style={{ marginTop: '0.25rem', color: msg.source === 'whatsapp' ? '#22c55e' : 'var(--text-muted)' }}>
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

        {/* Chat Input */}
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
      </div>

      {/* Review Changes Modal */}
      <AnimatePresence>
        {selectedChange && (
          <motion.div
            className="modal-overlay"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setSelectedChange(null)}
          >
            <motion.div
              className="modal-content"
              initial={{ scale: 0.95, y: 20 }}
              animate={{ scale: 1, y: 0 }}
              exit={{ scale: 0.95, y: 20 }}
              onClick={e => e.stopPropagation()}
            >
              <div className="modal-header">
                <div className="modal-title">
                  <FileText color="var(--accent-1)" />
                  File Changes Meta Review
                </div>
                <button className="close-btn" onClick={() => setSelectedChange(null)}>
                  <X size={20} />
                </button>
              </div>
              <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', padding: '1.5rem', overflowY: 'auto' }}>
                <p style={{ marginBottom: '1.5rem', color: 'var(--text-muted)' }}>
                  The agent updated these files. Look at the filesystem to review exact line changes.
                </p>
                <div style={{ display: 'grid', gap: '1rem' }}>
                  {selectedChange.map((change, idx) => (
                    <div key={idx} style={{ background: 'rgba(0,0,0,0.2)', padding: '1rem', borderRadius: '12px', border: '1px solid var(--glass-border)' }}>
                      <div style={{ fontWeight: 600, color: 'var(--accent-1)', marginBottom: '0.25rem' }}>
                        {change.file_name}
                      </div>
                      <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontFamily: 'monospace' }}>
                        Hash: {change.hash}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
