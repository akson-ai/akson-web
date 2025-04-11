import { useEffect } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import "./App.css";
import Drawer from "./components/Drawer";
import ChatContent from "./components/ChatContent";
import KeyboardShortcutsModal from "./components/KeyboardShortcutsModal";
import { API_BASE_URL } from "./constants";

// TODO allow editing of messages
// TODO allow forking of chats
// TODO when new chat is persisted, reload chat history
// TODO fix jumping to button when streaming
// TODO add "trim history" button
// TODO add "summarize history" button
// TODO format and colorize structured output chat bubbles

// Redirect from root path to /chat with a new UUID
// or generate new UUID if at /chat without ID
if (
  window.location.pathname === "/" ||
  (window.location.pathname === "/chat" &&
    !new URLSearchParams(window.location.search).get("id"))
) {
  const newId = crypto.randomUUID();
  window.location.href = `/chat?id=${newId}`;
}

const defaultQueryFn = async ({ queryKey }) => {
  const endpoint = queryKey.join("/");
  const response = await fetch(`${API_BASE_URL}/${endpoint}`, {
    credentials: "include",
  });
  return await response.json();
};

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      queryFn: defaultQueryFn,
    },
  },
});

function App() {
  const urlParams = new URLSearchParams(window.location.search);
  const chatId = urlParams.get("id");

  useEffect(() => {
    const handleKeyDown = (e) => {
      // Add shortcut for keyboard shortcuts modal
      if ((e.metaKey || e.ctrlKey) && e.key === "/") {
        e.preventDefault();
        document.getElementById("shortcuts_modal").showModal();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  return (
    <QueryClientProvider client={queryClient}>
      <Drawer chatId={chatId}>
        <ChatContent chatId={chatId} />
      </Drawer>

      <KeyboardShortcutsModal />

      {/* Keyboard shortcuts hint button */}
      <div
        className="fixed bottom-4 right-4 btn btn-sm btn-ghost opacity-60 hover:opacity-100"
        onClick={() => document.getElementById("shortcuts_modal").showModal()}
      >
        <i className="fas fa-keyboard mr-1"></i>
        <span>⌘ + /</span>
      </div>
    </QueryClientProvider>
  );
}

export default App;
