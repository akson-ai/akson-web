import { useState, useEffect, useRef } from "react";
import { useSuspenseQuery, useMutation } from "@tanstack/react-query";
import ChatMessage from "./ChatMessage";
import { API_BASE_URL } from "../constants";

function ChatContent({ chatId }) {
  const abortControllerRef = useRef(null);
  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState("");
  const [selectedAssistant, setSelectedAssistant] = useState(undefined);
  const [scrolledToBottom, setScrolledToBottom] = useState(true);
  const chatHistoryRef = useRef(null);
  const messageInputRef = useRef(null);
  const { data: assistants } = useSuspenseQuery({ queryKey: ["assistants"] });
  const { data: state } = useSuspenseQuery({ queryKey: [chatId, "state"] });

  useEffect(() => {
    document.title = state.title;
    setSelectedAssistant(state.assistant);
    setMessages(
      state.messages.map((msg) => ({
        id: msg.id,
        role: msg.role,
        name: msg.name,
        content: msg.content,
        category: msg.category,
      })),
    );
  }, [state]);

  const updateAssistantMutation = useMutation({
    mutationFn: async (assistant) => {
      await fetch(`${API_BASE_URL}/${chatId}/assistant`, {
        method: "PUT",
        credentials: "include",
        body: assistant,
      });
    },
  });

  const sendMessageMutation = useMutation({
    mutationFn: async (message) => {
      await fetch(`${API_BASE_URL}/${chatId}/message`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify(message),
        signal: abortControllerRef.current.signal,
      });
    },
  });

  const deleteMessageMutation = useMutation({
    mutationFn: async (messageId) => {
      await fetch(`${API_BASE_URL}/${chatId}/message/${messageId}`, {
        method: "DELETE",
        credentials: "include",
      });
    },
    onSuccess: (_, messageId) => {
      setMessages((prev) => prev.filter((msg) => msg.id !== messageId));
    },
  });

  const createNewChat = () => {
    window.location.href = "/chat";
  };

  useEffect(() => {
    // Set up SSE listener
    const eventSource = new EventSource(`${API_BASE_URL}/${chatId}/events`, {
      withCredentials: true,
    });
    eventSource.onmessage = function (event) {
      const data = JSON.parse(event.data);
      console.log(data);

      if (data.type === "begin_message") {
        setMessages((prev) => [
          ...prev,
          {
            id: data.id,
            role: data.role,
            name: data.name,
            content: "",
            category: data.category,
          },
        ]);
      } else if (data.type === "clear") {
        setMessages([]);
      } else if (data.type === "add_chunk") {
        // Append chunk to the last message
        setMessages((prev) => {
          const updated = [...prev];
          const i = updated.length - 1;
          updated[i] = {
            ...updated[i],
            content: updated[i].content + data.chunk,
          };
          return updated;
        });
      } else if (data.type === "end_message") {
        // TODO handle end_message in web app
      }
    };

    return () => {
      eventSource.close();
    };
  }, [chatId]);

  // Add a separate useEffect for the keyboard shortcut
  useEffect(() => {
    const handleNewChatShortcut = (e) => {
      // Check for Cmd+Shift+O (Mac) or Ctrl+Shift+O (Windows/Linux)
      if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key === "o") {
        e.preventDefault();
        createNewChat();
      }
    };

    window.addEventListener("keydown", handleNewChatShortcut);

    return () => {
      window.removeEventListener("keydown", handleNewChatShortcut);
    };
  }, []);

  // Add a separate useEffect for keyboard shortcuts
  useEffect(() => {
    const handleKeyboardShortcuts = (e) => {
      // Check for Shift+Esc to focus input
      if (e.shiftKey && e.key === "Escape") {
        e.preventDefault();
        if (messageInputRef.current) {
          messageInputRef.current.focus();
        }
      }

      // Check for Escape to abort current request
      if (e.key === "Escape" && abortControllerRef.current) {
        abortControllerRef.current.abort();
        abortControllerRef.current = null;
      }
    };

    window.addEventListener("keydown", handleKeyboardShortcuts);

    return () => {
      window.removeEventListener("keydown", handleKeyboardShortcuts);
    };
  }, []);

  // Add scroll event listener to track when user scrolls
  useEffect(() => {
    const chatHistory = chatHistoryRef.current;
    if (!chatHistory) return;

    const handleScroll = () => {
      const { scrollTop, scrollHeight, clientHeight } = chatHistory;
      const isAtBottom = scrollHeight <= scrollTop + clientHeight;
      setScrolledToBottom(isAtBottom);
    };

    chatHistory.addEventListener("scroll", handleScroll);
    return () => chatHistory.removeEventListener("scroll", handleScroll);
  }, []);

  // Scroll to bottom when messages change, but only if already at bottom
  useEffect(() => {
    if (chatHistoryRef.current && scrolledToBottom) {
      chatHistoryRef.current.scrollTop = chatHistoryRef.current.scrollHeight;
    }
  }, [messages, scrolledToBottom]);

  const sendMessage = () => {
    if (!inputText.trim()) return;

    // Generate a unique ID for the message
    const messageId = crypto.randomUUID();

    // Add message to UI with the generated ID
    setMessages((prev) => [
      ...prev,
      {
        id: messageId,
        role: "user",
        name: "You",
        content: inputText,
      },
    ]);

    // Create new AbortController for this request
    abortControllerRef.current = new AbortController();

    sendMessageMutation.mutate({
      id: messageId,
      content: inputText,
      assistant: selectedAssistant,
    });

    setInputText("");
  };

  const deleteMessage = (messageId) => {
    if (!confirm("Are you sure you want to delete this message?")) {
      return;
    }
    deleteMessageMutation.mutate(messageId);
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
              updateAssistantMutation.mutate(assistant);
              document.getElementById("messageInput").focus();
            }}
          >
            {assistants.map((assistant) => (
              <option key={assistant.name} value={assistant.name}>
                {assistant.name}
              </option>
            ))}
          </select>
        </div>
        <div className="navbar-end">
          <div className="tooltip tooltip-left" data-tip="New chat">
            <button
              className="btn btn-ghost btn-circle"
              onClick={createNewChat}
            >
              <i className="fas fa-comment-medical text-lg"></i>
            </button>
          </div>
        </div>
      </div>

      <div className="flex flex-col max-w-5xl mx-auto h-[calc(100vh-64px)] w-full">
        <div
          id="chatHistory"
          className="p-4 overflow-y-auto flex-grow"
          ref={chatHistoryRef}
        >
          {messages.map((msg) => (
            <ChatMessage
              id={msg.id}
              key={msg.id}
              role={msg.role}
              content={msg.content}
              name={msg.name}
              category={msg.category}
              onDelete={deleteMessage}
            />
          ))}
        </div>
        <div id="chatControls" className="flex flex-col mt-auto p-4 space-y-2">
          <div className="flex flex-col space-y-2">
            <label className="form-control w-full">
              <div className="flex space-x-2">
                <textarea
                  id="messageInput"
                  ref={messageInputRef}
                  className="textarea textarea-bordered flex-1 min-h-12 max-h-48"
                  placeholder="Type your message... (Shift+Enter for new line)"
                  value={inputText}
                  onChange={(e) => {
                    setInputText(e.target.value);
                    // Auto-resize the textarea
                    e.target.style.height = "auto";
                    e.target.style.height =
                      Math.min(e.target.scrollHeight, 192) + "px";
                  }}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      sendMessage();
                    }
                  }}
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
