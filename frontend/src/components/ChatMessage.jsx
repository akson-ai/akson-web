import { useState } from 'react';
import Markdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';

function ChatMessage({ id, role, name, content, category, onDelete }) {
  const [isHovered, setIsHovered] = useState(false);

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
      <div className={`chat-bubble mt-1 ${category ? `chat-bubble-${category}` : ''}`}>
        {!content ? (
          <div className="flex items-center">
            <div className="loading loading-spinner loading-sm mr-2"></div>
            <span>Thinking...</span>
          </div>
        ) : (
          <div className="prose">
            <Markdown
              components={{
                code({node, className, children, ...props}) {
                  const match = /language-(\w+)/.exec(className || '')
                  return match ? (
                    <SyntaxHighlighter
                      style={vscDarkPlus}
                      language={match[1]}
                      {...props}
                    >
                      {String(children).replace(/\n$/, '')}
                    </SyntaxHighlighter>
                  ) : (
                    <code className={className} {...props}>
                      {children}
                    </code>
                  )
                }
              }}
            >
              {content}
            </Markdown>
          </div>
        )}
      </div>
      {content && (
        <div className={`chat-footer mt-1 ${isHovered ? 'visible' : 'invisible'}`}>
          <>
            <button
              className="btn btn-xs btn-ghost btn-square"
              onClick={() => navigator.clipboard.writeText(content)}
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

export default ChatMessage;
