import json
import logging
from datetime import datetime, timezone

import anthropic
from beanie import PydanticObjectId

from api.config import get_settings
from api.schemas.orm.artifact import Artifact, ArtifactType
from api.schemas.orm.conversation import Conversation, Message
from api.schemas.orm.entity import Entity, EntityCounter, EntityType
from api.schemas.orm.note import ActivityLog
from api.schemas.orm.project import Project, ProjectPhase
from api.services.status_reporter import NullStatusReporter, StatusReporter

logger = logging.getLogger(__name__)

TOOLS = [
    {
        "name": "save_artifact",
        "description": "Save a project artifact (requirements doc, problem statement, user stories, etc.). Use this when you have synthesized enough information to produce a structured document.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Title of the artifact",
                },
                "artifact_type": {
                    "type": "string",
                    "enum": [t.value for t in ArtifactType],
                    "description": "Type of artifact",
                },
                "content": {
                    "type": "string",
                    "description": "Markdown content of the artifact",
                },
            },
            "required": ["title", "artifact_type", "content"],
        },
    },
    {
        "name": "save_entity",
        "description": "Save a structured entity (requirement, decision, constraint, etc.) as it emerges from conversation. Use this incrementally — don't wait until the end. Each call creates one entity visible in the project sidebar.",
        "input_schema": {
            "type": "object",
            "properties": {
                "entity_type": {
                    "type": "string",
                    "enum": [t.value for t in EntityType],
                    "description": "Type of entity (REQ, DEC, CONST, ASSUME, RISK, Q, NOTE, etc.)",
                },
                "title": {
                    "type": "string",
                    "description": "Short summary of the entity",
                },
                "description": {
                    "type": "string",
                    "description": "Full description of the entity",
                },
                "priority": {
                    "type": "integer",
                    "description": "Priority 1-5 (1=highest). Optional.",
                    "minimum": 1,
                    "maximum": 5,
                },
            },
            "required": ["entity_type", "title", "description"],
        },
    },
    {
        "name": "update_phase",
        "description": "Recommend moving the project to the next phase. Use this when you believe the current phase is complete and it's time to move forward.",
        "input_schema": {
            "type": "object",
            "properties": {
                "next_phase": {
                    "type": "string",
                    "enum": [
                        p.value for p in ProjectPhase
                        if p not in (
                            ProjectPhase.INTAKE,
                            ProjectPhase.REQUIREMENTS,
                            ProjectPhase.ARCHITECTURE,
                        )
                    ],
                    "description": "The phase to move to",
                },
                "reason": {
                    "type": "string",
                    "description": "Why the project should move to this phase",
                },
            },
            "required": ["next_phase", "reason"],
        },
    },
]

PHASE_INSTRUCTIONS = {
    ProjectPhase.DISCOVERY: """You are in the DISCOVERY phase. Your goal is to understand the client's idea, gather MVP requirements, and produce structured artifacts — all in one conversation.

IMPORTANT: Focus ONLY on the MVP (Minimum Viable Product). Do NOT save future plans, nice-to-haves, or stretch goals as requirements. Only save what is needed to launch.

Follow this process:

**Part 1 — Problem Discovery**
1. Let the client describe their idea freely.
2. Ask clarifying questions ONE at a time about:
   - The Problem: What problem does this solve? Who has it? How do they solve it now?
   - The Users: Who will use this? Technical comfort? Devices?
   - The Vision: What does success look like? What's the ONE must-have? What's out of scope?
3. As MVP requirements, decisions, constraints, and assumptions emerge from the conversation, save each one immediately using the save_entity tool. Do NOT wait until the end — capture them incrementally as they come up.

**Part 2 — MVP Requirements**
4. After discovery, help the client identify what is essential for launch:
   - What must exist on day one for this to be useful?
   - What is the simplest version that solves the core problem?
5. Save ONLY MVP requirements as save_entity(entity_type="REQ", ...). If the client mentions features that are not essential for launch, acknowledge them but do NOT save them as requirements.

**Part 3 — Out of Scope**
6. Collect any ideas the client mentioned that are NOT part of the MVP (nice-to-haves, future features, stretch goals). Save these as a single artifact using save_artifact with artifact_type="spec" and title="Out of Scope — Future Ideas". This keeps them recorded without cluttering the MVP requirements.

**Part 4 — Wrap-up**
7. Create summary artifacts using save_artifact:
   - Problem Statement
   - Requirements Document (compiled from the MVP entities you already saved)
8. Get explicit confirmation from the client, then use update_phase to move to domain_design.

IMPORTANT: Use save_entity frequently throughout the conversation — every time an MVP requirement, decision, constraint, or assumption is identified. The client can see these appear in the sidebar in real-time. Do NOT save future/non-MVP items as entities.""",

    ProjectPhase.DOMAIN_DESIGN: """You are in the DOMAIN DESIGN phase. A DDD scaffold (entities, subdomains, events) has been auto-generated from Discovery. Your goal is to review and refine it with the client.

Follow this process:

**Part 1 — Review Auto-Generated Scaffold**
1. Present the generated domain entities, subdomains, and events to the client.
2. Walk through each subdomain and its entities. Ask if anything is missing or wrong.
3. Identify aggregate roots — which entities are the primary "owners" of related data?

**Part 2 — Refine the Model**
4. Add missing entities, remove false positives, and adjust relationships.
5. Verify subdomain boundaries make sense — no entity should belong to multiple subdomains.
6. Define key domain events — what triggers them and what reacts to them.

**Part 3 — Produce Artifacts**
7. Create a Domain Model artifact using save_artifact (artifact_type="architecture_doc") containing:
   - Entity list with properties and relationships
   - Subdomain map
   - Event catalog
   - ER diagram (Mermaid)
8. Get explicit confirmation from the client, then use update_phase to move to build.

Use save_entity to capture any new decisions or constraints that emerge.""",
}

DEFAULT_INSTRUCTIONS = """You are a helpful AI project manager guiding software development. Help the client with their current needs based on the project's phase and context."""


def build_system_prompt(project: Project, artifacts: list[Artifact]) -> str:
    parts = [
        "You are the Golden Incubator AI — a project manager guiding software development from idea to deployment.",
        f"\n## Current Project: {project.name}",
    ]

    if project.description:
        parts.append(f"Description: {project.description}")

    parts.append(f"Current Phase: {project.current_phase.value}")

    # Map legacy phases to their replacement
    effective_phase = project.current_phase
    if effective_phase in (ProjectPhase.INTAKE, ProjectPhase.REQUIREMENTS):
        effective_phase = ProjectPhase.DISCOVERY
    elif effective_phase == ProjectPhase.ARCHITECTURE:
        effective_phase = ProjectPhase.DOMAIN_DESIGN

    phase_instructions = PHASE_INSTRUCTIONS.get(
        effective_phase, DEFAULT_INSTRUCTIONS
    )
    parts.append(f"\n## Phase Instructions\n{phase_instructions}")

    if artifacts:
        parts.append("\n## Existing Artifacts")
        for artifact in artifacts:
            parts.append(f"\n### {artifact.title} ({artifact.artifact_type.value})")
            if len(artifact.content) <= 2000:
                parts.append(artifact.content)
            else:
                parts.append(artifact.content[:2000] + "\n...(truncated)")

    parts.append(
        "\n## Guidelines"
        "\n- Ask one question at a time"
        "\n- Summarize back what you hear"
        "\n- Be conversational and friendly"
        "\n- Probe for specifics when answers are vague"
        "\n- Flag potential scope creep early — redirect non-MVP ideas to the out-of-scope artifact"
        "\n- Use save_entity to capture MVP requirements, decisions, constraints, and assumptions as they emerge — don't wait"
        "\n- Use save_artifact to produce structured documents when ready"
        "\n- Use update_phase when the current phase is complete"
    )

    return "\n".join(parts)


async def get_or_create_conversation(
    project_id: PydanticObjectId, phase: ProjectPhase
) -> Conversation:
    conversation = await Conversation.find_one(
        Conversation.project_id == project_id,
        Conversation.phase == phase,
    )
    if not conversation:
        conversation = Conversation(
            project_id=project_id,
            phase=phase,
        )
        await conversation.insert()
    return conversation


async def handle_tool_call(
    tool_name: str,
    tool_input: dict,
    project: Project,
) -> str:
    if tool_name == "save_artifact":
        existing = await Artifact.find_one(
            Artifact.project_id == project.id,
            Artifact.artifact_type == tool_input["artifact_type"],
        )
        if existing:
            existing.content = tool_input["content"]
            existing.title = tool_input["title"]
            existing.version += 1
            existing.updated_at = datetime.now(timezone.utc)
            await existing.save()
            logger.info(
                "Artifact updated: %s v%d for project %s",
                tool_input["title"],
                existing.version,
                project.id,
            )
            return json.dumps(
                {
                    "status": "updated",
                    "artifact_id": str(existing.id),
                    "version": existing.version,
                }
            )
        else:
            # Auto-assign step_order
            last = await Artifact.find(
                {"project_id": project.id, "phase": project.current_phase}
            ).sort("-step_order").limit(1).to_list()
            step_order = (last[0].step_order + 1) if last else 1

            artifact = Artifact(
                project_id=project.id,
                phase=project.current_phase,
                artifact_type=tool_input["artifact_type"],
                title=tool_input["title"],
                content=tool_input["content"],
                step_order=step_order,
                created_by="agent",
            )
            await artifact.insert()
            logger.info(
                "Artifact created: %s for project %s",
                tool_input["title"],
                project.id,
            )
            return json.dumps(
                {"status": "created", "artifact_id": str(artifact.id), "version": 1}
            )

    elif tool_name == "save_entity":
        entity_type = EntityType(tool_input["entity_type"])

        # Get or create counter document for this project
        counter = await EntityCounter.find_one(
            EntityCounter.project_id == project.id
        )
        if not counter:
            counter = EntityCounter(project_id=project.id)

        reference_id = counter.next_id(entity_type)
        await counter.save()

        entity = Entity(
            project_id=project.id,
            entity_type=entity_type,
            reference_id=reference_id,
            title=tool_input["title"],
            description=tool_input["description"],
            priority=tool_input.get("priority"),
            source_text=tool_input["description"],
            created_by="agent",
        )
        await entity.insert()

        await ActivityLog(
            project_id=project.id,
            phase=project.current_phase,
            action="entity_created",
            actor="agent",
            target_type="entity",
            target_id=entity.id,
            details={
                "entity_type": entity_type.value,
                "reference_id": reference_id,
                "title": tool_input["title"],
            },
        ).insert()

        logger.info(
            "Entity created: %s %s for project %s",
            reference_id,
            tool_input["title"],
            project.id,
        )
        return json.dumps(
            {
                "status": "created",
                "entity_id": str(entity.id),
                "reference_id": reference_id,
            }
        )

    elif tool_name == "update_phase":
        next_phase = ProjectPhase(tool_input["next_phase"])
        now = datetime.now(timezone.utc)

        # Complete current phase in history
        for entry in project.phase_history:
            if entry.phase == project.current_phase and entry.completed_at is None:
                entry.completed_at = now
                break

        # Add new phase entry
        from api.schemas.orm.project import PhaseHistoryEntry

        project.phase_history.append(
            PhaseHistoryEntry(phase=next_phase, entered_at=now)
        )
        project.current_phase = next_phase
        project.updated_at = now
        await project.save()
        logger.info(
            "Project %s moved to phase %s: %s",
            project.id,
            next_phase.value,
            tool_input["reason"],
        )
        return json.dumps(
            {
                "status": "phase_updated",
                "new_phase": next_phase.value,
                "reason": tool_input["reason"],
            }
        )

    return json.dumps({"error": f"Unknown tool: {tool_name}"})


async def send_message(
    project_id: str,
    user_message: str,
    reporter: StatusReporter | None = None,
) -> tuple[str, Conversation]:
    if reporter is None:
        reporter = NullStatusReporter()

    settings = get_settings()
    if not settings.anthropic_api_key:
        raise ValueError("ANTHROPIC_API_KEY not configured")

    project = await Project.get(PydanticObjectId(project_id))
    if not project:
        raise ValueError("Project not found")

    artifacts = await Artifact.find(
        Artifact.project_id == project.id
    ).to_list()

    conversation = await get_or_create_conversation(
        project.id, project.current_phase
    )

    # Add user message
    conversation.messages.append(
        Message(role="user", content=user_message)
    )

    # Build messages for Anthropic API
    system_prompt = build_system_prompt(project, artifacts)
    api_messages = [
        {"role": m.role, "content": m.content}
        for m in conversation.messages
    ]

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    # Agent loop - keep calling until no more tool use
    assistant_text = ""
    max_iterations = 10

    try:
        for iteration in range(1, max_iterations + 1):
            await reporter.report_thinking(iteration)

            response = await client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=4096,
                system=system_prompt,
                messages=api_messages,
                tools=TOOLS,
            )

            # Collect text blocks and tool use blocks
            text_parts = []
            tool_uses = []
            for block in response.content:
                if block.type == "text":
                    text_parts.append(block.text)
                elif block.type == "tool_use":
                    tool_uses.append(block)

            if text_parts:
                assistant_text = "\n".join(text_parts)

            if not tool_uses:
                # No tool calls - we're done
                break

            # Process tool calls
            # Add the full assistant response to messages
            api_messages.append({"role": "assistant", "content": response.content})

            # Execute each tool and collect results
            tool_results = []
            for tool_use in tool_uses:
                await reporter.report_tool_call(tool_use.name, tool_use.input)

                result = await handle_tool_call(
                    tool_use.name, tool_use.input, project
                )

                await reporter.report_tool_result(tool_use.name, result)

                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_use.id,
                        "content": result,
                    }
                )

            api_messages.append({"role": "user", "content": tool_results})

    except Exception as e:
        await reporter.report_error(str(e))
        raise

    # Store the final assistant text in conversation
    if assistant_text:
        conversation.messages.append(
            Message(role="assistant", content=assistant_text)
        )

    conversation.updated_at = datetime.now(timezone.utc)
    await conversation.save()

    await reporter.report_complete(assistant_text, str(conversation.id))

    return assistant_text, conversation
