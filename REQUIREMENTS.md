# Golden Incubator — Requirements Pivot

## What It Is

A **collaborative requirements gathering tool** where a user and an AI agent work together through conversation to produce a clean, comprehensive requirements document. That's it — no architecture, no infrastructure, no deployment, no code generation.

## UX: Split-Screen Layout

The entire app is one screen, split 50/50:

```
┌─────────────────────┬─────────────────────┐
│                     │                     │
│    Chat Panel       │  Requirements Doc   │
│                     │   (live markdown)   │
│  [user messages]    │                     │
│  [agent responses]  │  ## Overview        │
│  [questions]        │  ## Users           │
│                     │  ## User Stories     │
│                     │  ## Business Rules   │
│                     │  ## Constraints      │
│  ________________   │  ## Open Questions   │
│  |  Type here... |  │                     │
│  |_______________|  │  [changes highlight] │
└─────────────────────┴─────────────────────┘
```

- **Left panel**: Chat interface. User describes what they want, agent asks clarifying questions, they iterate together.
- **Right panel**: Requirements markdown document. Updates in real-time as the conversation progresses. User can see changes as they happen.

## How It Works

1. User creates a new session (gives it a name like "My App Idea")
2. Agent starts with an open-ended prompt: "Tell me about what you want to build"
3. As the user talks, the agent:
   - Asks smart follow-up questions
   - Identifies gaps and edge cases
   - Fills in sections of the requirements doc progressively
4. The right panel updates live — user sees the doc evolving
5. When the doc is complete, user can export it as a `.md` file

## The Requirements Template

The agent starts with this skeleton and fills it in as the conversation progresses:

```markdown
# [Project Name]

## Overview
Brief description of what this product does and why it exists.

## Target Users
Who is this for? User personas and their goals.

## User Stories
As a [user type], I want to [action] so that [benefit].

## Features & Capabilities
What the product does, organized by area.

## Business Rules
Logic, constraints, and rules that govern how things work.

## Data & Content
What data does the system manage? What content does it display?

## Integrations
External systems, APIs, or services this needs to connect with.

## Constraints & Assumptions
Known limitations, assumptions we're making, things explicitly out of scope.

## Success Criteria
How do we know this is done and working?

## Open Questions
Things we still need to figure out.
```

## Backend Architecture

### API Endpoints
- `POST /api/sessions` — Create a new requirements session
- `GET /api/sessions` — List user's sessions
- `GET /api/sessions/:id` — Get session with chat history + current doc
- `POST /api/sessions/:id/messages` — Send a chat message
- `GET /api/sessions/:id/document` — Get the current requirements doc
- `DELETE /api/sessions/:id` — Delete a session
- `GET /api/sessions/:id/export` — Export requirements as markdown file

### WebSocket
- `WS /api/sessions/:id/ws` — Real-time updates for chat responses and document changes
- When user sends a message, backend:
  1. Saves the message
  2. Calls Claude API with full conversation + current doc state
  3. Claude returns: chat response + updated requirements markdown
  4. Backend pushes both to frontend via WebSocket
  5. Saves updated doc version

### Data Models

**Session**
```
- id
- user_id
- name (user-provided project name)
- created_at
- updated_at
```

**Message**
```
- id
- session_id
- role (user | assistant)
- content
- created_at
```

**Document**
```
- id
- session_id
- content (markdown string)
- version (incrementing integer)
- created_at
```

### Claude Integration
- System prompt instructs Claude to act as a requirements analyst
- Each request includes: system prompt + conversation history + current doc state
- Claude responds with JSON: `{ "reply": "...", "document": "..." }`
- The `reply` goes to chat, the `document` replaces the current doc content

## Frontend

### Tech
- React + TypeScript (already in place)
- WebSocket client for real-time updates
- Markdown renderer for the right panel (e.g., `react-markdown`)
- Diff highlighting for recently changed sections (optional but nice)

### Views
- **Session List** — Simple list of the user's sessions, create new
- **Session View** — The split-screen (this is 95% of the app)
- **Auth** — Login/register (already exists)

### Key Interactions
- User types message → sends via WebSocket → gets chat response + doc update
- Right panel re-renders markdown on every doc update
- Optional: briefly highlight/flash sections that just changed
- Export button downloads the current doc as `[session-name]-requirements.md`

## What to Keep from Current Codebase
- Auth system (login, register, JWT)
- FastAPI + MongoDB + React stack
- Docker setup
- Basic project/session CRUD patterns

## What to Remove
- Entities system
- Architecture/build/deploy phases
- Progress tracking
- Template system
- Artifact system
- Most current conversation flow logic

## What to Add
- WebSocket support (FastAPI `WebSocket` endpoint)
- Claude API integration (anthropic Python SDK)
- Markdown renderer in frontend
- Split-screen layout component
- Document versioning

## Environment Variables
```
ANTHROPIC_API_KEY=sk-ant-...
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB_NAME=golden-incubator
JWT_SECRET=...
```

## Non-Goals (Explicitly Out of Scope)
- Code generation
- Architecture decisions
- Infrastructure/deployment
- Project management
- Technical implementation details
- Building or running the software described in the requirements
