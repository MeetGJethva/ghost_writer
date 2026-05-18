import React, { useState, useEffect, useRef } from 'react';
import { FileText, X, Plus } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import NotificationManager from './NotificationManager';
import Sidebar from './Sidebar';
import ChatArea from './ChatArea';

const API_BASE = 'http://localhost:3300/api';

export default function ChatInterface() {
  const [activeTab, setActiveTab] = useState('chats');
  const [activeConversationId, setActiveConversationId] = useState(null);
  const [selectedChange, setSelectedChange] = useState(null);
  const [conversationsTrigger, setConversationsTrigger] = useState(0);

  const [projects, setProjects] = useState([]);
  const [showCreateProject, setShowCreateProject] = useState(false);
  const [newProject, setNewProject] = useState({ name: '', description: '', keywords: '', folder_path: '' });

  const [tasks, setTasks] = useState([]);
  const [taskFilter, setTaskFilter] = useState('all'); // all, PENDING, PROCESSING, COMPLETED, FAILED
  const [isFetchingTasks, setIsFetchingTasks] = useState(false);

  const chatAreaRef = useRef(null);

  const fetchProjects = async () => {
    try {
      const res = await fetch(`${API_BASE}/projects`);
      const data = await res.json();
      setProjects(data);
    } catch (err) {
      console.error('Failed to fetch projects', err);
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
    fetchProjects();
  }, []);

  useEffect(() => {
    if (activeTab === 'tasks') {
      fetchTasks();
    }
  }, [activeTab]);

  const handleStartJiraTask = async (jiraTask) => {
    setActiveTab('chats');
    setActiveConversationId(null);

    const taskQuery = `Start working on Jira Task [${jiraTask.key}]: ${jiraTask.summary}\n\nDescription:\n${jiraTask.description}`;

    // Execute on a small delay to ensure state initialization
    setTimeout(() => {
      chatAreaRef.current?.handleSend(taskQuery, 'JIRA', true);
    }, 150);
  };

  const handleNewConversation = () => {
    setActiveConversationId(null);
    chatAreaRef.current?.clearMessages();
    setActiveTab('chats');
  };

  const handleActiveConversationDeleted = () => {
    setActiveConversationId(null);
    chatAreaRef.current?.clearMessages();
  };

  const handleConversationCreated = () => {
    setConversationsTrigger(prev => prev + 1);
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

      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        activeConversationId={activeConversationId}
        setActiveConversationId={setActiveConversationId}
        handleNewConversation={handleNewConversation}
        onActiveConversationDeleted={handleActiveConversationDeleted}
        projects={projects}
        setShowCreateProject={setShowCreateProject}
        handleDeleteProject={handleDeleteProject}
        tasks={tasks}
        taskFilter={taskFilter}
        setTaskFilter={setTaskFilter}
        fetchTasks={fetchTasks}
        isFetchingTasks={isFetchingTasks}
        conversationsTrigger={conversationsTrigger}
      />

      <ChatArea
        ref={chatAreaRef}
        activeTab={activeTab}
        activeConversationId={activeConversationId}
        setActiveConversationId={setActiveConversationId}
        projects={projects}
        handleDeleteProject={handleDeleteProject}
        tasks={tasks}
        taskFilter={taskFilter}
        setSelectedChange={setSelectedChange}
        onConversationCreated={handleConversationCreated}
      />

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
                    onChange={e => setNewProject({ ...newProject, name: e.target.value })}
                    placeholder="e.g., frontend-client"
                    style={{ background: 'rgba(0,0,0,0.2)', border: '1px solid var(--glass-border)', padding: '0.75rem', borderRadius: '10px', color: 'white', outline: 'none' }}
                  />
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  <label style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Folder Path * (Absolute Path)</label>
                  <input
                    type="text"
                    value={newProject.folder_path}
                    onChange={e => setNewProject({ ...newProject, folder_path: e.target.value })}
                    placeholder="/home/user/project"
                    style={{ background: 'rgba(0,0,0,0.2)', border: '1px solid var(--glass-border)', padding: '0.75rem', borderRadius: '10px', color: 'white', outline: 'none' }}
                  />
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  <label style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Description</label>
                  <textarea
                    value={newProject.description}
                    onChange={e => setNewProject({ ...newProject, description: e.target.value })}
                    placeholder="A brief summary of what this project does..."
                    style={{ background: 'rgba(0,0,0,0.2)', border: '1px solid var(--glass-border)', padding: '0.75rem', borderRadius: '10px', color: 'white', outline: 'none', resize: 'none', minHeight: '80px' }}
                  />
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  <label style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Keywords (Comma separated)</label>
                  <input
                    type="text"
                    value={newProject.keywords}
                    onChange={e => setNewProject({ ...newProject, keywords: e.target.value })}
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
      <NotificationManager onStartTask={handleStartJiraTask} />
    </div>
  );
}
