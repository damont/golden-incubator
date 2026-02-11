# System Architecture Overview

## The Big Picture

```mermaid
flowchart TB
    subgraph Client["Client Experience"]
        C1[Requirements Session]
        C2[Project Dashboard]
        C3[Feedback Portal]
    end

    subgraph Core["Golden Incubator Core"]
        AI[AI Orchestrator]
        TM[Template Manager]
        PM[Project Manager]
    end

    subgraph Templates["Template Library"]
        T1[Project Scaffolds]
        T2[Admin Portals]
        T3[Deployment Configs]
        T4[Support Systems]
    end

    subgraph Output["Delivered Projects"]
        P1[Client App]
        P2[Admin Portal]
        P3[API Backend]
        P4[Cloud Infrastructure]
    end

    C1 --> AI
    AI --> TM
    TM --> Templates
    AI --> PM
    PM --> Output
    C2 --> PM
    C3 --> PM
```

## Component Breakdown

### 1. Client Experience Layer
The interfaces clients interact with:
- **Requirements Session** — AI-guided requirements capture
- **Project Dashboard** — Track progress, milestones, deliverables
- **Feedback Portal** — Submit feedback, request changes

### 2. AI Orchestrator
The brain that connects everything:
- Conducts requirements interviews
- Selects appropriate templates
- Configures projects based on requirements
- Coordinates build/deploy workflows

### 3. Template Manager
Library of reusable components:
- Project scaffolding (FastAPI, React, etc.)
- Admin portal templates
- Deployment configurations
- Common patterns (auth, CRUD, etc.)

### 4. Project Manager
Tracks and delivers:
- Project state and progress
- Environment management
- Deployment orchestration
- Handoff documentation

## Technology Stack

```mermaid
flowchart LR
    subgraph Frontend
        React
        TailwindCSS
        TypeScript
    end
    
    subgraph Backend
        FastAPI
        Python
        Beanie/MongoDB
    end
    
    subgraph Infrastructure
        Docker
        Azure/AWS
        GitHub_Actions[GitHub Actions]
    end
    
    subgraph AI
        Claude
        Clawdbot
    end
    
    Frontend --> Backend
    Backend --> Infrastructure
    AI --> Backend
    AI --> Infrastructure
```

## Data Flow

```mermaid
sequenceDiagram
    participant C as Client
    participant AI as AI Orchestrator
    participant TM as Template Manager
    participant GH as GitHub
    participant Cloud as Cloud Provider
    
    C->>AI: Start project
    AI->>C: Requirements interview
    C->>AI: Answers & feedback
    AI->>AI: Generate specs
    AI->>TM: Select templates
    TM->>GH: Create repo from template
    AI->>GH: Customize for project
    AI->>Cloud: Provision environments
    AI->>C: MVP ready for review
    C->>AI: Feedback
    AI->>GH: Iterate
```

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Primary Backend | FastAPI + Python | Fast to build, AI-friendly, good async |
| Database | MongoDB | Flexible schema, good for rapid iteration |
| Frontend | React + TypeScript | Industry standard, component reusability |
| Hosting | Azure or AWS | Enterprise-ready, good AI integration |
| CI/CD | GitHub Actions | Integrated with repos, easy automation |

---

*See `/decisions/` for detailed Architecture Decision Records.*
