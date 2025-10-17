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
import logging
from typing import Any, Dict, List, Optional

# Check deepagents availability
try:
    from deepagents import create_deep_agent
except ImportError:
    print("\n[ERROR] deepagents package not found!")
    print("Please install dependencies using: uv sync")
    raise

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

# Setup logger for this module
logger = logging.getLogger(__name__)


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
    """
    Create a single deep agent and pass subagents list to create_deep_agent per README schema.
    
    Args:
        all_tools: List of tool functions available to the agent
        instructions: System instructions for the agent
        subagents: List of subagent configurations
        
    Returns:
        The configured deep agent with checkpointer
    """
    logger.info("Building deep agent with %d tools and %d subagents", 
                len(all_tools), len(subagents))
    
    # Require HITL for all tool calls by name
    tool_configs = {tool.__name__: True for tool in all_tools}
    
    try:
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
        
        logger.info("Deep agent successfully built")
        return agent
        
    except Exception as e:
        logger.error("Failed to build deep agent: %s", str(e), exc_info=True)
        raise


def is_tool_calling(chunk: dict) -> bool:
    """
    Check if a chunk indicates a tool calling request.
    
    Args:
        chunk: Stream chunk dictionary
        
    Returns:
        bool: True if chunk indicates tool calling
    """
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
        logger.error("Error checking tool calling status: %s", str(e))
        raise


def run_orchestration(agent, high_level_prompt: str):
    """
    Run the main agent interactively. The main agent will call subagents (by name) for specific phases.

    This function listens for interrupts (proposed tool calls) and forces operator approval.
    For each proposed tool call we append audit entries and resume the agent with the operator decision.
    
    Args:
        agent: The configured deep agent
        high_level_prompt: Initial prompt to start the orchestration
    """
    logger.info("Starting orchestration with prompt")
    
    try:
        # Start streaming the agent until it pauses for HITL
        config = {"configurable": {"thread_id": str(uuid.uuid4())}, "recursion_limit": 100}
        next_input = {"messages": [{"role": "user", "content": high_level_prompt}]}

        iteration = 0
        while True:
            iteration += 1
            logger.debug("Orchestration iteration %d", iteration)
            
            last_chunk = None
            try:
                for chunk in agent.stream(next_input, config=config):
                    last_chunk = dict(chunk)
                    print_format_chunk(last_chunk)
            except Exception as e:
                logger.error("Error during agent stream: %s", str(e), exc_info=True)
                notify(f"Agent stream error: {str(e)}", LogLevel.ERROR)
                break

            if last_chunk is None:
                logger.warning("No chunks produced. Agent probably finished or returned nothing.")
                print("No chunks produced. Agent probably finished or returned nothing.")
                break

            if not is_tool_calling(last_chunk):
                logger.info("End of stream without tool calling request")
                notify(
                    "End of the stream. But it doesn't have a tool calling request.",
                    LogLevel.ERROR,
                )
                print(last_chunk)
                break

            try:
                resume_payload = HumanInTheLoopService.prompt_human_for_resume_cli()
                logger.info("Human decision received: %s", resume_payload[0].get("type"))
            except Exception as e:
                logger.error("Error getting human decision: %s", str(e), exc_info=True)
                notify(f"Error getting input: {str(e)}", LogLevel.ERROR)
                break

            # Resume the agent with the operator's decision
            next_input = Command(resume=resume_payload)

        logger.info("Top-level orchestration complete after %d iterations", iteration)
        print("Top-level orchestration complete.")
        
    except KeyboardInterrupt:
        logger.warning("Orchestration interrupted by user")
        notify("Orchestration interrupted by user", LogLevel.WARN)
    except Exception as e:
        logger.error("Fatal error in orchestration: %s", str(e), exc_info=True)
        notify(f"Fatal error: {str(e)}", LogLevel.ERROR)
        raise
