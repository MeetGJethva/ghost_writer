import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, Smartphone, Briefcase, MessageSquare, Globe } from 'lucide-react';

const filterOptions = [
  { id: 'all', label: 'All Streams', icon: Globe, color: 'var(--accent-2)' },
  { id: 'HTTP', label: 'Web Sessions', icon: MessageSquare, color: 'var(--accent-1)' },
  { id: 'WHATSAPP', label: 'WhatsApp', icon: Smartphone, color: '#22c55e' },
  { id: 'JIRA', label: 'Jira Tasks', icon: Briefcase, color: '#3b82f6' }
];

export default function ViewModeSelector({ currentFilter, onChange }) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);

  const activeOption = filterOptions.find(opt => opt.id === currentFilter) || filterOptions[0];

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSelect = (id) => {
    onChange(id);
    setIsOpen(false);
  };

  return (
    <div className="view-mode-dropdown-container" ref={dropdownRef}>
      <h3 className="sidebar-sub-header">View Mode</h3>
      <div className="custom-dropdown">
        <button 
          type="button"
          className={`dropdown-trigger ${isOpen ? 'active' : ''}`}
          onClick={() => setIsOpen(!isOpen)}
        >
          <activeOption.icon size={16} color={activeOption.color} />
          <span className="trigger-label">{activeOption.label}</span>
          <motion.div
            animate={{ rotate: isOpen ? 180 : 0 }}
            transition={{ duration: 0.2 }}
            style={{ display: 'flex', alignItems: 'center' }}
          >
            <ChevronDown size={16} className="chevron-icon" />
          </motion.div>
        </button>

        <AnimatePresence>
          {isOpen && (
            <motion.ul 
              className="dropdown-menu"
              initial={{ opacity: 0, y: -8, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -8, scale: 0.98 }}
              transition={{ duration: 0.15, ease: "easeOut" }}
            >
              {filterOptions.map(option => {
                const isSelected = option.id === currentFilter;
                return (
                  <li key={option.id}>
                    <button
                      type="button"
                      className={`dropdown-item ${isSelected ? 'selected' : ''}`}
                      onClick={() => handleSelect(option.id)}
                    >
                      <option.icon size={16} color={isSelected ? '#fff' : option.color} style={{ opacity: isSelected ? 1 : 0.8 }} />
                      <span>{option.label}</span>
                    </button>
                  </li>
                );
              })}
            </motion.ul>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
