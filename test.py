from dotenv import load_dotenv

load_dotenv()

from agent.orchestrator import (
    make_subagents,
    build_deep_agent_with_subagents,
    run_orchestration,
)

from tools.nmap import make_langchain_tool, nmap_tool
from tools.sqlmap import sqlmap_tool

# nmap_tool = make_langchain_tool()
# sqlmap_tool = make_sqlmap_tool()


if __name__ == "__main__":
    print("Multi-subagent DeepAgents HITL runner (corrected to use subagents param)")

    # target = input("Enter target (IP/hostname/CIDR): ").strip()
    target = "127.0.0.1"

    # ok = (
    #     input(
    #         "Confirm you have written authorization to test the target(s) involved [yes/no]: "
    #     )
    #     .strip()
    #     .lower()
    # )
    ok = "yes"
    if ok not in ("y", "yes"):
        print("Authorization not confirmed. Exiting.")
        exit(1)

    # Build subagents and top-level agent
    subagents = make_subagents()

    # All tools available at top-level (subagents can choose a subset)
    all_tools = [nmap_tool, sqlmap_tool]

    instructions = (
        "You are the top-level penetration testing coordinator. Delegate tasks to subagents by calling them by name. "
        "Each subagent has a specialized prompt and limited toolset. Every tool invocation requires operator approval."
    )

    agent = build_deep_agent_with_subagents(all_tools, instructions, subagents)

    # Run the orchestration with HITL enforced
    run_orchestration(agent, target)
