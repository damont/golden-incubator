# Application Architecture Guide

How we build full-stack applications in the household project, based on the patterns established in `calendarapp` and `track`.

---

## Core Principles

1. **API-first** -- The backend is a standalone REST API. It must work completely without the frontend (testable via curl, Postman, or Claude).
2. **Separate concerns** -- Backend and frontend are independent build targets in the same repo. They share nothing except an HTTP contract.
3. **Mobile-first** -- Design for phone screens first, then enhance for larger viewports. Use Tailwind's responsive prefixes (`sm:`, `md:`, `lg:`) to add desktop layout, not the other way around.
4. **URL-driven navigation** -- Every distinct view and detail page has its own URL. Browser back/forward, page refresh, and deep-linking must all work. Use the History API directly via a lightweight custom hook -- no router library needed.
5. **Docker Compose for local dev** -- Every app runs locally via `docker-compose.yml`. Production deployment depends on the app -- see [Deployment](#deployment).
6. **Keep it simple** -- No ORMs with migrations, no Redux, no GraphQL. MongoDB documents, React Context, and REST endpoints.

---

## Tech Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| Language (backend) | Python >= 3.12 | Use the most stable release available |
| Package manager | uv | Fast, lockfile-based, replaces pip/poetry |
| Web framework | FastAPI | Async, auto-generates OpenAPI docs |
| Database | MongoDB | Via async Motor driver |
| ODM | Beanie | Pydantic-based document models |
| Auth | JWT (PyJWT) + Argon2 (argon2-cffi) | See auth section below |
| Config | pydantic-settings | Reads from `.env` files |
| Frontend framework | React 19 + TypeScript | Vite for bundling |
| Styling | Tailwind CSS v4 | Utility-first, no custom CSS framework |
| Containerization | Docker + Docker Compose | Multi-stage builds |
| Deployment target | Raspberry Pi **or** Azure | See [Deployment](#deployment) |

---

## Project Structure

Every new app follows this layout:

```
<appname>/
├── api/
│   ├── __init__.py
│   ├── main.py              # FastAPI app, lifespan, router includes
│   ├── config.py            # pydantic-settings, reads .env
│   ├── routes/
│   │   ├── auth.py          # Login/register endpoints
│   │   └── <resource>.py    # One file per resource (tasks, weeks, etc.)
│   ├── schemas/
│   │   ├── orm/             # Beanie Document models (database shape)
│   │   │   └── <model>.py
│   │   └── dto/             # Request/response Pydantic models
│   │       └── <model>.py
│   ├── services/            # Business logic (optional, use when routes get complex)
│   │   └── <service>.py
│   └── utils/
│       └── auth.py          # JWT creation/validation, password hashing
├── frontend/
│   ├── src/
│   │   ├── main.tsx         # React entry point
│   │   ├── App.tsx          # Root component, auth gating, top-level routing
│   │   ├── index.css        # Tailwind import + CSS variables
│   │   ├── api/
│   │   │   └── client.ts    # HTTP client wrapper
│   │   ├── hooks/
│   │   │   └── useRouter.ts # URL-based navigation (History API wrapper)
│   │   ├── context/
│   │   │   └── AuthContext.tsx
│   │   ├── types/
│   │   │   └── index.ts     # TypeScript interfaces matching API shapes
│   │   └── components/
│   │       ├── auth/        # Login, Register, LandingPage
│   │       ├── layout/      # AppLayout, Header
│   │       └── <feature>/   # Feature-specific components
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   └── nginx.conf           # Production nginx for SPA + API proxy
├── Dockerfile               # Multi-stage: backend, frontend-build, frontend
├── docker-compose.yml
├── pyproject.toml
├── uv.lock
├── .env.example
├── .gitignore
│
│   # Azure deployment only (see Deployment section):
├── Dockerfile.api           # Standalone API image
├── Dockerfile.frontend      # Standalone frontend/nginx image
├── infra/
│   ├── providers.tf         # Azure provider + backend config
│   ├── variables.tf         # Terraform variable definitions
│   ├── main.tf              # ACI container group, data sources, locals
│   ├── outputs.tf           # FQDN, IP address
│   └── terraform.tfvars     # Non-secret prod defaults
└── .github/
    └── workflows/
        ├── deploy.yml       # Prod: push to main → build → terraform apply
        └── deploy-dev.yml   # Dev: PR opened → build → terraform apply
```

---

## Backend

### FastAPI App Entry Point

`api/main.py` sets up the app with a lifespan handler for MongoDB initialization:

```python
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie

from api.config import get_settings
from api.schemas.orm.thing import Thing
from api.routes import auth, things

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    client = AsyncIOMotorClient(settings.mongodb_url)
    await init_beanie(
        database=client[settings.mongodb_db_name],
        document_models=[Thing],  # Register all Beanie documents here
    )
    logger.info("Connected to MongoDB database: %s", settings.mongodb_db_name)
    yield
    client.close()
    logger.info("Disconnected from MongoDB")

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(things.router, prefix="/api/things", tags=["things"])

@app.get("/api/health")
async def health_check():
    return {"status": "ok"}
```

### Configuration

`api/config.py` uses pydantic-settings to load environment variables:

```python
from functools import lru_cache
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    mongodb_url: str = "mongodb://localhost:27017"
    mongodb_db_name: str = "myapp"
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 10080  # 7 days

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

@lru_cache
def get_settings() -> Settings:
    return Settings()
```

### Database Design Diagram

Before writing any Beanie models, create a draw.io (`.drawio`) diagram in the app root that shows the database objects and their relationships. This serves as a visual reference for how documents relate to each other and what gets nested vs. stored separately.

The diagram should include:
- Each MongoDB document (Beanie `Document` subclass) as a box with its fields and types
- Nested models (`BaseModel` subclasses embedded inside documents) shown as contained boxes or with composition arrows
- Relationships between documents (e.g., `user_id` references) shown as association arrows
- Collection names labeled on each document box

Save the file as `<appname>/database-design.drawio` and keep it updated as the schema evolves. This makes it easy for anyone (including Claude) to understand the data model at a glance without reading through all the ORM files.

### Database Models (Beanie Documents)

Place these in `api/schemas/orm/`. Each document maps to a MongoDB collection:

```python
from datetime import datetime, timezone
from typing import Optional
from beanie import Document, Indexed
from pydantic import BaseModel, Field

class Step(BaseModel):
    """Nested model -- stored inside the parent document, not its own collection."""
    id: str
    description: str
    completed: bool = False

class Thing(Document):
    name: str
    user_id: Indexed(str)
    description: Optional[str] = None
    steps: list[Step] = []
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "things"  # MongoDB collection name
```

Key patterns:
- Use `Indexed()` for fields you query on frequently.
- Nest related data (steps, references, history entries) as `BaseModel` lists inside the document rather than separate collections.
- Keep `created_at` and `updated_at` on every document.

### DTOs (Request/Response Models)

Place these in `api/schemas/dto/`. Separate from ORM models so the API shape can differ from the database shape:

```python
from pydantic import BaseModel
from typing import Optional

class ThingCreate(BaseModel):
    name: str
    description: Optional[str] = None

class ThingUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class ThingResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    created_at: str
```

### Routes

One file per resource in `api/routes/`. Use FastAPI's dependency injection for auth:

```python
from fastapi import APIRouter, Depends, HTTPException
from api.schemas.orm.thing import Thing
from api.schemas.dto.thing import ThingCreate, ThingResponse
from api.utils.auth import get_current_user

router = APIRouter()

@router.get("/", response_model=list[ThingResponse])
async def list_things(user=Depends(get_current_user)):
    things = await Thing.find(Thing.user_id == str(user.id)).to_list()
    return [thing_to_response(t) for t in things]

@router.post("/", response_model=ThingResponse, status_code=201)
async def create_thing(data: ThingCreate, user=Depends(get_current_user)):
    thing = Thing(name=data.name, description=data.description, user_id=str(user.id))
    await thing.insert()
    return thing_to_response(thing)
```

Conventions:
- All routes are prefixed in `main.py` (e.g., `/api/things`).
- Return DTOs, not raw Beanie documents.
- Use `Depends(get_current_user)` on every protected route.
- Standard HTTP methods: GET (list/detail), POST (create), PUT (update), DELETE (delete).
- Pagination via `?skip=0&limit=20` query params on list endpoints.

### Authentication

Use **Argon2** for password hashing (not bcrypt/passlib -- there are compatibility issues with bcrypt 5.x):

```python
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from api.config import get_settings

ph = PasswordHasher()
security = HTTPBearer()

def hash_password(password: str) -> str:
    return ph.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        ph.verify(hashed_password, plain_password)
        return True
    except VerifyMismatchError:
        return False

def create_access_token(subject: str) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    settings = get_settings()
    try:
        payload = jwt.decode(
            credentials.credentials, settings.jwt_secret,
            algorithms=[settings.jwt_algorithm]
        )
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    # Look up user from database here
    user = await User.get(user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user
```

### Logging

All apps use Python's built-in `logging` module. Logs go to stdout, where Docker captures them. No file-based logging -- Docker handles rotation and storage.

#### Setup

Configure logging once in `api/main.py`, before the app is created:

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
```

This configures the root logger. Uvicorn's access logs (request method, path, status code) are already included -- this adds application-level logging on top.

#### Usage in modules

In any module that needs logging, create a module-level logger:

```python
import logging

logger = logging.getLogger(__name__)
```

Then log significant events and errors:

```python
# In routes or services:

# Significant state changes
logger.info("Task %s marked complete by user %s", task_id, user.id)
logger.info("New user registered: %s", username)

# Things that might need investigation
logger.warning("User %s attempted to access task %s owned by another user", user.id, task_id)

# Errors that don't crash the app but indicate problems
logger.error("Failed to send notification for task %s: %s", task_id, str(e))

# Unexpected exceptions (include stack trace)
try:
    await some_operation()
except Exception:
    logger.exception("Unexpected error during some_operation")
    raise
```

#### What to log

- **User actions that change state**: created, updated, deleted, completed resources
- **Authentication events**: login, failed login, registration
- **Authorization failures**: user tried to access something they shouldn't
- **External service errors**: if an app calls another app's API and it fails
- **Startup/shutdown**: app started, connected to database, shutting down

#### What NOT to log

- **Every request** -- uvicorn already does this
- **Request/response bodies** -- can contain passwords or personal data
- **Successful reads** -- too noisy, no diagnostic value
- **Anything at DEBUG level in production** -- keep the log level at INFO

#### Docker log rotation

To prevent logs from filling the Pi's disk, configure Docker's log rotation. Add to `/etc/docker/daemon.json` on the Pi:

```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
```

This caps each container at 30MB of logs (3 files x 10MB, rotated automatically). Restart Docker after changing this: `sudo systemctl restart docker`.

### In-App Feedback via GitHub Issues

Apps can include a feedback button that creates GitHub issues directly from the UI. This gives users a simple way to report bugs or request features without leaving the app.

#### How it works

1. User clicks a feedback button in the app header
2. A modal collects a title and description
3. The backend calls the GitHub REST API to create an issue with a "feedback" label
4. The user sees a success confirmation

#### Backend

**Config** -- add three settings to `api/config.py`:

```python
# In-app feedback → GitHub Issues
feedback_github_token: Optional[str] = None
feedback_github_repo_owner: Optional[str] = None
feedback_github_repo_name: Optional[str] = None
```

**Service** -- `api/services/github_service.py`:

```python
import httpx
import logging
from api.config import get_settings

logger = logging.getLogger(__name__)

class GitHubService:
    @staticmethod
    async def create_issue(title: str, body: str, labels: list[str] | None = None) -> dict | None:
        settings = get_settings()
        if not all([settings.feedback_github_token, settings.feedback_github_repo_owner, settings.feedback_github_repo_name]):
            logger.warning("GitHub feedback not configured")
            return None

        url = f"https://api.github.com/repos/{settings.feedback_github_repo_owner}/{settings.feedback_github_repo_name}/issues"
        headers = {
            "Authorization": f"Bearer {settings.feedback_github_token}",
            "Accept": "application/vnd.github.v3+json",
        }
        payload = {"title": title, "body": body}
        if labels:
            payload["labels"] = labels

        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers)
            if response.status_code == 201:
                data = response.json()
                return {"number": data["number"], "url": data["html_url"]}
            logger.error("GitHub API error: %s %s", response.status_code, response.text)
            return None


async def create_feedback_issue(title: str, description: str, username: str | None = None) -> dict | None:
    body_parts = []
    if username:
        body_parts.append(f"### Submitted By\n{username}")
    body_parts.append(f"### Feedback\n{description}")
    body_parts.append("*Submitted via in-app feedback*")
    body = "\n\n".join(body_parts)
    return await GitHubService.create_issue(title, body, labels=["feedback"])
```

**Route** -- `api/routes/feedback.py`:

```python
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from api.utils.auth import get_current_user
from api.services.github_service import create_feedback_issue

router = APIRouter()

class FeedbackRequest(BaseModel):
    title: str = Field(..., max_length=200)
    description: str

class FeedbackResponse(BaseModel):
    success: bool
    issue_number: Optional[int] = None
    issue_url: Optional[str] = None
    message: str

@router.post("", response_model=FeedbackResponse)
async def submit_feedback(data: FeedbackRequest, user=Depends(get_current_user)):
    result = await create_feedback_issue(data.title, data.description, username=user.username)
    if result:
        return FeedbackResponse(
            success=True, issue_number=result["number"],
            issue_url=result["url"], message="Feedback submitted"
        )
    raise HTTPException(status_code=500, detail="Failed to submit feedback")
```

Register in `main.py`:
```python
app.include_router(feedback.router, prefix="/api/feedback", tags=["feedback"])
```

#### Frontend

Add a `FeedbackModal` component with a title input and description textarea. Wire a button in the app header to open it. On submit, call `api.post("/api/feedback", { title, description })` and show a success message before auto-closing.

#### GitHub token

Create a fine-grained personal access token with **Issues: Read and Write** permission scoped to the target repository. Add it as `FEEDBACK_GITHUB_TOKEN` in your environment. Add `httpx` to your `pyproject.toml` dependencies.

---

### Python Dependencies

`pyproject.toml` -- managed by uv:

```toml
[project]
name = "myapp"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.109.0",
    "uvicorn[standard]>=0.27.0",
    "beanie>=1.25.0",
    "motor>=3.3.0",
    "pydantic>=2.5.0",
    "pydantic-settings>=2.1.0",
    "PyJWT>=2.8.0",
    "argon2-cffi>=23.1.0",
    "python-multipart>=0.0.6",
    "httpx>=0.26.0",
]

[tool.uv]
dev-dependencies = [
    "pytest>=7.4.0",
    "anyio[trio]>=4.0.0",
    "pytest-asyncio>=0.23.0",
    "httpx>=0.26.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["api"]
```

Install and lock dependencies:

```bash
uv sync          # Install deps, create uv.lock
uv run uvicorn api.main:app --reload --port 8020   # Run dev server
```

---

## Frontend

### Vite Configuration

`frontend/vite.config.ts` -- proxy API calls to the backend during development:

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 8095,
    proxy: {
      '/api': {
        target: 'http://localhost:8020',
        changeOrigin: true,
      },
    },
  },
})
```

The proxy means the frontend can call `fetch('/api/things')` in dev without CORS issues. In production, nginx handles the same routing.

### API Client

`frontend/src/api/client.ts` -- a class that wraps fetch with token management:

```typescript
class ApiClient {
  private baseUrl = ''

  getToken(): string | null {
    return localStorage.getItem('token')
  }

  setToken(token: string) {
    localStorage.setItem('token', token)
  }

  clearToken() {
    localStorage.removeItem('token')
  }

  isAuthenticated(): boolean {
    return this.getToken() !== null
  }

  private async request<T>(method: string, path: string, body?: unknown): Promise<T> {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' }
    const token = this.getToken()
    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }

    const res = await fetch(`${this.baseUrl}${path}`, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    })

    if (res.status === 401) {
      this.clearToken()
      throw new Error('Unauthorized')
    }

    if (!res.ok) {
      throw new Error(`API error: ${res.status}`)
    }

    if (res.status === 204) return undefined as T
    return res.json()
  }

  get<T>(path: string) { return this.request<T>('GET', path) }
  post<T>(path: string, body: unknown) { return this.request<T>('POST', path, body) }
  put<T>(path: string, body: unknown) { return this.request<T>('PUT', path, body) }
  delete<T>(path: string) { return this.request<T>('DELETE', path) }
}

export const api = new ApiClient()
```

Key pattern: on a 401 response, clear the token and throw. The `AuthContext` will detect the missing token on re-render and show the login screen. Avoid `window.location.reload()` here -- it can cause infinite reload loops if the token validation request on page load also returns 401.

### Auth Context

`frontend/src/context/AuthContext.tsx` -- wraps the entire app:

```typescript
import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { api } from '../api/client'

interface AuthContextType {
  isAuthenticated: boolean
  isLoading: boolean
  user: User | null
  login: (username: string, password: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextType | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    // Check for existing token on mount
    if (api.isAuthenticated()) {
      api.get<User>('/api/auth/me')
        .then(setUser)
        .catch(() => api.clearToken())
        .finally(() => setIsLoading(false))
    } else {
      setIsLoading(false)
    }
  }, [])

  const login = async (username: string, password: string) => {
    // Call login endpoint, store token
    const res = await api.post<{ access_token: string }>('/api/auth/login', { username, password })
    api.setToken(res.access_token)
    const user = await api.get<User>('/api/auth/me')
    setUser(user)
  }

  const logout = () => {
    api.clearToken()
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ isAuthenticated: !!user, isLoading, user, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)!
```

### App Root

`frontend/src/App.tsx` -- gates the app behind authentication and routes based on the URL:

```typescript
import { useEffect } from 'react'
import { AuthProvider, useAuth } from './context/AuthContext'
import { useRouter } from './hooks/useRouter'
import { AppLayout, type View } from './components/layout/AppLayout'

const VIEWS: View[] = ['items', 'browse', 'settings']  // your app's views

function pathToView(path: string): View | null {
  const first = path.split('/').filter(Boolean)[0]
  return VIEWS.includes(first as View) ? (first as View) : null
}

function AppContent() {
  const { user, loading } = useAuth()
  const { path, navigate } = useRouter()

  // Redirect authenticated users on / or unknown paths to default view
  useEffect(() => {
    if (!loading && user && !pathToView(path)) {
      navigate('/items', true)  // replaceState, not pushState
    }
  }, [loading, user, path, navigate])

  // Redirect unauthenticated users on protected paths to /
  useEffect(() => {
    if (!loading && !user && path !== '/' && path !== '/login' && path !== '/register') {
      navigate('/', true)
    }
  }, [loading, user, path, navigate])

  if (loading) return <div>Loading...</div>
  if (!user) {
    if (path === '/login') return <Login ... />
    if (path === '/register') return <Register ... />
    return <LandingPage ... />
  }

  const currentView = pathToView(path) || 'items'
  return (
    <AppLayout currentView={currentView} onViewChange={(v) => navigate(`/${v}`)}>
      <ViewContent view={currentView} />
    </AppLayout>
  )
}
```

The key pattern: **derive the current view from the URL** rather than storing it in `useState`. The `navigate()` function updates the URL, which triggers a re-render, which reads the new view from the path. This means back/forward buttons, page refresh, and direct URL access all work automatically.

### Component Organization

Group components by feature, not by type:

```
components/
├── auth/           # Login.tsx, Register.tsx, AuthPage.tsx
├── layout/         # AppLayout.tsx, Header.tsx, Sidebar.tsx
├── tasks/          # TaskList.tsx, TaskItem.tsx, TaskDetail.tsx
└── categories/     # CategoryFilter.tsx, CategoryForm.tsx
```

Each component should:
- Be a single default export function component.
- Accept props via a typed interface.
- Use Tailwind utility classes directly -- no separate CSS files.
- Keep state local unless it needs to be shared (then lift to context).

### URL-Based Routing

Every app uses a custom `useRouter` hook that wraps the browser History API. No external router library needed.

#### The `useRouter` hook

`frontend/src/hooks/useRouter.ts`:

```typescript
import { useState, useEffect, useCallback } from 'react'

interface RouterState {
  path: string
  navigate: (path: string, replace?: boolean) => void
}

export function useRouter(): RouterState {
  const [path, setPath] = useState(() => window.location.pathname)

  useEffect(() => {
    const onPopState = () => setPath(window.location.pathname)
    window.addEventListener('popstate', onPopState)
    return () => window.removeEventListener('popstate', onPopState)
  }, [])

  const navigate = useCallback((to: string, replace = false) => {
    if (to === window.location.pathname) return
    if (replace) {
      window.history.replaceState({}, '', to)
    } else {
      window.history.pushState({}, '', to)
    }
    setPath(to)
  }, [])

  return { path, navigate }
}

export function matchPath(
  pattern: string,
  path: string,
): Record<string, string> | null {
  const patternParts = pattern.split('/').filter(Boolean)
  const pathParts = path.split('/').filter(Boolean)
  if (patternParts.length !== pathParts.length) return null
  const params: Record<string, string> = {}
  for (let i = 0; i < patternParts.length; i++) {
    if (patternParts[i].startsWith(':')) {
      params[patternParts[i].slice(1)] = pathParts[i]
    } else if (patternParts[i] !== pathParts[i]) {
      return null
    }
  }
  return params
}
```

#### URL design

Plan URL paths when designing a new app. Every navigable state should have its own path:

| Path | What it shows |
|------|---------------|
| `/items` | List view |
| `/items/new` | Create form |
| `/items/:id` | Detail view |
| `/items/:id/edit` | Edit form |

#### Deriving state from the URL

In view components, replace `useState` for selection/mode with URL-derived values:

```typescript
// Before (broken back button, no deep links):
const [selectedId, setSelectedId] = useState<string | null>(null)

// After (URL is the source of truth):
const { path, navigate } = useRouter()
const selectedId = path.match(/^\/items\/(.+)/)?.[1] ?? null
// Click handler: navigate(`/items/${item.id}`)
// Close handler: navigate('/items')
```

State that is purely UI (search filters, sort mode, toggles) stays in `useState` -- only navigable page transitions go in the URL.

#### Nav links

Use `<a>` tags with `href` and `preventDefault` for navigation links. This enables right-click "Open in new tab", middle-click, and URL on hover:

```tsx
<a
  href={`/${key}`}
  onClick={(e) => { e.preventDefault(); onViewChange(key) }}
  className={...}
>
  {label}
</a>
```

#### SPA fallback

The nginx config's `try_files $uri $uri/ /index.html` directive already handles this -- all paths serve `index.html`, and the React app reads the URL on mount. Vite's dev server handles this by default too. No additional configuration needed.

### Mobile-First Design

All UI is designed for phone-sized screens first, then enhanced for larger viewports using Tailwind's responsive prefixes.

#### Principles

- **Start small**: Write the mobile layout as the default styles (no prefix). Add `sm:`, `md:`, `lg:` only when the layout needs to change at larger sizes.
- **Touch-friendly targets**: Interactive elements (buttons, links, list items) should be at least 44px tall on mobile. Use `min-h-[44px] sm:min-h-0` to enforce this on mobile and relax it on desktop.
- **Stack on mobile, row on desktop**: Use `flex flex-col sm:flex-row` for layouts that should stack vertically on phones and sit side-by-side on desktop.
- **Full-width on mobile**: Buttons and inputs should be `w-full sm:w-auto` so they're easy to tap on narrow screens.
- **Responsive grids**: Use `grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4` for card layouts -- 2 columns on phones, more on larger screens.

#### Common patterns

```tsx
{/* Stack on mobile, row on desktop */}
<div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
  <h2 className="text-lg font-semibold">Title</h2>
  <button className="w-full sm:w-auto min-h-[44px] sm:min-h-0 ...">Action</button>
</div>

{/* Responsive card grid */}
<div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
  {items.map(item => <Card key={item.id} ... />)}
</div>

{/* Horizontal scroll tabs on mobile */}
<nav className="flex gap-1 overflow-x-auto scrollbar-hide">
  {tabs.map(tab => <a ... />)}
</nav>
```

#### Breakpoints (Tailwind defaults)

| Prefix | Min width | Typical device |
|--------|-----------|----------------|
| (none) | 0px | Phones |
| `sm:` | 640px | Large phones / small tablets |
| `md:` | 768px | Tablets |
| `lg:` | 1024px | Laptops / desktops |

Most apps only need `sm:` and `lg:`. Avoid overusing `md:` and `xl:` -- two breakpoints is usually enough.

### TypeScript Types

`frontend/src/types/index.ts` -- mirror the API response shapes:

```typescript
export interface Thing {
  id: string
  name: string
  description: string | null
  steps: Step[]
  created_at: string
  updated_at: string
}

export interface Step {
  id: string
  description: string
  completed: boolean
}

// Keep these in sync with the backend DTOs.
// If the API changes, update these types first.
```

### Styling

Use Tailwind CSS v4 with the Vite plugin. Import it in `frontend/src/index.css`:

```css
@import "tailwindcss";
```

For app-level theming (dark mode, custom colors), define CSS variables in the same file:

```css
:root {
  --bg-main: #111116;
  --bg-surface: #1a1a22;
  --accent: #6c8aec;
  --text-primary: #e4e4e8;
}
```

Then reference them in Tailwind classes or inline styles as needed.

### Frontend Dependencies

`frontend/package.json` core dependencies:

```json
{
  "dependencies": {
    "react": "^19.2.0",
    "react-dom": "^19.2.0"
  },
  "devDependencies": {
    "typescript": "~5.9.3",
    "vite": "^7.2.0",
    "@vitejs/plugin-react": "^5.1.0",
    "tailwindcss": "^4.1.0",
    "@tailwindcss/vite": "^4.1.0"
  }
}
```

Add other dependencies as needed per app (e.g., `@dnd-kit` for drag-and-drop in `track`). Routing is handled by a custom `useRouter` hook using the History API -- no router library needed.

---

## Docker

### Dockerfile (Multi-Stage) -- Used by Both Paths

Three stages: backend, frontend build, frontend serve. Used by `docker-compose.yml` for local dev and Pi deployment.

```dockerfile
# --- Backend ---
FROM python:3.12-slim AS backend

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY api/ api/

EXPOSE 8020
CMD ["uv", "run", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8020"]

# --- Frontend Build ---
FROM node:20-slim AS frontend-build

WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

# --- Frontend Serve ---
FROM nginx:alpine AS frontend

COPY --from=frontend-build /app/dist /usr/share/nginx/html
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

Key points:
- `python:3.12-slim` as the base -- stable and small.
- uv is copied from its official container image.
- `uv sync --frozen --no-dev` installs only production dependencies from the lockfile.
- Frontend is built with node then served with nginx -- no node runtime in production.

### Separate Dockerfiles -- Azure Path Only

Azure Container Instances runs each container independently (no multi-stage `target` support like Docker Compose). Split into two Dockerfiles:

**`Dockerfile.api`**:
```dockerfile
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY api/ api/
EXPOSE 8020
CMD ["uv", "run", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8020"]
```

**`Dockerfile.frontend`**:
```dockerfile
FROM node:20-slim AS build
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY frontend/nginx.azure.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

Note the frontend uses `nginx.azure.conf` instead of `nginx.conf` -- the difference is the API proxy target:
- **`nginx.conf`** (Docker Compose): `proxy_pass http://api:8020;` -- uses the Compose service name
- **`nginx.azure.conf`** (ACI): `proxy_pass http://localhost:8020;` -- ACI containers share a network namespace (like a Kubernetes pod)

### docker-compose.yml

```yaml
services:
  api:
    build:
      context: .
      target: backend
    container_name: myapp-api
    ports:
      - "8020:8020"
    extra_hosts:
      - "host.docker.internal:host-gateway"
    environment:
      - MONGODB_URL=mongodb://host.docker.internal:27017
      - MONGODB_DB_NAME=myapp
      - JWT_SECRET=${JWT_SECRET:-change-me-in-production}
    restart: unless-stopped

  frontend:
    build:
      context: .
      target: frontend
    container_name: myapp-frontend
    ports:
      - "8095:80"
    depends_on:
      - api
    restart: unless-stopped
```

Key points:
- `extra_hosts` maps `host.docker.internal` so the API container can reach MongoDB running on the host (the Raspberry Pi).
- `restart: unless-stopped` keeps services running after reboots.
- Ports are exposed to the host so nginx (running separately on the Pi) can reverse-proxy to them.
- Secrets like `JWT_SECRET` come from the shell environment or a `.env` file.

### Nginx Config (Frontend)

`frontend/nginx.conf` -- handles SPA routing and proxies API calls to the backend container:

```nginx
server {
    listen 80;
    root /usr/share/nginx/html;
    index index.html;

    # SPA: serve index.html for all routes
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Proxy API calls to the backend container
    location /api/ {
        proxy_pass http://api:8020;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Cache static assets
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

The `proxy_pass http://api:8020` works because Docker Compose puts both containers on the same network and `api` resolves to the backend container.

---

## Port Registry

Every app needs unique ports. Check this table and `house/applications.md` before picking ports for a new app.

| Port | Service | App |
|------|---------|-----|
| 3000 | Frontend | calendarapp |
| 5000 | App | todoozey |
| 8005 | API (internal Docker) | calendarapp |
| 8010 | API | track |
| 8080 | App | Nextcloud |
| 8081 | Reverse proxy | nginx |
| 8085 | API (production) | calendarapp |
| 8090 | Frontend | track |
| 8123 | App | Home Assistant |
| 9000 | App | Portainer |
| 27017 | Database | MongoDB |

**Next available ranges**: 8020-8049 (APIs), 8095-8099 or 3001+ (frontends). The example code in this guide uses **8020** (API) and **8095** (frontend) as placeholders -- replace with your actual chosen ports.

When choosing ports for a new app, pick from the available ranges and update both this table and `house/applications.md`.

---

## Environment Variables

Every app has a `.env.example` checked into git with sensible local defaults:

```
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB_NAME=myapp
JWT_SECRET=change-me-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=10080
```

Copy to `.env` and fill in real values. The `.env` file is in `.gitignore`.

**How env vars reach the app depends on the deployment path:**

| Path | Local | Production |
|------|-------|------------|
| **A (Pi)** | `.env` file | `.env` file on the Pi |
| **B (Azure)** | `.env` file | GitHub Secrets → `TF_VAR_` → Terraform → ACI `secure_environment_variables` |

For Path B, secrets never live in files that are committed -- they flow from GitHub Environments through Terraform into the container at deploy time. See the [Secret management](#secret-management) section under Path B for the full flow.

---

## Deployment

Every app runs locally via Docker Compose. For production, you must choose one of two deployment paths. **This is a decision you make when creating the app** -- it affects your project structure, CI/CD, and where secrets live.

### Decision: Choose Your Deployment Path

| | **Path A: Raspberry Pi** | **Path B: Azure** |
|---|---|---|
| **Best for** | Internal/family apps, low traffic | Public-facing apps, external users |
| **Environments** | Local → Production (Pi) | Local → Dev (PR-triggered) → Production |
| **Production host** | Raspberry Pi (`piservices`) | Azure Container Instances |
| **Database** | MongoDB on Pi (shared) | MongoDB Atlas (one cluster per env) |
| **Routing** | Cloudflare Tunnel + nginx | ACI public IP + DNS label |
| **CI/CD** | Auto-deploy script (polls GitHub) | GitHub Actions + Terraform |
| **Secrets** | `.env` file on Pi | GitHub Environments |
| **Cost** | Free (already running) | Azure pay-per-use |
| **Examples** | `calendarapp`, `track` | `toolshed` |

Choose **Path A** if the app is for personal/family use and the Pi is sufficient. Choose **Path B** if the app needs to be publicly accessible, needs a dev/staging environment, or needs more resources than the Pi can provide.

---

### Local Development (Both Paths)

```bash
# Backend only (no Docker)
cd <appname>
uv sync
uv run uvicorn api.main:app --reload --port 8020

# Frontend only (no Docker)
cd <appname>/frontend
npm install
npm run dev

# Everything via Docker
cd <appname>
docker compose up --build
```

When running backend and frontend separately, the Vite dev server proxies `/api` requests to the backend automatically.

---

### Path A: Raspberry Pi Deployment

The Raspberry Pi (`piservices`) runs:
- **Docker** for all application containers
- **MongoDB** on the host (shared by all apps)
- **nginx** as a reverse proxy (routes `<appname>.rabidflamingos.com` to the right container port)
- **Cloudflare Tunnel** for external HTTPS access
- **Auto-deploy script** (`house/deploy/auto-deploy.sh`) polls GitHub and rebuilds on changes

#### Deploying a new app

1. Build and start containers on the Pi:
   ```bash
   cd /path/to/appname
   docker compose up -d --build
   ```

2. Add nginx config and Cloudflare DNS record (see `house/adding-new-app.md`).

3. Register the app's ports in `house/applications.md`.

4. Add the app to the auto-deploy script's `APPS` array so future pushes to `main` are deployed automatically.

The Pi's MongoDB instance is shared across apps. Each app uses a separate database (set via `MONGODB_DB_NAME`). Apps never access each other's databases directly -- cross-app communication goes through REST APIs.

#### Files specific to Path A

No extra files beyond the standard project structure. The multi-stage `Dockerfile` and `docker-compose.yml` handle everything.

---

### Path B: Azure Deployment

Three environments managed by Terraform and GitHub Actions:

| Tier | Trigger | Infrastructure | URL |
|------|---------|---------------|-----|
| **Local** | `docker-compose up --build` | Docker Compose, local MongoDB | `localhost:<port>` |
| **Dev** | PR opened/updated | ACI (Terraform `dev` workspace) | `<app>-dev.<region>.azurecontainer.io` |
| **Production** | Push to `main` | ACI (Terraform `prod` workspace) | Custom domain or `<app>.<region>.azurecontainer.io` |

#### How it works

- **Terraform** manages ACI container groups using two workspaces: `prod` and `dev`
- **GitHub Environments** (`production` and `development`) hold environment-scoped secrets -- same variable names, different values per environment
- **GitHub Actions** orchestrates: build images → push to shared ACR → `terraform apply`
- Shared resources (ACR, Storage Account, Resource Group) are referenced via Terraform `data` sources, not managed by Terraform
- Dev gets its own ACI container group and (optionally) its own MongoDB Atlas cluster
- One dev environment total (not per-PR) -- most recently pushed PR wins

#### Secret management

Secrets flow from GitHub to containers:

```
GitHub Environment Secret (e.g., MONGODB_URL on "production")
  → Workflow job: `environment: production`
  → env: TF_VAR_mongodb_url: ${{ secrets.MONGODB_URL }}
  → Terraform variable "mongodb_url" (sensitive)
  → azurerm_container_group secure_environment_variables
  → Container env var MONGODB_URL
  → Python pydantic-settings: Settings.mongodb_url
```

Secret layout:

| Secret | Scope | Notes |
|--------|-------|-------|
| `ARM_SUBSCRIPTION_ID`, `ARM_TENANT_ID`, `ARM_CLIENT_ID`, `ARM_CLIENT_SECRET` | Repository | Service principal for Azure auth |
| `ACR_PASSWORD` | Repository | Shared Azure Container Registry |
| `MONGODB_URL` | **Environment** (both) | Different Atlas cluster per env |
| `JWT_SECRET` | **Environment** (both) | Different values per env |
| App-specific secrets | **Environment** (both) | e.g., `AZURE_STORAGE_CONNECTION_STRING` |

#### Adding a new environment variable

1. Add the GitHub Secret to the relevant environment(s)
2. Add the `variable` in `infra/variables.tf`
3. Wire it into the ACI container block in `infra/main.tf`
4. Add the `TF_VAR_` mapping in the workflow file(s)

#### Terraform structure

```
infra/
├── providers.tf       # azurerm provider + backend config
├── variables.tf       # All input variable definitions
├── main.tf            # Data sources, locals, ACI container group
├── outputs.tf         # FQDN, IP address
└── terraform.tfvars   # Non-secret prod defaults (committed)
```

Key Terraform patterns:
- Use `locals` to derive environment-specific names (e.g., `container_group = is_prod ? "myapp" : "myapp-dev"`)
- Use `data` sources for shared pre-existing resources (resource group, ACR, storage account)
- Pass environment via `-var="environment=dev"` flag (not `TF_VAR_` env var) because `terraform.tfvars` takes precedence over env vars
- State stored in Azure Blob Storage (`sttoolshedtfstate` account, `tfstate` container)

#### GitHub Actions workflows

**`deploy.yml`** (production):
- Trigger: push to `main`
- Job 1 (`build`): Build + push images to ACR (`:$SHA` + `:latest`)
- Job 2 (`deploy`): `environment: production` → `terraform init` → `workspace select prod` → `plan` → `apply`

**`deploy-dev.yml`** (development):
- Trigger: `pull_request: [opened, synchronize, reopened]`
- Concurrency group with cancel-in-progress (only one deploy at a time)
- Job 1 (`build`): Build + push images to ACR (`:dev-$SHA`)
- Job 2 (`deploy`): `environment: development` → `terraform init` → `workspace select dev` → `plan` → `apply`
- Post-deploy: comment on PR with dev URL (read from `terraform output`)

#### Azure gotchas

- ACI containers in the same container group share a network namespace (like a Kubernetes pod) -- they communicate via `localhost`
- ACI memory must be in 0.1 GB increments (0.25 fails, use 0.3)
- MongoDB Atlas free tier needs `0.0.0.0/0` network access for ACI (dynamic IPs)
- `terraform.tfvars` overrides `TF_VAR_` env vars -- use `-var` flags for per-environment overrides
- Setting explicit `permissions` on a GitHub Actions job removes all defaults -- must include `contents: read` for checkout

#### One-time bootstrap for a new Azure app

1. Create a Terraform state storage account:
   ```bash
   az storage account create --resource-group <rg> --name <tfstate-account> --sku Standard_LRS
   az storage container create --name tfstate --account-name <tfstate-account>
   ```

2. Create a service principal:
   ```bash
   az ad sp create-for-rbac --name "github-<appname>" --role contributor \
     --scopes /subscriptions/<sub-id>/resourceGroups/<rg> --json-auth
   ```

3. Create GitHub Environments (`production`, `development`) and add secrets.

4. Create the Terraform files in `infra/`.

5. Import existing resources (if any) into Terraform state.

#### Files specific to Path B

| File | Purpose |
|------|---------|
| `Dockerfile.api` | Standalone API image for ACI |
| `Dockerfile.frontend` | Standalone frontend/nginx image for ACI |
| `frontend/nginx.azure.conf` | nginx config using `localhost` instead of Compose service name |
| `infra/*.tf` | Terraform infrastructure definitions |
| `.github/workflows/deploy.yml` | Production CI/CD |
| `.github/workflows/deploy-dev.yml` | Dev environment CI/CD |

---

## Testing

Tests run directly against your local environment -- no Docker containers needed. The only external requirement is a running MongoDB instance.

### Prerequisites

MongoDB must be accessible at the URL specified in your test config. By default, tests expect `mongodb://localhost:27017`. If your MongoDB is elsewhere, set the `MONGODB_URL` environment variable before running tests.

### Backend Tests (pytest + httpx)

Tests live in a `tests/` directory at the app root:

```
<appname>/
├── api/
├── tests/
│   ├── conftest.py          # Fixtures: app client, test DB, auth helpers
│   ├── test_auth.py         # Auth endpoint tests
│   └── test_<resource>.py   # One file per resource, matching api/routes/
├── pyproject.toml
```

#### conftest.py

This is the most important file -- it wires up the test database, creates the async HTTP client, and provides auth helpers:

```python
import pytest
import os
from httpx import AsyncClient, ASGITransport
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie

from api.main import app
from api.schemas.orm.user import User
from api.schemas.orm.thing import Thing  # Import all your Beanie documents
from api.utils.auth import hash_password, create_access_token

# Test database name -- always suffixed with _test to avoid touching real data.
TEST_DB_NAME = "myapp_test"
MONGODB_URL = os.environ.get("MONGODB_URL", "mongodb://localhost:27017")


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
async def setup_test_db():
    """Initialize Beanie with a test database before each test, drop it after."""
    client = AsyncIOMotorClient(MONGODB_URL)
    await init_beanie(
        database=client[TEST_DB_NAME],
        document_models=[User, Thing],  # All Beanie documents
    )
    yield
    await client.drop_database(TEST_DB_NAME)
    client.close()


@pytest.fixture
async def client():
    """Async HTTP client pointed at the FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
async def authenticated_client(client: AsyncClient):
    """Client with a valid auth token for a test user."""
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=hash_password("testpass123"),
    )
    await user.insert()
    token = create_access_token(str(user.id))
    client.headers["Authorization"] = f"Bearer {token}"
    yield client
```

Key points:
- `TEST_DB_NAME` is hardcoded with a `_test` suffix -- this prevents accidentally wiping a real database.
- `MONGODB_URL` comes from the environment, defaulting to `localhost:27017`.
- The `setup_test_db` fixture is `autouse=True` -- it runs before every test and drops the entire test database afterward, so each test starts with a clean slate.
- `authenticated_client` creates a real user and real JWT, so tests exercise the actual auth pipeline.

#### Example test file

```python
import pytest

@pytest.mark.anyio
async def test_health_check(client):
    res = await client.get("/api/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}

@pytest.mark.anyio
async def test_create_thing(authenticated_client):
    res = await authenticated_client.post("/api/things", json={
        "name": "Test thing",
        "description": "A test",
    })
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Test thing"
    assert "id" in data

@pytest.mark.anyio
async def test_list_things_requires_auth(client):
    res = await client.get("/api/things")
    assert res.status_code == 401 or res.status_code == 403

@pytest.mark.anyio
async def test_users_only_see_own_things(authenticated_client, client):
    # Create a thing as the authenticated user
    await authenticated_client.post("/api/things", json={"name": "Private"})

    # Second user shouldn't see it
    from api.schemas.orm.user import User
    from api.utils.auth import hash_password, create_access_token

    user2 = User(
        username="other",
        email="other@example.com",
        hashed_password=hash_password("pass"),
    )
    await user2.insert()
    token2 = create_access_token(str(user2.id))
    client.headers["Authorization"] = f"Bearer {token2}"

    res = await client.get("/api/things")
    assert res.status_code == 200
    assert len(res.json()) == 0
```

#### What to test

Focus on route-level integration tests -- they cover routing, auth, validation, and database logic in one shot:

- **Auth flow**: register, login, token validation, bad credentials rejected
- **CRUD per resource**: create, list, get by ID, update, delete
- **Authorization**: user A can't access user B's data
- **Business logic edge cases**: ordering, status transitions, etc.

Skip testing Pydantic validation in isolation (FastAPI handles that) and skip testing individual database queries (the route tests cover them).

#### pytest configuration

Add to `pyproject.toml`:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

This avoids needing `@pytest.mark.anyio` on every test -- all async test functions are treated as async automatically.

#### Running backend tests

```bash
cd <appname>
uv run pytest              # run all tests
uv run pytest -v           # verbose output
uv run pytest tests/test_auth.py   # single file
uv run pytest -x           # stop on first failure
```

If MongoDB is not on localhost:
```bash
MONGODB_URL=mongodb://192.168.1.50:27017 uv run pytest
```

### Frontend Tests (Vitest + React Testing Library)

Frontend tests use Vitest (same build pipeline as Vite) and React Testing Library for component tests.

#### Setup

Add to `frontend/package.json` devDependencies:

```json
"vitest": "^3.0.0",
"@testing-library/react": "^16.0.0",
"@testing-library/jest-dom": "^6.0.0",
"jsdom": "^25.0.0"
```

Add a test script:

```json
"scripts": {
  "dev": "vite",
  "build": "tsc -b && vite build",
  "test": "vitest run",
  "test:watch": "vitest"
}
```

Add test config to `frontend/vite.config.ts`:

```typescript
export default defineConfig({
  plugins: [react(), tailwindcss()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/test/setup.ts',
  },
  server: {
    // ...existing proxy config
  },
})
```

Create `frontend/src/test/setup.ts`:

```typescript
import '@testing-library/jest-dom'
```

#### Test structure

```
frontend/
├── src/
│   ├── api/
│   │   ├── client.ts
│   │   └── client.test.ts       # Test alongside the source file
│   ├── components/
│   │   └── tasks/
│   │       ├── TaskItem.tsx
│   │       └── TaskItem.test.tsx
│   └── test/
│       └── setup.ts             # Global test setup
```

Place test files next to the source files they test (`*.test.ts` / `*.test.tsx`). This keeps tests discoverable and easy to maintain.

#### What to test

- **API client**: mock `fetch`, verify it sets auth headers, handles 401 correctly, clears tokens
- **Components with logic**: forms with validation, state-driven UI (expanded/collapsed, filtered lists)
- **Context providers**: auth login/logout flows update state correctly

Skip testing components that just render props with no logic, and skip testing styling.

#### Running frontend tests

```bash
cd <appname>/frontend
npm test                # single run
npm run test:watch      # watch mode, re-runs on file changes
```

No backend or Docker needed -- frontend tests mock all API calls.

### When to run tests

- **After changing backend code**: `uv run pytest` from the app directory
- **After changing frontend code**: `npm test` from the frontend directory
- **Before committing**: run both

### Instructions for Claude

When Claude is building or modifying an app, it should:
- Run `uv run pytest` after backend changes
- Run `cd frontend && npm test` after frontend changes
- Write route-level integration tests for new API endpoints
- Write component tests for new components that contain non-trivial logic

---

## Checklist for New Apps

### All apps (both paths)

- [ ] **Choose deployment path: Pi (Path A) or Azure (Path B)**
- [ ] Create `database-design.drawio` with document models and their relationships
- [ ] Copy structure from an existing app (`track` for Path A, `toolshed` for Path B)
- [ ] Update `pyproject.toml` with app name and any new dependencies
- [ ] Choose unique ports (check `house/applications.md`)
- [ ] Set unique `MONGODB_DB_NAME` in `.env.example`
- [ ] Update `vite.config.ts` proxy target port
- [ ] Update Dockerfile exposed ports and uvicorn port
- [ ] Update `docker-compose.yml` port mappings and container names
- [ ] Update `frontend/nginx.conf` proxy_pass port (confirm `try_files` SPA fallback is present)
- [ ] Copy `useRouter.ts` hook into `frontend/src/hooks/`
- [ ] Design URL paths for all navigable views and wire them into `App.tsx`
- [ ] Add the app to `house/applications.md`
- [ ] Create `tests/conftest.py` with test DB fixtures (copy from an existing app)
- [ ] Add vitest + React Testing Library to frontend devDependencies
- [ ] Add vitest config to `frontend/vite.config.ts`
- [ ] Create `frontend/src/test/setup.ts`
- [ ] Verify `uv run pytest` and `npm test` both pass

### Path A only (Raspberry Pi)

- [ ] Add nginx config on the Pi per `house/adding-new-app.md`
- [ ] Add Cloudflare DNS CNAME record
- [ ] Add app to auto-deploy script's `APPS` array

### Path B only (Azure)

- [ ] Create `Dockerfile.api` and `Dockerfile.frontend`
- [ ] Create `frontend/nginx.azure.conf` (copy from `toolshed`, change proxy port)
- [ ] Bootstrap Terraform state storage account (if not sharing existing one)
- [ ] Create `infra/` directory with Terraform files (copy from `toolshed`, update names/vars)
- [ ] Create GitHub Environments (`production`, `development`) with secrets
- [ ] Create `.github/workflows/deploy.yml` and `deploy-dev.yml`
- [ ] Create service principal for GitHub Actions (or reuse existing one with expanded scope)
- [ ] Provision dev MongoDB Atlas cluster
- [ ] Test: create PR → verify dev deployment → merge → verify prod deployment

---

## Improvement Suggestions

Issues found comparing `calendarapp` and `track`, plus ideas for agent integration.

### 1. Fix Inconsistent Password Hashing in calendarapp

`calendarapp` still uses `passlib` with bcrypt (`calendarapp/api/utils/auth.py`), which has known compatibility issues with bcrypt 5.x. `track` already uses the correct approach (Argon2 via `argon2-cffi`). The calendarapp auth module should be updated to match track's pattern.

### 2. Standardize the Frontend Theme

The two apps have completely different styling:

- **track**: Dark theme with CSS variables (`--bg-main: #111116`, `--accent: #6c8aec`, etc.)
- **calendarapp**: Light theme with hardcoded values (`background: rgb(249 250 251)`)

To fix this, create a shared theme file that all apps copy into their `frontend/src/index.css`. The track theme is a good starting point:

```css
@import "tailwindcss";

:root {
  --bg-main: #111116;
  --bg-surface: #1a1a22;
  --bg-raised: #24242e;
  --border-color: #2e2e3a;
  --accent: #6c8aec;
  --accent-hover: #5a7ad4;
  --text-primary: #e4e4e8;
  --text-secondary: #9898a4;
  --text-muted: #5e5e6a;
  --selected-bg: rgba(108, 138, 236, 0.12);
  --header-bg: #14141a;
  --success: #4ade80;
  --warning: #facc15;
  --danger: #f87171;
}

body {
  margin: 0;
  min-height: 100vh;
  background-color: var(--bg-main);
  color: var(--text-primary);
}

#root {
  min-height: 100vh;
}
```

All new apps should use these variables rather than hardcoding colors. Components should reference them via Tailwind arbitrary values (e.g., `bg-[var(--bg-surface)]`) or inline styles. This gives every app a consistent dark look.

If a shared npm package feels like overkill (it is for now), just keep a reference copy of the theme CSS in this guide and copy it when creating new apps.

### 3. Standardize Frontend Directory Naming

- `calendarapp` uses `frontend-react/`
- `track` uses `frontend/`

Pick one. `frontend/` is simpler and sufficient since we're committed to React. New apps should use `frontend/`.

### 4. Agent / AI Integration via API Keys

Currently both apps only support JWT tokens, which require a login flow (username/password or a shared password). This is awkward for AI agents (Claude, MCP servers, scripts) because they need to:
1. POST to `/api/auth/login` with credentials
2. Store and manage the JWT
3. Handle token expiration and re-auth

A simpler approach for agents: **static API keys** that bypass the JWT flow entirely. Here's how to add it:

**Backend changes** -- add an `X-API-Key` header check as an alternative auth path:

```python
# api/utils/auth.py

from fastapi import Request, Depends, HTTPException
from fastapi.security import HTTPBearer, APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)

async def get_current_user_or_agent(
    api_key: str | None = Depends(api_key_header),
    bearer: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
):
    settings = get_settings()

    # Path 1: API key auth (for agents)
    if api_key and api_key == settings.agent_api_key:
        return AgentUser(name="agent")  # A simple sentinel object

    # Path 2: JWT auth (for browser users)
    if bearer:
        user = await _decode_jwt_and_fetch_user(bearer.credentials)
        if user:
            return user

    raise HTTPException(status_code=401, detail="Not authenticated")
```

**Config addition**:
```
# .env
AGENT_API_KEY=generate-a-long-random-string-here
```

**Usage by agents**:
```bash
curl -H "X-API-Key: your-key-here" https://track.rabidflamingos.com/api/tasks
```

This keeps JWT for browser users and adds a zero-friction path for agents. The API key is a single env var per app -- no database, no expiration to manage. If you later want per-agent keys or scoped permissions, you can add an `api_keys` collection in MongoDB, but the single env var approach is enough to start.

### 5. Standardize Auth Model Across Apps

The two apps use different auth models:

- **calendarapp**: Single shared password (no user accounts, JWT subject is "family")
- **track**: Per-user accounts with registration, email, username

For consistency and agent access, standardize on per-user accounts (the track model). The calendarapp should eventually migrate to this. A shared password is fine for a family calendar, but it makes agent integration harder since there's no user identity.

### 6. Frontend Directory Naming for calendarapp

The `calendarapp` Dockerfile references `frontend-react/` paths. If you rename to `frontend/`, update:
- `Dockerfile` COPY paths
- `docker-compose.yml` if it references the directory
- Any CI/CD scripts
