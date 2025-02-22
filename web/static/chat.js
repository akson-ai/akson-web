function ChatMessage({ sender, text }) {
  return (
    <div className={`chat ${sender === 'user' ? 'chat-end' : 'chat-start'}`}>
      <div className="chat-bubble">{text}</div>
    </div>
  );
}

function ChatApp() {
  const [messages, setMessages] = React.useState([]);
  const [inputText, setInputText] = React.useState('');
  const [assistants, setAssistants] = React.useState([]);
  const [selectedAssistant, setSelectedAssistant] = React.useState('');
  const chatHistoryRef = React.useRef(null);
  const abortControllerRef = React.useRef(null);

  const urlParams = new URLSearchParams(window.location.search);
  const chatId = urlParams.get('id');

  // TODO save selected assistant
  // TODO add assistant name to assistant messages
  // TODO add avatar to messages
  // TODO allow deleting individual messages
  // TODO allow editing of messages
  // TODO allow adding of new messages
  // TODO allow forking of chats

  React.useEffect(() => {
    // Load chat state
    fetch(`/${chatId}/state`)
      .then((res) => res.json())
      .then((state) => {
        setSelectedAssistant(state.assistant);
        setMessages(state.messages.map(msg => ({
          sender: msg.role,
          text: msg.content
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

    // Set up SSE listener
    const eventSource = new EventSource(`/${chatId}/events`);
    eventSource.onmessage = function(event) {
      const data = JSON.parse(event.data);
      console.log(data)

      if (data.control === 'new_message') {
        // Create a new empty message when receiving control event
        setMessages(prev => [...prev, { sender: 'assistant', text: '' }]);
      } else if (data.control === 'clear') {
        // Create a new empty message when receiving control event
        setMessages([]);
      } else if (data.chunk) {
        // Append chunk to the last message
        setMessages(prev => {
          const newMessages = [...prev];
          const lastMessage = newMessages[newMessages.length - 1];
          lastMessage.text += data.chunk;
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

    setMessages(prev => [...prev, { sender: 'user', text: inputText }]);

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

  return (
    <div className="flex flex-col max-w-prose mx-auto h-screen">
      <div id="chatHistory" className="p-4 overflow-y-auto" ref={chatHistoryRef}>
        {messages.map((msg, index) => (
          <ChatMessage key={index} sender={msg.sender} text={msg.text} />
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
            onChange={(e) => setSelectedAssistant(e.target.value)}
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
                type="text"
                className="input input-bordered flex-1"
                placeholder="Type your message..."
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
                autoFocus
              />
              <button className="btn" onClick={sendMessage}>&uarr;</button>
            </div>
          </label>
        </div>
      </div>
    </div>
  );
}

// Render your app
const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<ChatApp />);
