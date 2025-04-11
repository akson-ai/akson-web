import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { API_BASE_URL } from '../constants';

function Sidebar({ chatId }) {
  const [searchTerm, setSearchTerm] = useState('');
  const [hoveredChatId, setHoveredChatId] = useState(null);
  const queryClient = useQueryClient();

  const { data: chatHistory = [] } = useQuery({
    queryKey: ['chats'],
    queryFn: async () => {
      const res = await fetch(`${API_BASE_URL}/chats`, { credentials: 'include' });
      return res.json();
    }
  });

  const deleteChatMutation = useMutation({
    mutationFn: async (id) => {
      await fetch(`${API_BASE_URL}/${id}`, {
        method: 'DELETE',
        credentials: 'include',
      });
    },
    onSuccess: (_, id) => {
      if (id === chatId) {
        window.location.href = '/chat';
      }
      queryClient.setQueryData(['chats'], prev => prev.filter(chat => chat.id !== id));
    }
  });

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
      deleteChatMutation.mutate(id);
    }
  };

  return (
    <div className="bg-base-200 w-160 h-full flex flex-col">
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
