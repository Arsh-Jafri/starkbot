import React from 'react';
import './Sidebar.css';

const Sidebar = ({ collapsed, chatSessions, currentSessionId, onSwitchSession, onNewChat }) => {
  const formatDate = (dateString) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffInHours = (now - date) / (1000 * 60 * 60);
    
    if (diffInHours < 24) {
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } else if (diffInHours < 24 * 7) {
      return date.toLocaleDateString([], { weekday: 'short' });
    } else {
      return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
    }
  };

  return (
    <div className={`sidebar ${collapsed ? 'collapsed' : ''}`}>
      <div className="sidebar-content">
        <div className="sidebar-header">
          <button className="new-chat-sidebar-button" onClick={onNewChat}>
            <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
              <path d="M8 2a.5.5 0 0 1 .5.5v5h5a.5.5 0 0 1 0 1h-5v5a.5.5 0 0 1-1 0v-5h-5a.5.5 0 0 1 0-1h5v-5A.5.5 0 0 1 8 2Z"/>
            </svg>
            <span>New Chat</span>
          </button>
        </div>
        
        <div className="sidebar-body">
          <div className="chat-history-section">
            <h3 className="section-title">Recent Chats</h3>
            {chatSessions.length === 0 ? (
              <div className="empty-state">
                <p>No chat history yet</p>
                <p className="empty-subtitle">Start a conversation to see it here</p>
              </div>
            ) : (
              <div className="chat-list">
                {chatSessions.map((session) => (
                  <div
                    key={session.id}
                    className={`chat-item ${session.id === currentSessionId ? 'active' : ''}`}
                    onClick={() => onSwitchSession(session.id)}
                  >
                    <div className="chat-item-content">
                      <div className="chat-title">{session.title}</div>
                      <div className="chat-time">{formatDate(session.updatedAt)}</div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Sidebar;
