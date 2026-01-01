# Real-Time Progress Updates

**Context**: Options for showing progress during long-running operations (sync, ingestion).

---

## Three Approaches

| Method | Direction | Complexity | Auto-Reconnect | Use Case |
|--------|-----------|------------|----------------|----------|
| **Polling** | Client → Server | Low | N/A | Simple progress, short jobs |
| **SSE** | Server → Client | Medium | Built-in | One-way updates, notifications |
| **WebSocket** | Bi-directional | High | Manual | Chat, multiplayer, real-time collab |

---

## AWS Lambda Limitations

| Component | Timeout | Notes |
|-----------|---------|-------|
| API Gateway (REST/HTTP) | 29-30s | Hard limit, cannot increase |
| Lambda execution | Up to 15 min | Configurable |

**Key insight**: API Gateway cuts the *connection* at 30s, but Lambda can keep *running* in background.

**SSE limitation**: Cannot reconnect to same Lambda instance - each reconnect spawns new instance.

---

## Industry Pattern for Long-Running Jobs

```
POST /start → job_id (immediate response)
       ↓
Worker Lambda (async) → writes progress to DB
       ↓
Frontend polls/SSE → reads progress from DB
```

**Used by**: Vercel (builds), GitHub Actions, AWS CodeBuild, Stripe, Heroku

### Architecture

```
┌──────────┐  POST /start   ┌─────────────┐  Invoke async  ┌────────────────┐
│ Frontend │───────────────▶│ API Lambda  │───────────────▶│ Worker Lambda  │
└──────────┘                │ returns id  │                │ (up to 15 min) │
     │                      └─────────────┘                └───────┬────────┘
     │                                                             │
     │  Poll or SSE /progress/{id}                                 │
     │                                                             │
     │                      ┌─────────────┐                        │
     └─────────────────────▶│  Streamer   │                        │
                            │  Lambda     │◀───────────────────────┘
                            └──────┬──────┘     writes progress
                                   │
                                   ▼
                            ┌─────────────┐
                            │ PostgreSQL  │
                            └─────────────┘
```

---

## SSE with Auto-Reconnect

SSE has built-in reconnect using `Last-Event-ID` header:

```python
# Server sends event with ID
yield f"id: {progress['processed']}\n"
yield f"data: {json.dumps(progress)}\n\n"

# On reconnect, browser sends Last-Event-ID header
# Server resumes from that point
```

```javascript
// Browser auto-reconnects
const source = new EventSource('/api/progress/123');
source.onmessage = (e) => setProgress(JSON.parse(e.data));
```

**Reconnect behavior**: Default 3s delay, customizable via `retry:` field.

---

## WebSocket API Gateway (AWS Free Tier Option)

API Gateway manages WebSocket connections, Lambda handles events:

| Event | Lambda Invoked | Purpose |
|-------|----------------|---------|
| `$connect` | Yes | Store connectionId |
| `$disconnect` | Yes | Remove connectionId |
| `$default` | Yes | Handle client messages |
| Server push | No | Call `post_to_connection()` API |

**Connection storage**: Can use PostgreSQL (existing DB) instead of DynamoDB.

---

## When to Use What

| Use Case | Recommended | Why |
|----------|-------------|-----|
| Progress bar (<30s) | Simple request/response | Fast enough |
| Progress bar (>30s) | Polling or SSE + reconnect | One-way, simple |
| Chat application | WebSocket | Bi-directional |
| Multiplayer editing | WebSocket | Bi-directional + low latency |
| Notifications | SSE | One-way push |

---

## Browser Connection Limits

| Protocol | Limit per Domain | Notes |
|----------|------------------|-------|
| HTTP/1.1 (SSE) | 6 connections | Shared across all tabs |
| HTTP/2 | 100+ | Multiplexed |
| WebSocket | No hard limit | Separate from HTTP |

---

## References

- [MDN: Server-Sent Events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events)
- [AWS: WebSocket API Gateway](https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-websocket-api.html)
