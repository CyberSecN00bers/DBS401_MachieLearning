from services.subagent_service import SubAgentService
from agent.prompt.subagent_prompt import REPORT_PROMPT
from tools.nmap import nmap_tool
from tools.sqlmap import sqlmap_tool
from deepagents.tools import ls, read_file, write_file, edit_file


NAME = "reporting"
DESCRIPTION = "Reporting & remediation"
PROMPT = REPORT_PROMPT
DEFAULT_TOOLS = [ls, read_file, write_file, edit_file]


def make_subagent(tools: list = []):
    agent_tools = tools + DEFAULT_TOOLS
    subagent = SubAgentService.create_subagent_enable_all_human_in_the_loop(
        name="reporting",
        description="Reporting & remediation",
        prompt=REPORT_PROMPT,
        tools=agent_tools,
    )
    return subagent
