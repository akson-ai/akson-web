function ChatMessage({ role, name, content, category }) {
  return (
    <div className={`chat ${role === 'user' ? 'chat-end' : 'chat-start'}`}>
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
      <div className={`chat-bubble ${category ? `chat-bubble-${category}` : ''} whitespace-pre-wrap`}>
        {!content ? (
          <div className="flex items-center">
            <div className="loading loading-spinner loading-sm mr-2"></div>
            <span>Thinking...</span>
          </div>
        ) : (
          content
        )}
      </div>
    </div>
  );
}

function Sidebar({ chatHistory, chatId, createNewChat, handleSelectChat }) {
  return (
    <div className="bg-base-200 w-80 h-full flex flex-col">
      <div className="p-4 border-b border-base-300">
        <button className="btn btn-secondary w-full" onClick={createNewChat}>
          New Chat
        </button>
      </div>
      <div className="overflow-y-auto flex-grow">
        <ul className="menu p-4 w-full">
          {chatHistory.map(chat => (
            <li key={chat.id} className={chat.id === chatId ? "bordered" : ""}>
              <a
                href={`/chat?id=${chat.id}`}
                onClick={(e) => {
                  e.preventDefault();
                  handleSelectChat(chat.id);
                }}
                className={chat.id === chatId ? "active" : ""}
              >
                {chat.title || "Untitled Chat"}
                <span className="text-xs opacity-50 ml-2">
                  {new Date(chat.last_updated).toLocaleDateString()}
                </span>
              </a>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

function Drawer({ children, sidebarOpen, setSidebarOpen, chatHistory, chatId, createNewChat, handleSelectChat }) {
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
        <Sidebar
          chatHistory={chatHistory}
          chatId={chatId}
          createNewChat={createNewChat}
          handleSelectChat={handleSelectChat}
        />
      </div>
    </div>
  );
}

function ChatApp() {
  const [messages, setMessages] = React.useState([]);
  const [inputText, setInputText] = React.useState('');
  const [assistants, setAssistants] = React.useState([]);
  const [selectedAssistant, setSelectedAssistant] = React.useState('');
  const [chatHistory, setChatHistory] = React.useState([]);
  const [sidebarOpen, setSidebarOpen] = React.useState(false);
  const chatHistoryRef = React.useRef(null);
  const abortControllerRef = React.useRef(null);

  const urlParams = new URLSearchParams(window.location.search);
  const chatId = urlParams.get('id');

  // TODO allow deleting individual messages
  // TODO allow editing of messages
  // TODO allow adding of new messages
  // TODO allow forking of chats
  // TODO handle markdown in message

  React.useEffect(() => {
    // Load chat state
    fetch(`/${chatId}/state`)
      .then((res) => res.json())
      .then((state) => {
        setSelectedAssistant(state.assistant);
        setMessages(state.messages.map(msg => ({
          role: msg.role,
          name: msg.name,
          content: msg.content,
          category: msg.category,
        })));
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

    // Load chat history
    loadChatHistory();

    // Set up SSE listener
    const eventSource = new EventSource(`/${chatId}/events`);
    eventSource.onmessage = function(event) {
      const data = JSON.parse(event.data);
      console.log(data)

      if (data.type === 'begin_message') {
        setMessages(prev => [...prev, { role: data.role, name: data.name, content: '', category: data.category }]);
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

    return () => eventSource.close();
  }, []);

  React.useEffect(() => {
    // Scroll to bottom when messages change
    if (chatHistoryRef.current) {
      chatHistoryRef.current.scrollTop = chatHistoryRef.current.scrollHeight;
    }
  }, [messages]);

  const loadChatHistory = () => {
    fetch('/chats')
      .then((res) => res.json())
      .then((data) => {
        setChatHistory(data);
      })
      .catch(err => {
        console.error('Error loading chat history:', err);
      });
  };

  const handleSelectChat = (id) => {
    window.location.href = `/chat?id=${id}`;
  };

  const createNewChat = () => {
    window.location.href = '/chat';
  };

  React.useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && abortControllerRef.current) {
        abortControllerRef.current.abort();
        abortControllerRef.current = null;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const sendMessage = () => {
    if (!inputText.trim()) return;

    setMessages(prev => [...prev, { role: 'user', name: 'You', content: inputText }]);

    // Create new AbortController for this request
    abortControllerRef.current = new AbortController();

    fetch(`/${chatId}/message`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
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

function ChatContent({
  messages,
  inputText,
  setInputText,
  selectedAssistant,
  setSelectedAssistant,
  assistants,
  chatId,
  sendMessage,
  chatHistoryRef
}) {
  return (
    <>
      <div className="navbar bg-base-300">
        <div className="flex-none">
          <label htmlFor="drawer-toggle" className="btn btn-square btn-ghost">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" className="inline-block w-6 h-6 stroke-current">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 4h18M9 8h12M9 12h12M9 16h12M3 20h18"></path>
            </svg>
          </label>
        </div>
        <div className="flex-1">
          <span className="text-xl font-bold">Chat</span>
        </div>
      </div>

      <div className="flex flex-col max-w-prose mx-auto h-[calc(100vh-64px)] w-full">
        <div id="chatHistory" className="p-4 overflow-y-auto flex-grow" ref={chatHistoryRef}>
          {messages.map((msg, index) => (
            <ChatMessage key={index} role={msg.role} content={msg.content} name={msg.name} category={msg.category} />
          ))}
        </div>
        <div id="chatControls" className="flex flex-col mt-auto p-4 space-y-2">
          <label className="form-control w-full max-w-xs">
            <div className="label">
              <span className="label-text">Select assistant</span>
            </div>
            <select
              className="select select-bordered"
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
          </label>
          <div className="flex flex-col space-y-2">
            <label className="form-control w-full">
              <div className="label">
                <span className="label-text">Send message</span>
              </div>
              <div className="flex space-x-2">
                <input
                  id="messageInput"
                  type="text"
                  className="input input-bordered flex-1"
                  placeholder="Type your message..."
                  value={inputText}
                  onChange={(e) => setInputText(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
                  autoFocus
                />
                <button className="btn btn-primary" onClick={sendMessage}>&uarr;</button>
              </div>
            </label>
          </div>
        </div>
      </div>
    </>
  );
}

  return (
    <Drawer
      sidebarOpen={sidebarOpen}
      setSidebarOpen={setSidebarOpen}
      chatHistory={chatHistory}
      chatId={chatId}
      createNewChat={createNewChat}
      handleSelectChat={handleSelectChat}
    >
      <ChatContent
        messages={messages}
        inputText={inputText}
        setInputText={setInputText}
        selectedAssistant={selectedAssistant}
        setSelectedAssistant={setSelectedAssistant}
        assistants={assistants}
        chatId={chatId}
        sendMessage={sendMessage}
        chatHistoryRef={chatHistoryRef}
      />
    </Drawer>
  );
}

// Render your app
const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<ChatApp />);
