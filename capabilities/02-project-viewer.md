# Capability 2: Project Viewer

**Status:** 🔄 In Progress

## Purpose

Make the Golden Incubator process **visible and understandable**. Clients and stakeholders can see where a project is, how it got there, and what decisions were made along the way.

## Design Principle

> **Git is the database.**

All artifacts live in the project repo as markdown and mermaid files. The viewer just renders what's already there — no separate data store, no sync issues, no drift.

## Two Views

### 1. Dashboard (Bird's Eye)

Shows all projects at a glance:

```
┌─────────────────────────────────────────────────────────────┐
│  Golden Incubator Projects                                  │
├─────────────────────────────────────────────────────────────┤
│  📦 jarrod-app        ████████░░░░  Phase 3: Architecture   │
│  🏠 household-app     ██████████░░  Phase 4: Build          │
│  🧪 test-project      ██░░░░░░░░░░  Phase 1: Intake         │
└─────────────────────────────────────────────────────────────┘
```

**Data source:** Read `docs/status.md` or `docs/phase.md` from each project repo.

### 2. Journey View (Walkthrough)

Step through the project chronologically:

```
┌─────────────────────────────────────────────────────────────┐
│  jarrod-app — Journey                                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ✅ Phase 1: Intake (Feb 15)                                │
│     └── Problem Statement                                   │
│     └── User Personas                                       │
│     └── Success Criteria                                    │
│                                                             │
│  ✅ Phase 2: Requirements (Feb 16)                          │
│     └── Feature List (MoSCoW)                               │
│     └── User Stories                                        │
│     └── Decision: Mobile-first approach [ADR-001]           │
│                                                             │
│  🔄 Phase 3: Architecture (Current)                         │
│     └── Data Model Diagram                                  │
│     └── API Design (in progress)                            │
│                                                             │
│  ⏳ Phase 4: Build                                          │
│  ⏳ Phase 5: Deploy                                         │
│  ⏳ Phase 6: Handoff                                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Data source:** 
- `docs/requirements.md` — requirements artifacts
- `docs/architecture.md` — design artifacts
- `diagrams/*.md` — mermaid diagrams
- `decisions/*.md` — ADRs (Architecture Decision Records)
- Git history — timestamps for "when"

## Technical Approach

### MVP (Simple)
A static site generator that:
1. Clones/pulls project repos
2. Parses markdown structure
3. Renders mermaid diagrams
4. Generates a navigable HTML site

Could use: Astro, Next.js, or even just a Python script + Jinja templates.

### Future (Richer)
- GitHub App that watches repos
- Real-time updates via webhooks
- Comments/annotations on artifacts
- Client login to view their project

## File Conventions

For the viewer to work, projects should follow this structure:

```
project-name/
├── docs/
│   ├── status.md          # Current phase + status
│   ├── requirements.md    # Phase 2 output
│   └── architecture.md    # Phase 3 output
├── diagrams/
│   ├── context.md         # C4 Context
│   ├── data-model.md      # ERD
│   └── flows/             # User flows
├── decisions/
│   └── 001-mobile-first.md  # ADR format
└── README.md
```

## Status File Format

`docs/status.md`:

```markdown
# Project Status

**Phase:** 3 - Architecture
**Status:** In Progress
**Last Updated:** 2026-02-15

## Completed
- [x] Intake
- [x] Requirements

## Current
- [ ] Data model design
- [ ] API specification

## Blocked
- None
```

## Next Steps

1. [ ] Define the exact file conventions
2. [ ] Build MVP viewer (static site)
3. [ ] Test with first real project (Jarrod's app)
4. [ ] Iterate based on what's actually useful
