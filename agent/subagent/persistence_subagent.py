from services.subagent_service import SubAgentService
from agent.prompt.subagent_prompt import PERSISTENCE_PROMPT
from tools.nmap import nmap_tool
from tools.sqlmap import sqlmap_tool

NAME = "persistence"
DESCRIPTION = "Persistence & cleanup (HITL)"
PROMPT = PERSISTENCE_PROMPT
DEFAULT_TOOLS = [sqlmap_tool]


def make_subagent(tools: list = []):
    agent_tools = tools + DEFAULT_TOOLS
    subagent = SubAgentService.create_subagent_enable_all_human_in_the_loop(
        name="persistence",
        description="Persistence & cleanup (HITL)",
        prompt=PERSISTENCE_PROMPT,
        tools=agent_tools,
    )
    return subagent