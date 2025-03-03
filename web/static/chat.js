// TODO allow editing of messages
// TODO allow forking of chats
// TODO handle markdown in message
// TODO when new chat is persisted, reload chat history
// TODO highlight code blocks

function ChatMessage({ id, role, name, content, category, onDelete }) {
  const [isHovered, setIsHovered] = React.useState(false);

  const copyToClipboard = () => {
    navigator.clipboard.writeText(content)
      .then(() => {
        // Show toast notification
        const toast = document.getElementById('toast');
        if (toast) {
          toast.classList.remove('hidden');
          setTimeout(() => {
            toast.classList.add('hidden');
          }, 3000);
        }
      })
      .catch(err => {
        console.error('Failed to copy message: ', err);
      });
  };

  return (
    <div
      className={`chat ${role === 'user' ? 'chat-end' : 'chat-start'}`}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <div className="chat-image avatar">
        <div className="w-10 rounded-full bg-base-300 place-content-center">
          <div className="text-2xl place-self-center">
            {role === 'user' ? '👤' : '🤖'}
          </div>
        </div>
      </div>
      <div className="chat-header">
        <time className="text-xs opacity-50">{name}</time>
      </div>
      <div className={`chat-bubble mt-1 ${category ? `chat-bubble-${category}` : ''} whitespace-pre-wrap`}>
        {!content ? (
          <div className="flex items-center">
            <div className="loading loading-spinner loading-sm mr-2"></div>
            <span>Thinking...</span>
          </div>
        ) : (
          content
        )}
      </div>
      {content && (
        <div className={`chat-footer mt-1 ${isHovered ? 'visible' : 'invisible'}`}>
          <>
            <button
              className="btn btn-xs btn-ghost btn-square"
              onClick={copyToClipboard}
              title="Copy message"
            >
              <i className="fas fa-copy"></i>
            </button>
            <button
              className="btn btn-xs btn-ghost btn-square btn-error"
              onClick={() => onDelete(id)}
              title="Delete message"
            >
              <i className="fas fa-trash"></i>
            </button>
          </>
        </div>
      )}
    </div>
  );
}

function Sidebar({ chatId }) {
  const [chatHistory, setChatHistory] = React.useState([]);
  const [isLoading, setIsLoading] = React.useState(true);
  const [searchTerm, setSearchTerm] = React.useState('');

  const loadChatHistory = () => {
    setIsLoading(true);
    fetch('/chats')
      .then((res) => res.json())
      .then((data) => {
        setChatHistory(data);
        setIsLoading(false);
      })
      .catch(err => {
        console.error('Error loading chat history:', err);
        setIsLoading(false);
      });
  };

  // Filter chats based on search term
  const filteredChats = searchTerm.trim()
    ? chatHistory.filter(chat =>
        chat.title.toLowerCase().includes(searchTerm.toLowerCase())
      )
    : chatHistory;

  const handleSelectChat = (id) => {
    window.location.href = `/chat?id=${id}`;
  };

  React.useEffect(() => {
    loadChatHistory();
  }, []);

  return (
    <div className="bg-base-200 w-80 h-full flex flex-col">
      <div className="p-4">
        <input
          type="text"
          placeholder="Search chats..."
          className="input input-bordered w-full"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
        />
      </div>
      <div className="overflow-y-auto flex-grow">
        {isLoading ? (
          <div className="flex justify-center items-center p-4">
            <div className="loading loading-spinner loading-md"></div>
          </div>
        ) : (
          <ul className="menu p-4 w-full">
            {filteredChats.length > 0 ? (
              filteredChats.map(chat => (
                <li key={chat.id} className={chat.id === chatId ? "bordered" : ""}>
                  <a
                    href={`/chat?id=${chat.id}`}
                    onClick={(e) => {
                      e.preventDefault();
                      handleSelectChat(chat.id);
                    }}
                    className={chat.id === chatId ? "active" : ""}
                  >
                    {chat.title}
                    <span className="text-xs opacity-50 ml-2">
                      {new Date(chat.last_updated).toLocaleDateString()}
                    </span>
                  </a>
                </li>
              ))
            ) : (
              <li className="text-center opacity-70">No chats found</li>
            )}
          </ul>
        )}
      </div>
    </div>
  );
}

function Drawer({ children, chatId }) {
  const [sidebarOpen, setSidebarOpen] = React.useState(false);

  // Add useEffect for the sidebar toggle shortcut
  React.useEffect(() => {
    const handleSidebarShortcut = (e) => {
      // Check for Cmd+Shift+S (Mac) or Ctrl+Shift+S (Windows/Linux)
      if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key === 's') {
        e.preventDefault();
        setSidebarOpen(prevState => !prevState);
      }
    };

    window.addEventListener('keydown', handleSidebarShortcut);

    return () => {
      window.removeEventListener('keydown', handleSidebarShortcut);
    };
  }, []);

  return (
    <div className="drawer"> {/* The root container */}

      {/* A hidden checkbox to toggle the visibility of the sidebar */}
      <input
        id="drawer-toggle"
        type="checkbox"
        className="drawer-toggle"
        checked={sidebarOpen}
        onChange={() => setSidebarOpen(!sidebarOpen)}
      />

      {/* All main page content goes here */}
      <div className="drawer-content flex flex-col">
        {children}
      </div>

      {/* Sidebar wrapper */}
      <div className="drawer-side">
        {/* A dark overlay that covers the whole page when the drawer is open */}
        <label htmlFor="drawer-toggle" className="drawer-overlay"></label>

        {/* The sidebar content */}
        <Sidebar chatId={chatId} />
      </div>
    </div>
  );
}

function ChatContent({ chatId, abortControllerRef }) {
  const [messages, setMessages] = React.useState([]);
  const [inputText, setInputText] = React.useState('');
  const [assistants, setAssistants] = React.useState([]);
  const [selectedAssistant, setSelectedAssistant] = React.useState('');
  const [isLoading, setIsLoading] = React.useState(true);
  const [error, setError] = React.useState(null);
  const chatHistoryRef = React.useRef(null);
  const messageInputRef = React.useRef(null);

  const createNewChat = () => {
    window.location.href = '/chat';
  };

  React.useEffect(() => {
    // Load chat state
    setIsLoading(true);
    setError(null);

    fetch(`/${chatId}/state`)
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
    fetch('/assistants')
      .then((res) => res.json())
      .then((data) => {
        setAssistants(data);
        if (data.length > 0) {
          setSelectedAssistant(data[0].name);
        }
      });

    // Set up SSE listener
    const eventSource = new EventSource(`/${chatId}/events`);
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
          const newMessages = [...prev];
          const lastMessage = newMessages[newMessages.length - 1];
          lastMessage.content += data.chunk;
          return newMessages;
        });
      }
    };

    return () => {
      eventSource.close();
    };
  }, []);

  // Add a separate useEffect for the keyboard shortcut
  React.useEffect(() => {
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

  // Add a separate useEffect for the focus input shortcut
  React.useEffect(() => {
    const handleFocusInputShortcut = (e) => {
      // Check for Shift+Esc
      if (e.shiftKey && e.key === 'Escape') {
        e.preventDefault();
        if (messageInputRef.current) {
          messageInputRef.current.focus();
        }
      }
    };

    window.addEventListener('keydown', handleFocusInputShortcut);

    return () => {
      window.removeEventListener('keydown', handleFocusInputShortcut);
    };
  }, []);

  React.useEffect(() => {
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

    fetch(`/${chatId}/message`, {
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
    // Optimistically update UI
    const newMessages = messages.filter(msg => msg.id !== messageId);
    setMessages(newMessages);

    // Send delete request to backend
    fetch(`/${chatId}/message/${messageId}`, {
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
            className="select select-bordered w-full max-w-xs"
            value={selectedAssistant}
            onChange={(e) => {
              const assistant = e.target.value;
              setSelectedAssistant(assistant);
              fetch(`/${chatId}/assistant`, {
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

      <div className="flex flex-col max-w-prose mx-auto h-[calc(100vh-64px)] w-full">
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
                  onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
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

function KeyboardShortcutsModal() {
  return (
    <dialog id="shortcuts_modal" className="modal">
      <div className="modal-box">
        <h3 className="font-bold text-lg">Keyboard Shortcuts</h3>
        <div className="py-4">
          <table className="table table-zebra">
            <thead>
              <tr>
                <th>Shortcut</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td><kbd className="kbd kbd-sm">Cmd</kbd> + <kbd className="kbd kbd-sm">Shift</kbd> + <kbd className="kbd kbd-sm">S</kbd></td>
                <td>Toggle sidebar</td>
              </tr>
              <tr>
                <td><kbd className="kbd kbd-sm">Cmd</kbd> + <kbd className="kbd kbd-sm">Shift</kbd> + <kbd className="kbd kbd-sm">O</kbd></td>
                <td>New chat</td>
              </tr>
              <tr>
                <td><kbd className="kbd kbd-sm">Shift</kbd> + <kbd className="kbd kbd-sm">Esc</kbd></td>
                <td>Focus input</td>
              </tr>
              <tr>
                <td><kbd className="kbd kbd-sm">Esc</kbd></td>
                <td>Cancel current request</td>
              </tr>
              <tr>
                <td><kbd className="kbd kbd-sm">Cmd</kbd> + <kbd className="kbd kbd-sm">/</kbd></td>
                <td>Show this help</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div className="modal-action">
          <form method="dialog">
            <button className="btn">Close</button>
          </form>
        </div>
      </div>
    </dialog>
  );
}

function ChatApp() {
  const abortControllerRef = React.useRef(null);

  const urlParams = new URLSearchParams(window.location.search);
  const chatId = urlParams.get('id');

  React.useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && abortControllerRef.current) {
        abortControllerRef.current.abort();
        abortControllerRef.current = null;
      }

      // Add shortcut for keyboard shortcuts modal
      if ((e.metaKey || e.ctrlKey) && e.key === '/') {
        e.preventDefault();
        document.getElementById('shortcuts_modal').showModal();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  return (
    <>
      <Drawer chatId={chatId}>
        <ChatContent chatId={chatId} abortControllerRef={abortControllerRef} />
      </Drawer>

      <KeyboardShortcutsModal />

      {/* Keyboard shortcuts hint button */}
      <div
        className="fixed bottom-4 right-4 btn btn-sm btn-ghost opacity-60 hover:opacity-100"
        onClick={() => document.getElementById('shortcuts_modal').showModal()}
      >
        <i className="fas fa-keyboard mr-1"></i>
        <span>⌘ + /</span>
      </div>

      {/* Toast notification */}
      <div id="toast" className="toast toast-end hidden">
        <div className="alert alert-success">
          <span>Copied to clipboard!</span>
        </div>
      </div>
    </>
  );
}

// Render your app
const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<ChatApp />);
