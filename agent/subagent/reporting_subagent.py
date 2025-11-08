from services.subagent_service import SubAgentService
from agent.prompt.subagent_prompt import REPORT_PROMPT
from tools.nmap import nmap_tool
from tools.sqlmap import sqlmap_tool
from tools.file_writer import file_writer_tool, create_html_report_template
from deepagents.tools import ls, read_file, edit_file


NAME = "reporting"
DESCRIPTION = "Reporting & remediation"
PROMPT = REPORT_PROMPT
# Using real filesystem writer instead of virtual write_file
DEFAULT_TOOLS = [ls, read_file, edit_file, file_writer_tool]


def make_subagent(tools: list = []):
    agent_tools = tools + DEFAULT_TOOLS
    subagent = SubAgentService.create_subagent_enable_all_human_in_the_loop(
        name="reporting",
        description="Reporting & remediation",
        prompt=REPORT_PROMPT,
        tools=agent_tools,
    )
    return subagent
