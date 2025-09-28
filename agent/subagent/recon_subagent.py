from services.subagent_service import SubAgentService
from agent.prompt.subagent_prompt import RECON_PROMPT
from tools.nmap import nmap_tool
from tools.sqlmap import sqlmap_tool


NAME = "recon"
DESCRIPTION = "Network & service discovery"
PROMPT = RECON_PROMPT
DEFAULT_TOOLS = [nmap_tool]


def make_subagent(tools: list = []):
    agent_tools = tools + DEFAULT_TOOLS
    subagent = SubAgentService.create_subagent_enable_all_human_in_the_loop(
        name="recon",
        description="Network & service discovery",
        prompt=RECON_PROMPT,
        tools=agent_tools,
    )
    return subagent
