from services.subagent_service import SubAgentService
from agent.prompt.subagent_prompt import RECON_PROMPT
from tools.nmap import nmap_tool
from tools.sqlmap import sqlmap_tool
from tools.authenticate import mssql_check_credentials
from deepagents.tools import ls, read_file, write_file, edit_file


NAME = "recon"
DESCRIPTION = "Network & service discovery"
PROMPT = RECON_PROMPT
DEFAULT_TOOLS = [nmap_tool, ls, read_file, write_file, edit_file, mssql_check_credentials]


def make_subagent(tools: list = []):
    agent_tools = tools + DEFAULT_TOOLS
    subagent = SubAgentService.create_subagent_enable_all_human_in_the_loop(
        name="recon",
        description="Network & service discovery",
        prompt=RECON_PROMPT,
        tools=agent_tools,
    )
    return subagent
