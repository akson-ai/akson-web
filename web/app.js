function ChatMessage({ sender, text }) {
  return (
    <div className={`chat ${sender === 'user' ? 'chat-start' : 'chat-end'}`}>
      <div className="chat-bubble">{text}</div>
    </div>
  );
}

function ChatApp() {
  const [messages, setMessages] = React.useState([]);
  const [inputText, setInputText] = React.useState('');
  const [assistants, setAssistants] = React.useState([]);
  const chatHistoryRef = React.useRef(null);

  React.useEffect(() => {
    // Load chat history
    fetch('/history')
      .then((res) => res.json())
      .then((history) => {
        setMessages(history.map(msg => ({
          sender: msg.role,
          text: msg.content
        })));
      });

    // Load assistants
    fetch('/assistants')
      .then((res) => res.json())
      .then(setAssistants);

    // Set up SSE listener
    const eventSource = new EventSource('/events');
    eventSource.onmessage = function(event) {
      const data = JSON.parse(event.data);
      setMessages(prev => [...prev, { sender: 'assistant', text: data.message }]);
    };

    return () => eventSource.close();
  }, []);

  React.useEffect(() => {
    // Scroll to bottom when messages change
    if (chatHistoryRef.current) {
      chatHistoryRef.current.scrollTop = chatHistoryRef.current.scrollHeight;
    }
  }, [messages]);

  const sendMessage = () => {
    if (!inputText.trim()) return;

    setMessages(prev => [...prev, { sender: 'user', text: inputText }]);

    fetch('/message', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: inputText }),
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
      <div className="flex mt-auto justify-center items-center space-x-2 p-4">
        <span className="text-sm font-medium">Assistant:</span>
        <select className="select select-bordered w-full max-w-xs">
          {assistants.map(assistant => (
            <option key={assistant.id} value={assistant.id}>
              {assistant.name}
            </option>
          ))}
        </select>
      </div>
      <div className="flex mt-2 justify-center items-center space-x-2 p-4">
        <input
          type="text"
          placeholder="Type here"
          className="input input-bordered w-full max-w-xs"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
          autoFocus
        />
        <button className="btn" onClick={sendMessage}>&uarr;</button>
      </div>
    </div>
  );
}

// Render your app
const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<ChatApp />);
