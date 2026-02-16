import json
import logging
from datetime import datetime, timezone

import anthropic
from beanie import PydanticObjectId

from api.config import get_settings
from api.schemas.orm.artifact import Artifact, ArtifactType
from api.schemas.orm.conversation import Conversation, Message
from api.schemas.orm.project import Project, ProjectPhase

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
        "name": "update_phase",
        "description": "Recommend moving the project to the next phase. Use this when you believe the current phase is complete and it's time to move forward.",
        "input_schema": {
            "type": "object",
            "properties": {
                "next_phase": {
                    "type": "string",
                    "enum": [p.value for p in ProjectPhase],
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
    ProjectPhase.INTAKE: """You are in the INTAKE (Discovery) phase. Your goal is to understand the client's idea and produce initial artifacts.

Follow this process:
1. Let the client describe their idea freely
2. Ask clarifying questions systematically about:
   - The Problem: What problem does this solve? Who has it? How are they solving it now? What's painful?
   - The Users: Who specifically will use this? Technical comfort? Usage frequency? Devices?
   - The Vision: What does success look like in 6 months? What's the ONE thing it must do? What's out of scope?
3. Synthesize into a Problem Statement: "[Target users] need a way to [accomplish goal] because [pain point]. Success means [measurable outcome]."
4. Create initial artifacts using the save_artifact tool:
   - Problem Statement
   - User Personas (brief, 2-3 max)
   - Success Criteria

Ask ONE question at a time. Summarize back what you hear. Probe for specifics when answers are vague.

When you have enough information to write a problem statement and initial artifacts, do so using the save_artifact tool, then recommend moving to the requirements phase using update_phase.""",

    ProjectPhase.REQUIREMENTS: """You are in the REQUIREMENTS phase. Your goal is to produce a complete requirements document.

Follow this process:
1. Feature Brainstorm: List everything the client wants. Don't filter yet.
2. Prioritization (MoSCoW):
   - Must Have: Launch blockers
   - Should Have: Important but can wait
   - Could Have: Nice to have
   - Won't Have: Explicitly out of scope
3. Write User Stories for Must Have features: "As a [role], I want to [action] so that [benefit]." Include acceptance criteria.
4. Compile the Requirements Document using save_artifact with all sections:
   - Problem Statement
   - User Personas
   - Features (prioritized)
   - User Stories with Acceptance Criteria
   - Constraints
   - Assumptions
   - Open Questions

Ask questions to fill gaps. Get explicit confirmation before finalizing.

When the requirements document is complete and the client approves, use update_phase to move to architecture.""",

    ProjectPhase.ARCHITECTURE: """You are in the ARCHITECTURE phase. Your goal is to produce technical design documents.

Cover:
1. Data Model: What entities exist? How do they relate? Create an ERD.
2. API Design: What operations are needed? RESTful resource structure. Auth requirements.
3. UI/UX: Key screens/flows. Wireframes (text-based).
4. Technical Decisions: Framework choices, hosting, integrations.

Produce artifacts using save_artifact:
- Architecture Document
- Data Model / ERD (as Mermaid diagram in markdown)
- Key User Flows

When architecture is complete, use update_phase to move to build.""",
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

    phase_instructions = PHASE_INSTRUCTIONS.get(
        project.current_phase, DEFAULT_INSTRUCTIONS
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
        "\n- Flag potential scope creep early"
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
            artifact = Artifact(
                project_id=project.id,
                phase=project.current_phase,
                artifact_type=tool_input["artifact_type"],
                title=tool_input["title"],
                content=tool_input["content"],
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
    project_id: str, user_message: str
) -> tuple[str, Conversation]:
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

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    # Agent loop - keep calling until no more tool use
    assistant_text = ""
    max_iterations = 10

    for _ in range(max_iterations):
        response = client.messages.create(
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
            result = await handle_tool_call(
                tool_use.name, tool_use.input, project
            )
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": tool_use.id,
                    "content": result,
                }
            )

        api_messages.append({"role": "user", "content": tool_results})

    # Store the final assistant text in conversation
    if assistant_text:
        conversation.messages.append(
            Message(role="assistant", content=assistant_text)
        )

    conversation.updated_at = datetime.now(timezone.utc)
    await conversation.save()

    return assistant_text, conversation
