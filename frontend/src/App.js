import React, { useState, useEffect } from 'react';
import './App.css';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import ChatArea from './components/ChatArea';
import MessageInput from './components/MessageInput';

function App() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [chatSessions, setChatSessions] = useState([]);
  const [currentSessionId, setCurrentSessionId] = useState(null);

  // Load chat sessions from localStorage on component mount
  useEffect(() => {
    const savedSessions = localStorage.getItem('ironManChatSessions');
    if (savedSessions) {
      setChatSessions(JSON.parse(savedSessions));
    }
  }, []);

  // Save chat sessions to localStorage whenever they change
  useEffect(() => {
    localStorage.setItem('ironManChatSessions', JSON.stringify(chatSessions));
  }, [chatSessions]);

  const toggleSidebar = () => {
    setSidebarCollapsed(!sidebarCollapsed);
  };

  const createNewSession = () => {
    // Check if there's already an empty session (no messages)
    const emptySession = chatSessions.find(session => session.messages.length === 0);
    
    if (emptySession) {
      // Switch to the existing empty session instead of creating a new one
      setCurrentSessionId(emptySession.id);
      setMessages([]);
      return emptySession.id;
    }
    
    // Only create a new session if no empty session exists
    const newSessionId = Date.now().toString();
    const newSession = {
      id: newSessionId,
      title: 'New Chat',
      messages: [],
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString()
    };
    
    setChatSessions(prev => [newSession, ...prev]);
    setCurrentSessionId(newSessionId);
    setMessages([]);
    return newSessionId;
  };

  const switchToSession = (sessionId) => {
    const session = chatSessions.find(s => s.id === sessionId);
    if (session) {
      setCurrentSessionId(sessionId);
      setMessages(session.messages);
    }
  };

  const updateSessionTitle = (sessionId, firstMessage) => {
    const title = firstMessage.length > 30 
      ? firstMessage.substring(0, 30) + '...' 
      : firstMessage;
    
    setChatSessions(prev => 
      prev.map(session => 
        session.id === sessionId 
          ? { ...session, title, updatedAt: new Date().toISOString() }
          : session
      )
    );
  };

  const deleteSession = (sessionId) => {
    setChatSessions(prev => prev.filter(session => session.id !== sessionId));
    
    // If we're deleting the current session, switch to another session or clear
    if (currentSessionId === sessionId) {
      const remainingSessions = chatSessions.filter(session => session.id !== sessionId);
      if (remainingSessions.length > 0) {
        // Switch to the first remaining session
        const newCurrentSession = remainingSessions[0];
        setCurrentSessionId(newCurrentSession.id);
        setMessages(newCurrentSession.messages);
      } else {
        // No sessions left, clear everything
        setCurrentSessionId(null);
        setMessages([]);
      }
    }
  };

  const sendMessage = async (userMessage) => {
    // Determine session ID - use current if it exists and is empty, otherwise create new
    let sessionId = currentSessionId;
    
    if (!sessionId) {
      // No current session, create one
      sessionId = createNewSession();
    } else if (messages.length > 0) {
      // Current session has messages, create a new one
      sessionId = createNewSession();
    }
    // If currentSessionId exists and messages.length === 0, use the existing empty session

    // Add user message to conversation
    const userMsg = { id: Date.now(), type: 'user', content: userMessage, timestamp: new Date() };
    const updatedMessages = [...messages, userMsg];
    setMessages(updatedMessages);
    setIsLoading(true);

    // Update session title with first message and add to sidebar immediately
    if (messages.length === 0) {
      updateSessionTitle(sessionId, userMessage);
    }

    try {
      // Send message to FastAPI backend
      const response = await fetch('http://localhost:8000/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message: userMessage }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();

      // Add bot response to conversation
      const botMsg = {
        id: Date.now() + 1,
        type: 'bot',
        content: data.response,
        sources: data.sources || [],
        timestamp: new Date()
      };
      const finalMessages = [...updatedMessages, botMsg];
      setMessages(finalMessages);

      // Update the session with all messages
      setChatSessions(prev => 
        prev.map(session => 
          session.id === sessionId 
            ? { ...session, messages: finalMessages, updatedAt: new Date().toISOString() }
            : session
        )
      );

    } catch (error) {
      console.error('Error sending message:', error);
      // Add error message to conversation
      const errorMsg = { 
        id: Date.now() + 1, 
        type: 'error', 
        content: 'Sorry, I encountered an error. Please try again.', 
        timestamp: new Date() 
      };
      const finalMessages = [...updatedMessages, errorMsg];
      setMessages(finalMessages);

      // Update the session with error message
      setChatSessions(prev => 
        prev.map(session => 
          session.id === sessionId 
            ? { ...session, messages: finalMessages, updatedAt: new Date().toISOString() }
            : session
        )
      );
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="App">
      <Sidebar 
        collapsed={sidebarCollapsed} 
        chatSessions={chatSessions}
        currentSessionId={currentSessionId}
        onSwitchSession={switchToSession}
        onNewChat={createNewSession}
        onDeleteSession={deleteSession}
      />
      <div className={`main-content ${sidebarCollapsed ? 'sidebar-collapsed' : ''}`}>
        <Header 
          onToggleSidebar={toggleSidebar} 
          sidebarCollapsed={sidebarCollapsed}
          onNewChat={createNewSession}
        />
        <ChatArea messages={messages} isLoading={isLoading} />
        <MessageInput onSendMessage={sendMessage} isLoading={isLoading} />
      </div>
    </div>
  );
}

export default App;
