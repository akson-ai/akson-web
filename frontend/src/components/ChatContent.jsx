import { useState, useEffect, useRef } from 'react';
import ChatMessage from './ChatMessage';

const API_BASE_URL = 'http://localhost:8000';

function ChatContent({ chatId }) {
  const abortControllerRef = useRef(null);
  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState('');
  const [assistants, setAssistants] = useState([]);
  const [selectedAssistant, setSelectedAssistant] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const chatHistoryRef = useRef(null);
  const messageInputRef = useRef(null);

  const createNewChat = () => {
    window.location.href = '/chat';
  };

  useEffect(() => {
    // Load chat state
    setIsLoading(true);
    setError(null);

    fetch(`${API_BASE_URL}/${chatId}/state`)
      .then((res) => {
        if (!res.ok) throw new Error('Failed to load chat state');
        return res.json();
      })
      .then((state) => {
        setSelectedAssistant(state.assistant);
        setMessages(state.messages.map(msg => ({
          id: msg.id,
          role: msg.role,
          name: msg.name,
          content: msg.content,
          category: msg.category,
        })));
        setIsLoading(false);
      })
      .catch(err => {
        console.error('Error loading chat state:', err);
        setError('Failed to load chat. Please try again.');
        setIsLoading(false);
      });

    // Load assistants
    fetch(`${API_BASE_URL}/assistants`)
      .then((res) => res.json())
      .then((data) => {
        setAssistants(data);
        if (data.length > 0) {
          setSelectedAssistant(data[0].name);
        }
      });

    // Set up SSE listener
    const eventSource = new EventSource(`${API_BASE_URL}/${chatId}/events`);
    eventSource.onmessage = function(event) {
      const data = JSON.parse(event.data);
      console.log(data)

      if (data.type === 'begin_message') {
        setMessages(prev => [...prev, { id: data.id, role: data.role, name: data.name, content: '', category: data.category }]);
      } else if (data.type === 'clear') {
        setMessages([]);
      } else if (data.type === 'add_chunk') {
        // Append chunk to the last message
        setMessages(prev => {
          const updated = [...prev];
          const i = updated.length - 1;
          updated[i] = {
            ...updated[i],
            content: updated[i].content + data.chunk
          };
          return updated;
        });
      } else if (data.type === 'end_message') {
        // TODO handle end_message in web app
      }
    };

    return () => {
      eventSource.close();
    };
  }, []);

  // Add a separate useEffect for the keyboard shortcut
  useEffect(() => {
    const handleNewChatShortcut = (e) => {
      // Check for Cmd+Shift+O (Mac) or Ctrl+Shift+O (Windows/Linux)
      if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key === 'o') {
        e.preventDefault();
        createNewChat();
      }
    };

    window.addEventListener('keydown', handleNewChatShortcut);

    return () => {
      window.removeEventListener('keydown', handleNewChatShortcut);
    };
  }, []);

  // Add a separate useEffect for keyboard shortcuts
  useEffect(() => {
    const handleKeyboardShortcuts = (e) => {
      // Check for Shift+Esc to focus input
      if (e.shiftKey && e.key === 'Escape') {
        e.preventDefault();
        if (messageInputRef.current) {
          messageInputRef.current.focus();
        }
      }
      
      // Check for Escape to abort current request
      if (e.key === 'Escape' && abortControllerRef.current) {
        abortControllerRef.current.abort();
        abortControllerRef.current = null;
      }
    };

    window.addEventListener('keydown', handleKeyboardShortcuts);

    return () => {
      window.removeEventListener('keydown', handleKeyboardShortcuts);
    };
  }, []);

  useEffect(() => {
    // Scroll to bottom when messages change
    if (chatHistoryRef.current) {
      chatHistoryRef.current.scrollTop = chatHistoryRef.current.scrollHeight;
    }
  }, [messages]);

  const sendMessage = () => {
    if (!inputText.trim()) return;

    // Generate a unique ID for the message
    const messageId = crypto.randomUUID();

    // Add message to UI with the generated ID
    setMessages(prev => [...prev, {
      id: messageId,
      role: 'user',
      name: 'You',
      content: inputText
    }]);

    // Create new AbortController for this request
    abortControllerRef.current = new AbortController();

    fetch(`${API_BASE_URL}/${chatId}/message`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        id: messageId,
        content: inputText,
        assistant: selectedAssistant,
      }),
      signal: abortControllerRef.current.signal,
    }).catch(err => {
      if (err.name === 'AbortError') {
        console.log('Request cancelled');
      } else {
        console.error('Error:', err);
      }
    });

    setInputText('');
  };

  const deleteMessage = (messageId) => {
    // Ask for confirmation before deleting
    if (!confirm('Are you sure you want to delete this message?')) {
      return;
    }
    
    // Optimistically update UI
    const newMessages = messages.filter(msg => msg.id !== messageId);
    setMessages(newMessages);

    // Send delete request to backend
    fetch(`${API_BASE_URL}/${chatId}/message/${messageId}`, {
      method: 'DELETE',
    })
    .then(response => {
      if (!response.ok) {
        throw new Error('Failed to delete message');
      }
      // Message successfully deleted on the server
    })
    .catch(error => {
      console.error('Error deleting message:', error);
      // Revert the optimistic update if there was an error
      setMessages(messages);
    });
  };

  return (
    <>
      <div className="navbar bg-base-100 shadow-sm">
        <div className="navbar-start">
          <div className="tooltip tooltip-right" data-tip="Chat history">
            <label htmlFor="drawer-toggle" className="btn btn-ghost btn-circle">
              <i className="fas fa-clock-rotate-left text-lg"></i>
            </label>
          </div>
        </div>
        <div className="navbar-center">
          <select
            id="assistant-select"
            className="select select-bordered w-full max-w-xs"
            value={selectedAssistant}
            onChange={(e) => {
              const assistant = e.target.value;
              setSelectedAssistant(assistant);
              fetch(`${API_BASE_URL}/${chatId}/assistant`, {
                method: 'PUT',
                body: assistant,
              });
              document.getElementById('messageInput').focus();
            }}
          >
            {assistants.map(assistant => (
              <option key={assistant.name} value={assistant.name}>
                {assistant.name}
              </option>
            ))}
          </select>
        </div>
        <div className="navbar-end">
          <div className="tooltip tooltip-left" data-tip="New chat">
            <button className="btn btn-ghost btn-circle" onClick={createNewChat}>
              <i className="fas fa-comment-medical text-lg"></i>
            </button>
          </div>
        </div>
      </div>

      <div className="flex flex-col max-w-5xl mx-auto h-[calc(100vh-64px)] w-full">
        {error && (
          <div className="alert alert-error shadow-lg m-4">
            <div>
              <i className="fas fa-exclamation-circle"></i>
              <span>{error}</span>
            </div>
          </div>
        )}

        <div id="chatHistory" className="p-4 overflow-y-auto flex-grow" ref={chatHistoryRef}>
          {isLoading ? (
            <div className="flex justify-center items-center h-full">
              <div className="loading loading-spinner loading-lg"></div>
            </div>
          ) : (
            messages.map((msg) => (
              <ChatMessage
                id={msg.id}
                key={msg.id}
                role={msg.role}
                content={msg.content}
                name={msg.name}
                category={msg.category}
                onDelete={deleteMessage}
              />
            ))
          )}
        </div>
        <div id="chatControls" className="flex flex-col mt-auto p-4 space-y-2">
          <div className="flex flex-col space-y-2">
            <label className="form-control w-full">
              <div className="flex space-x-2">
                <input
                  id="messageInput"
                  ref={messageInputRef}
                  type="text"
                  className="input input-bordered flex-1"
                  placeholder="Type your message..."
                  value={inputText}
                  onChange={(e) => setInputText(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
                  autoFocus
                />
                <button className="btn btn-primary" onClick={sendMessage}>
                  <i className="fas fa-arrow-up"></i>
                </button>
              </div>
            </label>
          </div>
        </div>
      </div>
    </>
  );
}

export default ChatContent;
