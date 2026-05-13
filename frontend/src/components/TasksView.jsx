import React from 'react';
import { Activity, CheckCircle, Clock, AlertCircle, RefreshCw, ListTodo, ChevronDown } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import MarkdownRenderer from './MarkdownRenderer';

export default function TasksView({ tasks, taskFilter, expandedTasks, toggleTaskExpand }) {
  return (
    <div style={{ padding: '2rem', display: 'flex', flexDirection: 'column', gap: '1.5rem', overflowY: 'auto', height: '100%' }}>
      {/* Dashboard Summary Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '1rem' }}>
        <div className="glass-panel" style={{ padding: '1.25rem', display: 'flex', flexDirection: 'column', gap: '0.25rem', background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.05)' }}>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Total Executed</span>
          <span style={{ fontSize: '1.75rem', fontWeight: 700, color: 'white' }}>{tasks.length}</span>
        </div>
        <div className="glass-panel" style={{ padding: '1.25rem', display: 'flex', flexDirection: 'column', gap: '0.25rem', background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.05)' }}>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Pending / Processing</span>
          <span style={{ fontSize: '1.75rem', fontWeight: 700, color: '#3b82f6' }}>
            {tasks.filter(t => t.status === 'PENDING' || t.status === 'PROCESSING').length}
          </span>
        </div>
        <div className="glass-panel" style={{ padding: '1.25rem', display: 'flex', flexDirection: 'column', gap: '0.25rem', background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.05)' }}>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Successfully Completed</span>
          <span style={{ fontSize: '1.75rem', fontWeight: 700, color: '#10b981' }}>
            {tasks.filter(t => t.status === 'COMPLETED').length}
          </span>
        </div>
        <div className="glass-panel" style={{ padding: '1.25rem', display: 'flex', flexDirection: 'column', gap: '0.25rem', background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.05)' }}>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Failed Pipeline Run</span>
          <span style={{ fontSize: '1.75rem', fontWeight: 700, color: '#ef4444' }}>
            {tasks.filter(t => t.status === 'FAILED').length}
          </span>
        </div>
      </div>

      {/* Tasks Data List */}
      <div className="glass-panel" style={{ background: 'rgba(255,255,255,0.01)', borderRadius: '16px', border: '1px solid var(--glass-border)', padding: '0.5rem', overflow: 'hidden' }}>
        <div style={{ padding: '1rem', borderBottom: '1px solid rgba(255,255,255,0.05)', display: 'grid', gridTemplateColumns: '0.4fr 1fr 0.5fr 0.8fr 0.5fr', gap: '1rem', fontSize: '0.75rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 600, letterSpacing: '0.05em' }}>
          <div>Status</div>
          <div>User Request</div>
          <div>Arrival / Start</div>
          <div>Task Identification</div>
          <div style={{ textAlign: 'right' }}>Details</div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', overflowY: 'auto', maxHeight: '500px' }}>
          {tasks.length === 0 ? (
            <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
              <ListTodo size={40} style={{ margin: '0 auto 1rem', opacity: 0.3 }} />
              No tasks found in Redis memory repository.
            </div>
          ) : (
            tasks
              .filter(t => {
                if (taskFilter === 'all') return true;
                if (taskFilter === 'PENDING') return t.status === 'PENDING' || t.status === 'PROCESSING';
                if (taskFilter === 'COMPLETED') return t.status === 'COMPLETED' || t.status === 'FAILED';
                return t.status === taskFilter;
              })
              .map((task) => {
                const isExpanded = !!expandedTasks[task.task_id];
                
                return (
                  <div key={task.task_id} style={{ borderBottom: '1px solid rgba(255,255,255,0.03)', transition: 'background 0.2s' }}>
                    {/* Main row */}
                    <div style={{ display: 'grid', gridTemplateColumns: '0.4fr 1fr 0.5fr 0.8fr 0.5fr', gap: '1rem', padding: '1rem', alignItems: 'center', fontSize: '0.85rem' }}>
                      <div>
                        <span style={{ 
                          display: 'inline-flex', alignItems: 'center', gap: '0.4rem', padding: '0.25rem 0.6rem', borderRadius: '6px', fontSize: '0.75rem', fontWeight: 600,
                          background: 
                            task.status === 'COMPLETED' ? 'rgba(16, 185, 129, 0.1)' : 
                            task.status === 'FAILED' ? 'rgba(239, 68, 68, 0.1)' : 
                            task.status === 'PROCESSING' ? 'rgba(245, 158, 11, 0.1)' : 'rgba(59, 130, 246, 0.1)',
                          color: 
                            task.status === 'COMPLETED' ? '#10b981' : 
                            task.status === 'FAILED' ? '#ef4444' : 
                            task.status === 'PROCESSING' ? '#f59e0b' : '#3b82f6',
                        }}>
                          {task.status === 'COMPLETED' && <CheckCircle size={12} />}
                          {task.status === 'FAILED' && <AlertCircle size={12} />}
                          {task.status === 'PENDING' && <Clock size={12} />}
                          {task.status === 'PROCESSING' && <RefreshCw size={12} className="spin-animation" />}
                          {task.status}
                        </span>
                      </div>
                      <div style={{ fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', paddingRight: '1rem' }}>
                        {task.user_query}
                      </div>
                      <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                        {new Date(task.arrival_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        <div style={{ fontSize: '0.7rem', opacity: 0.7 }}>
                          {new Date(task.arrival_time).toLocaleDateString([], { month: 'short', day: 'numeric' })}
                        </div>
                      </div>
                      <div style={{ fontFamily: 'monospace', fontSize: '0.75rem', color: '#94a3b8', display: 'flex', flexDirection: 'column', gap: '0.15rem' }}>
                        <span style={{ color: 'var(--accent-1)', opacity: 0.8 }}>ID: {task.task_id.substring(0, 13)}...</span>
                        <span>Via: {task.source} ({task.source_id})</span>
                      </div>
                      <div style={{ textAlign: 'right' }}>
                        <button 
                          onClick={() => toggleTaskExpand(task.task_id)}
                          style={{ background: 'rgba(255,255,255,0.05)', border: 'none', cursor: 'pointer', color: 'white', padding: '0.4rem 0.75rem', borderRadius: '8px', fontSize: '0.75rem', transition: 'background 0.2s', display: 'inline-flex', alignItems: 'center', gap: '0.3rem' }}
                          onMouseEnter={e => e.currentTarget.style.background = 'rgba(255,255,255,0.1)'}
                          onMouseLeave={e => e.currentTarget.style.background = 'rgba(255,255,255,0.05)'}
                        >
                          View Result
                          <ChevronDown size={14} style={{ transform: isExpanded ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }} />
                        </button>
                      </div>
                    </div>
                    
                    {/* Collapsible Details */}
                    <AnimatePresence>
                      {isExpanded && (
                        <motion.div
                          initial={{ height: 0, opacity: 0 }}
                          animate={{ height: 'auto', opacity: 1 }}
                          exit={{ height: 0, opacity: 0 }}
                          style={{ overflow: 'hidden', background: 'rgba(0,0,0,0.15)', borderTop: '1px solid rgba(255,255,255,0.02)' }}
                        >
                          <div style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem' }}>
                              <div>
                                <h4 style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '0.5rem', letterSpacing: '0.05em' }}>Full Query Text</h4>
                                <div style={{ background: 'rgba(0,0,0,0.2)', padding: '0.75rem', borderRadius: '8px', fontSize: '0.85rem', border: '1px solid rgba(255,255,255,0.03)', color: '#e2e8f0', whiteSpace: 'pre-wrap' }}>
                                  {task.user_query}
                                </div>
                              </div>
                              <div>
                                <h4 style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '0.5rem', letterSpacing: '0.05em' }}>Pipeline Timing</h4>
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem', fontSize: '0.8rem' }}>
                                  <div>🚀 Ingest: <span style={{ color: 'white' }}>{new Date(task.arrival_time).toLocaleString()}</span></div>
                                  {task.completion_time && (
                                    <>
                                      <div>🏁 Completed: <span style={{ color: 'white' }}>{new Date(task.completion_time).toLocaleString()}</span></div>
                                      <div>🕒 Duration: <span style={{ color: 'var(--accent-2)', fontWeight: 600 }}>
                                        {Math.round((new Date(task.completion_time) - new Date(task.arrival_time)) / 1000)} seconds
                                      </span></div>
                                    </>
                                  )}
                                  {!task.completion_time && (
                                    <div style={{ color: '#f59e0b' }}>⏱️ Pending execution completion...</div>
                                  )}
                                </div>
                              </div>
                            </div>

                            <div>
                              <h4 style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '0.5rem', letterSpacing: '0.05em' }}>Result Payload Response</h4>
                              <div style={{ background: 'rgba(0,0,0,0.3)', padding: '1rem', borderRadius: '10px', border: '1px solid rgba(255,255,255,0.05)', maxHeight: '250px', overflowY: 'auto' }}>
                                {task.result ? (
                                  <div style={{ fontSize: '0.85rem', color: '#cbd5e1', lineHeight: '1.6' }}>
                                    <MarkdownRenderer content={task.result} />
                                  </div>
                                ) : (
                                  <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontStyle: 'italic' }}>
                                    {task.status === 'PROCESSING' ? 'Worker is currently generating results...' : 'No result generated yet.'}
                                  </div>
                                )}
                              </div>
                            </div>
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                );
              })
          )}
        </div>
      </div>
    </div>
  );
}
