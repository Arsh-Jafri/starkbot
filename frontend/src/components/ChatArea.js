import React, { useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import './ChatArea.css';

const ChatArea = ({ messages, isLoading }) => {
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const formatTime = (timestamp) => {
    return new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div className="chat-area">
      <div className="chat-content">
        {messages.length === 0 ? (
          // Welcome screen when no messages
          <div className="welcome-screen">
            <div className="logo-container">
                <img 
                  src="/iron-man-logo-red.jpg" 
                  alt="Iron Man Logo" 
                  className="iron-man-logo"
                />
            </div>
            <h1 className="main-title">Welcome to StarkBot</h1>
            <p className="subtitle">StarkBot's your AI assistant for exploring the world of Tony Stark and his creations.</p>
          </div>
        ) : (
          // Chat messages
          <div className="messages-container">
            {messages.map((message) => (
              <div key={message.id} className={`message ${message.type}`}>
                <div className="message-content">
                  <div className="message-text">
                    {message.type === 'bot' ? (
                      <ReactMarkdown>{message.content}</ReactMarkdown>
                    ) : (
                      message.content
                    )}
                  </div>
                  {message.type === 'bot' && message.sources && message.sources.length > 0 && (
                    <div className="message-sources">
                      <span className="sources-label">Sources:</span>
                      {message.sources.map((source, idx) => (
                        source.url ? (
                          <a
                            key={idx}
                            href={source.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="source-chip"
                          >
                            {source.name}
                          </a>
                        ) : (
                          <span key={idx} className="source-chip">{source.name}</span>
                        )
                      ))}
                    </div>
                  )}
                  <div className="message-time">{formatTime(message.timestamp)}</div>
                </div>
              </div>
            ))}
            
            {/* Loading indicator */}
            {isLoading && (
              <div className="message bot">
                <div className="message-content">
                  <div className="message-text loading">
                    <div className="typing-indicator">
                      <span></span>
                      <span></span>
                      <span></span>
                    </div>
                    StarkBot is thinking...
                  </div>
                </div>
              </div>
            )}
            
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>
    </div>
  );
};

export default ChatArea;
