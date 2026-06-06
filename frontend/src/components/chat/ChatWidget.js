/**
 * ChatWidget — floating chat assistant (lower-right of the Search page). Phase 6C.
 *
 * States: closed (pill launcher) → open (panel) → minimized (bar). Close prompts a
 * confirm (ends the chat / loses context) and starts a NEW session next open.
 *
 * History lives in Redis (backend source of truth, ADR-027); this widget only
 * renders. sessionId is tab-tied (sessionStorage). Streaming uses fetch+ReadableStream
 * (POST + Bearer, so not EventSource — see chatStream.js).
 */

import React, { useState, useRef, useEffect, useCallback } from 'react';
import { streamChatTurn, fetchSession } from './chatStream';
import './ChatWidget.css';

const CHAT_URL = process.env.REACT_APP_CHAT_URL;

// sessionStorage keys (tab-scoped, survive refresh, clear on tab close).
const SID_KEY = 'chat_session_id';
const OPEN_KEY = 'chat_widget_state'; // 'closed' | 'open' | 'min'

function newSessionId() {
  const id = (crypto.randomUUID && crypto.randomUUID()) || `sid-${Date.now()}-${Math.random()}`;
  sessionStorage.setItem(SID_KEY, id);
  return id;
}
function getSessionId() {
  return sessionStorage.getItem(SID_KEY) || newSessionId();
}

export default function ChatWidget() {
  const [widgetState, setWidgetState] = useState(() => sessionStorage.getItem(OPEN_KEY) || 'closed');
  const [sessionId, setSessionId] = useState(getSessionId);
  const [messages, setMessages] = useState([]); // {role, content, steps, interrupted}
  const [streaming, setStreaming] = useState(false);
  const [input, setInput] = useState('');
  const [showCloseConfirm, setShowCloseConfirm] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // Auto-grow the textarea up to its CSS max-height (~4 lines), then it scrolls.
  const autoResize = () => {
    const el = inputRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${el.scrollHeight}px`;
  };

  const token = localStorage.getItem('access_token');

  // Persist widget open/min/closed across refresh.
  useEffect(() => {
    sessionStorage.setItem(OPEN_KEY, widgetState);
  }, [widgetState]);

  // Load existing history when the panel opens (backend is source of truth).
  const loadHistory = useCallback(async () => {
    if (!CHAT_URL || !token) return;
    const data = await fetchSession({ chatUrl: CHAT_URL, token, sessionId });
    if (data?.session?.messages) {
      setMessages(data.session.messages.map((m) => ({
        role: m.role, content: m.content, interrupted: m.interrupted,
      })));
    }
  }, [sessionId, token]);

  useEffect(() => {
    if (widgetState === 'open') loadHistory();
  }, [widgetState, loadHistory]);

  // Auto-scroll to bottom as content streams.
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Debug: fetch the stored Redis session blob (via GET /session — same prod path,
  // JWT-authed) and print it inline as a transient debug message (not persisted,
  // not re-sent to the model — diagnostic only).
  const dumpDebug = async () => {
    const data = await fetchSession({ chatUrl: CHAT_URL, token, sessionId });
    const dump = data ? JSON.stringify(data, null, 2) : '(no session data / fetch failed)';
    setMessages((prev) => [...prev, { role: 'debug', content: dump }]);
  };

  const send = async () => {
    const text = input.trim();
    if (!text || streaming) return;
    setInput('');
    if (inputRef.current) inputRef.current.style.height = 'auto'; // reset to 1 line
    setMessages((prev) => [...prev, { role: 'user', content: text }]);
    setStreaming(true);

    // Placeholder assistant bubble we stream tokens + steps into. Steps are kept
    // ON the message so they persist as a record of how the answer was produced.
    let answer = '';
    const turnSteps = [];
    setMessages((prev) => [...prev, { role: 'assistant', content: '', steps: [], streaming: true }]);

    const updateLast = (patch) => {
      setMessages((prev) => {
        const copy = [...prev];
        copy[copy.length - 1] = { ...copy[copy.length - 1], ...patch };
        return copy;
      });
    };

    try {
      await streamChatTurn({
        chatUrl: CHAT_URL,
        token,
        sessionId,
        message: text,
        onEvent: (evt) => {
          if (evt.type === 'step') {
            turnSteps.push(evt.data);
            updateLast({ steps: [...turnSteps] });
          } else if (evt.type === 'token') {
            answer += evt.data;
            updateLast({ content: answer });
          } else if (evt.type === 'error') {
            answer += `\n[error: ${evt.data}]`;
            updateLast({ content: answer });
          } else if (evt.type === 'interrupted') {
            updateLast({ interrupted: true, streaming: false });
          }
        },
      });
    } catch (err) {
      answer += `\n[connection error]`;
      updateLast({ content: answer });
    } finally {
      updateLast({ streaming: false });
      setStreaming(false);
    }
  };

  const onKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  const confirmClose = () => {
    // End chat: new session next open, clear local view.
    const id = newSessionId();
    setSessionId(id);
    setMessages([]);
    setShowCloseConfirm(false);
    setWidgetState('closed');
  };

  // ---- Render ----
  if (widgetState === 'closed') {
    return (
      <button className="chat-launcher" onClick={() => setWidgetState('open')}>
        💬 Job Assistant
      </button>
    );
  }

  if (widgetState === 'min') {
    return (
      <div className="chat-minbar" onClick={() => setWidgetState('open')}>
        <span>💬 Job Assistant</span>
        <button className="chat-icon-btn" title="Expand">▢</button>
      </div>
    );
  }

  return (
    <div className="chat-panel">
      <div className="chat-header">
        <div className="chat-header-left">
          <span className="chat-title">💬 Job Assistant</span>
          <span className="chat-session-id">session: {sessionId}</span>
        </div>
        <div className="chat-header-btns">
          <button className="chat-icon-btn" title="Debug: dump Redis session" onClick={dumpDebug}>🐛</button>
          <button className="chat-icon-btn" title="Minimize" onClick={() => setWidgetState('min')}>—</button>
          <button className="chat-icon-btn" title="Close" onClick={() => setShowCloseConfirm(true)}>✕</button>
        </div>
      </div>

      <div className="chat-messages">
        {messages.length === 0 && (
          <div className="chat-empty">
            <div>Ask about your tracked jobs or how your resume fits a role.</div>
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`chat-msg chat-msg-${m.role}`}>
            {m.role === 'debug' ? (
              <div className="chat-debug">
                <div className="chat-debug-label">🐛 Redis session dump</div>
                <pre className="chat-debug-body">{m.content}</pre>
              </div>
            ) : (
              <>
                {m.role === 'assistant' && m.steps && m.steps.length > 0 && (
                  <div className="chat-steps">
                    {m.steps.map((s, j) => <div key={j} className="chat-step">• {s}</div>)}
                  </div>
                )}
                <div className="chat-bubble">
                  {m.content || (m.streaming ? <span className="chat-cursor">▌</span> : '')}
                  {m.interrupted && <span className="chat-interrupted"> (interrupted)</span>}
                </div>
              </>
            )}
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input-row">
        <textarea
          ref={inputRef}
          className="chat-input"
          placeholder={streaming ? 'Waiting for response…' : 'Type a message…'}
          value={input}
          onChange={(e) => { setInput(e.target.value); autoResize(); }}
          onKeyDown={onKeyDown}
          disabled={streaming}
          rows={1}
        />
        <button className="chat-send" onClick={send} disabled={streaming || !input.trim()}>↑</button>
      </div>

      {showCloseConfirm && (
        <div className="chat-confirm-overlay">
          <div className="chat-confirm">
            <p>End this chat? The current conversation and its context will be lost — a new chat starts next time.</p>
            <div className="chat-confirm-btns">
              <button className="chat-confirm-cancel" onClick={() => setShowCloseConfirm(false)}>Cancel</button>
              <button className="chat-confirm-end" onClick={confirmClose}>End chat</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
