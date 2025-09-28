from services.subagent_service import SubAgentService
from agent.prompt.subagent_prompt import VULN_PROMPT
from tools.nmap import nmap_tool
from tools.sqlmap import sqlmap_tool


NAME = "vuln_scan"
DESCRIPTION = "Vulnerability & misconfiguration scanning"
PROMPT = VULN_PROMPT
DEFAULT_TOOLS = [nmap_tool, sqlmap_tool]


def make_subagent(tools: list = []):
    agent_tools = tools + DEFAULT_TOOLS
    subagent = SubAgentService.create_subagent_enable_all_human_in_the_loop(
        name="vuln_scan",
        description="Vulnerability & misconfiguration scanning",
        prompt=VULN_PROMPT,
        tools=agent_tools,
    )
    return subagent
