function Counter() {
    const [count, setCount] = React.useState(0);

    return (
	<div style={{
	    padding: '20px',
	    maxWidth: '300px',
	    margin: '20px auto',
	    border: '1px solid #ddd',
	    borderRadius: '8px',
	    textAlign: 'center'
	}}>
	    <h2>Counter: {count}</h2>
	    <button
		onClick={() => setCount(count + 1)}
		style={{
		    padding: '8px 16px',
		    backgroundColor: '#0070f3',
		    color: 'white',
		    border: 'none',
		    borderRadius: '4px',
		    cursor: 'pointer'
		}}
	    >
		Increment
	    </button>
	</div>
    );
}


chatHistory = document.getElementById('chatHistory');
input = document.getElementById('input');
send = document.getElementById('send');
function addMessage(sender, text) {
  const chatDiv = document.createElement('div');
  chatDiv.classList.add('chat');
  if (sender === 'user') {
    chatDiv.classList.add('chat-start');
  } else if (sender === 'assistant') {
    chatDiv.classList.add('chat-end');
  }
  const messageDiv = document.createElement('div');
  messageDiv.classList.add('chat-bubble');
  messageDiv.textContent = text;
  chatDiv.appendChild(messageDiv);
  chatHistory.appendChild(chatDiv);
  chatHistory.scrollTop = chatHistory.scrollHeight;
}
function sendMessage() {
  if (!input.value) return;
  const message = input.value;
  addMessage('user', message);
  input.value = '';

  // Send message to server
  fetch('/message', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ message: message }),
  });
}
send.addEventListener('click', sendMessage);
input.addEventListener('keypress', (event) => {
  if (event.key === 'Enter') {
    sendMessage();
  }
});

// Create a new EventSource object
const eventSource = new EventSource('/events');

// Listen for incoming messages
eventSource.onmessage = function(event) {
  console.log('Received message:', event.data);
  const data = JSON.parse(event.data);

  // Add each message uniquely
  addMessage('assistant', data.message);
};

fetch('/history').then((res) => {
  res.json().then((history) => {
    history.forEach((message) => {
      addMessage(message.role, message.content);
    });
  });
});

fetch('/assistants').then((res) => {
  res.json().then((assistants) => {
    const select = document.getElementById('assistant');
    assistants.forEach((assistant) => {
      const option = document.createElement('option');
      option.value = assistant.id;
      option.textContent = assistant.name;
      select.appendChild(option);
    });
  });
});

input.focus();

// Render your app
const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<Counter />);
