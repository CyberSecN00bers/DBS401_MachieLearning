from services.subagent_service import SubAgentService
from agent.prompt.subagent_prompt import ENUM_PROMPT
from tools.nmap import nmap_tool
from tools.mssql import mssql_agent_tool
from deepagents.tools import ls, read_file, write_file, edit_file
from tools.authenticate import mssql_check_credentials

NAME = "enumeration"
DESCRIPTION = "SQL Server enumeration"
PROMPT = ENUM_PROMPT
DEFAULT_TOOLS = [
    nmap_tool,
    mssql_agent_tool,
    ls,
    read_file,
    write_file,
    edit_file,
    mssql_check_credentials,
]


def make_subagent(tools: list = []):
    agent_tools = tools + DEFAULT_TOOLS
    subagent = SubAgentService.create_subagent_enable_all_human_in_the_loop(
        name="enumeration",
        description="SQL Server enumeration",
        prompt=ENUM_PROMPT,
        tools=agent_tools,
    )
    return subagent
