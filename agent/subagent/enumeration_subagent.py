from services.subagent_service import SubAgentService
from agent.prompt.subagent_prompt import ENUM_PROMPT
from tools.nmap import nmap_tool

NAME = "enumeration"
DESCRIPTION = "SQL Server enumeration"
PROMPT = ENUM_PROMPT
DEFAULT_TOOLS = [nmap_tool]


def make_subagent(tools: list = []):
    agent_tools = tools + DEFAULT_TOOLS
    subagent = SubAgentService.create_subagent_enable_all_human_in_the_loop(
        name="enumeration",
        description="SQL Server enumeration",
        prompt=ENUM_PROMPT,
        tools=agent_tools,
    )
    return subagent
