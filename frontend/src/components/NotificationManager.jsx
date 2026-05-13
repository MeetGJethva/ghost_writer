import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Bell, X, PlayCircle, ExternalLink } from 'lucide-react';

const API_BASE = 'http://localhost:3300/api';

export default function NotificationManager({ onStartTask }) {
  const [notifications, setNotifications] = useState([]);

  useEffect(() => {
    // Setup Server-Sent Events listener
    const eventSource = new EventSource(`${API_BASE}/notifications/sse`);

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data && data.key) {
          const newNotification = {
            id: `${data.key}-${Date.now()}`,
            ...data,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          };
          
          setNotifications((prev) => [newNotification, ...prev]);
          
          // Play sound if supported
          try {
            const audio = new Audio('https://assets.mixkit.co/active_storage/sfx/2869/2869-preview.mp3');
            audio.volume = 0.3;
            audio.play();
          } catch (e) {
            // Ignore browser auto-play block issues
          }
        }
      } catch (err) {
        console.error("Failed to parse notification JSON", err);
      }
    };

    eventSource.onerror = (error) => {
      console.error("EventSource connection error. Retrying...", error);
    };

    return () => {
      eventSource.close();
    };
  }, []);

  const removeNotification = (id) => {
    setNotifications((prev) => prev.filter((n) => n.id !== id));
  };

  const handleStartTask = (task) => {
    // Propagate to callback
    onStartTask(task);
    // Remove this notification
    removeNotification(task.id);
  };

  return (
    <div className="notification-container">
      <AnimatePresence>
        {notifications.map((notif) => (
          <motion.div
            key={notif.id}
            initial={{ opacity: 0, y: -20, scale: 0.95, filter: 'blur(8px)' }}
            animate={{ opacity: 1, y: 0, scale: 1, filter: 'blur(0px)' }}
            exit={{ opacity: 0, scale: 0.9, filter: 'blur(4px)', transition: { duration: 0.2 } }}
            layout
            className="notification-toast"
          >
            <div className="notification-header">
              <div style={{ 
                background: 'rgba(59, 130, 246, 0.15)', 
                padding: '8px', 
                borderRadius: '10px',
                color: 'var(--accent-1)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}>
                <Bell size={18} className="pulse-animation" />
              </div>
              <div className="notification-title" style={{ display: 'flex', flexDirection: 'column' }}>
                <span style={{ fontWeight: 650 }}>New Jira Task</span>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 400 }}>{notif.key} • {notif.timestamp}</span>
              </div>
              <button className="notification-close" onClick={() => removeNotification(notif.id)}>
                <X size={16} />
              </button>
            </div>

            <div className="notification-body">
              <strong style={{ color: 'white', display: 'block', marginBottom: '4px' }}>{notif.summary}</strong>
              {notif.description}
            </div>

            <div style={{ display: 'flex', gap: '8px', marginTop: '4px' }}>
              <button 
                className="notification-action-btn"
                onClick={() => handleStartTask(notif)}
              >
                <PlayCircle size={16} />
                Start with this task
              </button>
              {notif.url && (
                <a 
                  href={notif.url} 
                  target="_blank" 
                  rel="noopener noreferrer" 
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    background: 'rgba(255,255,255,0.05)',
                    border: '1px solid var(--glass-border)',
                    borderRadius: '10px',
                    color: 'var(--text-muted)',
                    padding: '0.5rem 0.75rem',
                    transition: 'all 0.2s',
                  }}
                  onMouseEnter={(e) => { e.currentTarget.style.color = 'white'; e.currentTarget.style.background = 'rgba(255,255,255,0.1)'}}
                  onMouseLeave={(e) => { e.currentTarget.style.color = 'var(--text-muted)'; e.currentTarget.style.background = 'rgba(255,255,255,0.05)'}}
                >
                  <ExternalLink size={16} />
                </a>
              )}
            </div>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}
