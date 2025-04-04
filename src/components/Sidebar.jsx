import { useState, useEffect } from 'react';
import { API_BASE_URL } from '../constants';

function Sidebar({ chatId }) {
  const [chatHistory, setChatHistory] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [hoveredChatId, setHoveredChatId] = useState(null);

  const loadChatHistory = () => {
    fetch(`${API_BASE_URL}/chats`, { credentials: 'include' })
      .then((res) => res.json())
      .then((data) => {
        setChatHistory(data);
      })
      .catch(err => {
        console.error('Error loading chat history:', err);
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

  const handleDeleteChat = (e, id) => {
    e.preventDefault();
    e.stopPropagation();

    if (confirm('Are you sure you want to delete this chat?')) {
      fetch(`${API_BASE_URL}/${id}`, {
        method: 'DELETE',
        credentials: 'include',
      })
        .then((res) => {
          if (res.ok) {
            // Remove the chat from the list
            setChatHistory(prev => prev.filter(chat => chat.id !== id));

            // If the deleted chat is the current one, redirect to a new chat
            if (id === chatId) {
              window.location.href = '/chat';
            }
          } else {
            console.error('Failed to delete chat');
          }
        })
        .catch(err => {
          console.error('Error deleting chat:', err);
        });
    }
  };

  useEffect(() => {
    loadChatHistory();
  }, []);

  return (
    <div className="bg-base-200 w-80 h-full flex flex-col">
      <div className="p-4">
        <input
          id="search-chats"
          type="text"
          placeholder="Search chats..."
          className="input input-bordered w-full"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
        />
      </div>
      <div className="overflow-y-auto flex-grow">
        <ul className="menu w-full">
        {filteredChats.map(chat => (
          <li
            key={chat.id}
            onMouseEnter={() => setHoveredChatId(chat.id)}
            onMouseLeave={() => setHoveredChatId(null)}
          >
            <a
              href={`/chat?id=${chat.id}`}
              className="flex"
              onClick={(e) => {
                e.preventDefault();
                handleSelectChat(chat.id);
              }}
            >
              <span className="grow truncate">{chat.title}</span>
              <button
                className={`btn btn-xs btn-ghost btn-square btn-error flex-none ${hoveredChatId === chat.id ? 'visible' : 'invisible'}`}
                onClick={(e) => handleDeleteChat(e, chat.id)}
                title="Delete chat"
              >
                <i className="fas fa-trash"></i>
              </button>
            </a>
          </li>
        ))}
        </ul>
      </div>
    </div>
  );
}

export default Sidebar;
