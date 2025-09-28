"""
deepagents_hitl_runner.py

Updated to use DeepAgents `subagents` parameter correctly: a single deep agent is created via
`create_deep_agent(tools, prompt, subagents=subagents)` where `subagents` is a list of dicts
(each dict contains name, description, prompt, tools, optionally model or a pre-built graph).

This runner builds a single top-level deep agent with specialized subagents for each pentest phase
(Recon, Enumeration, Vulnerability Scanning, Exploitation, Post-Exploitation, Persistence, Reporting).

Behavior highlights:
 - subagents are declared and passed into `create_deep_agent(...)` according to the README schema.
 - Human-In-The-Loop (HITL) is enforced for tool calls via `tool_configs` so every tool invocation pauses the
   agent and requires operator Accept/Edit/Respond/Abort.
 - Everything is auditable: proposed calls, operator decisions, actual commands and outputs are logged
   to a JSONL audit file.

Security / Legal reminder: Only run this code against systems you are explicitly authorized to test.
All actions will be logged; follow your organization's rules of engagement.
"""

from __future__ import annotations

import json
import uuid
import time
import os
from typing import Any, Dict, List, Optional

from deepagents import create_deep_agent
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command


# Internal
from services.io_service import (
    safe_parse_int_input,
    print_menu,
    notify,
    LogLevel,
    print_format_chunk,
)
from agent.subagent import (
    enumeration_subagent,
    recon_subagent,
    persistence_subagent,
    post_exploitation_subagent,
    reporting_subagent,
    vuln_scan_subagent,
    exploitation_subagent,
)
from services.human_in_the_loop_service import HumanInTheLoopService


# --------------------- Subagents definition ---------------------
def make_subagents() -> List[Dict[str, Any]]:
    subagents = [
        recon_subagent.make_subagent(tools=[]),
        enumeration_subagent.make_subagent(tools=[]),
        vuln_scan_subagent.make_subagent(tools=[]),
        persistence_subagent.make_subagent(tools=[]),
        exploitation_subagent.make_subagent(tools=[]),
        post_exploitation_subagent.make_subagent(tools=[]),
        reporting_subagent.make_subagent(tools=[]),
    ]
    return subagents


# --------------------- Build and run the top-level agent ---------------------


def build_deep_agent_with_subagents(
    all_tools: List[Any], instructions: str, subagents: List[Dict[str, Any]]
):
    """Create a single deep agent and pass subagents list to create_deep_agent per README schema."""
    # Require HITL for all tool calls by name
    tool_configs = {tool.__name__: True for tool in all_tools}

    from langchain.chat_models import init_chat_model

    llm = init_chat_model(model="gemini-2.0-flash", model_provider="google_genai")
    agent = create_deep_agent(
        all_tools,
        instructions,
        subagents=subagents,
        tool_configs=tool_configs,
        model=llm,
    )

    # Attach in-memory checkpointer required for pause/resume
    agent.checkpointer = InMemorySaver()

    return agent


def is_tool_calling(chunk: dict) -> bool:
    try:
        # Check for interrupt chunk
        if isinstance(chunk, dict) and "__interrupt__" in chunk:
            return True

        # Check for tool calling in a model response message
        if "model_request" in chunk and "messages" in chunk["model_request"]:
            for message in chunk["model_request"]["messages"]:
                tool_calls = message.tool_calls
                if tool_calls:
                    return True
        return False
    except Exception as e:
        raise e


def run_orchestration(agent, high_level_prompt: str):
    """Run the main agent interactively. The main agent will call subagents (by name) for specific phases.

    This function listens for interrupts (proposed tool calls) and forces operator approval.
    For each proposed tool call we append audit entries and resume the agent with the operator decision.
    """
    # Start streaming the agent until it pauses for HITL
    config = {"configurable": {"thread_id": str(uuid.uuid4())}, "recursion_limit": 100}
    next_input = {"messages": [{"role": "user", "content": high_level_prompt}]}

    while True:
        last_chunk = None
        for chunk in agent.stream(next_input, config=config):
            # print("STREAM->", chunk)
            last_chunk = dict(chunk)
            print_format_chunk(last_chunk)

        if last_chunk is None:
            print("No chunks produced. Agent probably finished or returned nothing.")
            break

        if not is_tool_calling(last_chunk):
            notify(
                "End of the stream. But it doesn't have a tool calling request.",
                LogLevel.ERROR,
            )
            break

        resume_payload = HumanInTheLoopService.prompt_human_for_resume_cli()

        # Resume the agent with the operator's decision
        next_input = Command(resume=resume_payload)

    print("Top-level orchestration complete.")
