import json
import logging

import anthropic

from api.config import get_settings

logger = logging.getLogger(__name__)

REQUIREMENTS_TEMPLATE = """# [Project Name]

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
"""

SYSTEM_PROMPT = """You are a senior requirements analyst. Your job is to have a natural conversation with the user to understand what they want to build, and progressively produce a comprehensive requirements document.

## How to behave
- Ask smart, clarifying follow-up questions — one or two at a time, not a wall of questions
- Identify gaps, edge cases, and unstated assumptions
- Be conversational and friendly, not formal or bureaucratic
- Summarize back what you hear to confirm understanding
- Probe for specifics when answers are vague
- Don't overwhelm the user — build understanding incrementally

## How to use the update_requirements tool
- You MUST call the `update_requirements` tool with every response
- The `reply` parameter is your conversational response to the user (what they see in the chat)
- The `document` parameter is the full, updated requirements markdown document
- Early in the conversation, many sections will still have placeholder text — that's fine
- As the conversation progresses, fill in sections with real content based on what you've learned
- Always return the COMPLETE document, not just the changed parts
- Update the project name in the heading when you learn it

## Requirements document structure
Start with this template and fill it in progressively:

""" + REQUIREMENTS_TEMPLATE + """

## Important
- Every response MUST include a tool call to `update_requirements`
- The document should evolve with each message — even small updates count
- Move sections from placeholder text to real content as information emerges
- Keep the document well-organized and readable
- Use bullet points, numbered lists, and sub-sections as needed
"""

UPDATE_REQUIREMENTS_TOOL = {
    "name": "update_requirements",
    "description": "Provide your chat reply and the updated requirements document. You must call this tool with every response.",
    "input_schema": {
        "type": "object",
        "properties": {
            "reply": {
                "type": "string",
                "description": "Your conversational response to the user (displayed in the chat panel).",
            },
            "document": {
                "type": "string",
                "description": "The full, updated requirements document in markdown format.",
            },
        },
        "required": ["reply", "document"],
    },
}


async def gather_requirements(
    messages: list[dict],
    current_document: str | None,
) -> dict:
    """Call Claude to get a chat reply and updated requirements document.

    Args:
        messages: Conversation history as list of {"role": ..., "content": ...} dicts.
        current_document: The current requirements markdown, or None for a new session.

    Returns:
        {"reply": str, "document": str}
    """
    settings = get_settings()
    if not settings.anthropic_api_key:
        raise ValueError("ANTHROPIC_API_KEY not configured")

    system = SYSTEM_PROMPT
    if current_document:
        system += f"\n\n## Current document state\n\n{current_document}"

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    response = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8192,
        system=system,
        messages=messages,
        tools=[UPDATE_REQUIREMENTS_TOOL],
        tool_choice={"type": "tool", "name": "update_requirements"},
    )

    # Extract the tool call result
    for block in response.content:
        if block.type == "tool_use" and block.name == "update_requirements":
            return {
                "reply": block.input["reply"],
                "document": block.input["document"],
            }

    # Fallback: if somehow no tool call was made, extract text
    logger.warning("No update_requirements tool call in response — falling back to text")
    text_parts = [b.text for b in response.content if b.type == "text"]
    return {
        "reply": "\n".join(text_parts) if text_parts else "I'm sorry, something went wrong. Could you try again?",
        "document": current_document or REQUIREMENTS_TEMPLATE,
    }
