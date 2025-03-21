// TODO allow editing of messages
// TODO allow forking of chats
// TODO handle markdown in message
// TODO when new chat is persisted, reload chat history
// TODO highlight code blocks
// TODO fix jumping to button when streaming
// TODO add "trim history" button
// TODO add "summarize history" button
// TODO ask confirmation when deleting single message

import React from 'react';
import {createRoot} from 'react-dom/client';

// Render your app
const root = createRoot(document.getElementById('root'));
root.render(<ChatApp />);
