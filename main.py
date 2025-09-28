from dotenv import load_dotenv
from deepagents import create_deep_agent

# Internal
from utils.system_check import check_system
from services.io_service import safe_input, banner, safe_parse_int_input, notify
from utils.installer import install_dependencies
from services.validator_service import is_valid_ip, is_valid_url
from agent.pentest import build_agent, run_interactive_scan
from agent.prompt.master_instruction import USER_PROMPT_TEMPLATE
from configs.app_configs import AppConfig

SYSTEM_INFO = check_system()
install_dependencies(
    SYSTEM_INFO["missing_system_packages"], SYSTEM_INFO["missing_python_packages"]
)

import logging
logging.basicConfig(level=logging.DEBUG)


# ================================================= banner =================================================
load_dotenv()
config = AppConfig()
banner()

# ================================================= main =================================================
agent = build_agent()

# Operator must explicitly confirm they have permission to test the target.
io = safe_input(
    "Do you confirm you have authorization to test systems you will specify? [yes/No]:"
)
ok = io.strip().lower()
if ok not in ("y", "yes"):
    notify("Authorization not confirmed. Exiting.")
    exit(1)

host = safe_input("Enter the target host (e.g., 192.168.1.100):", is_valid_ip, "127.0.0.1")
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

run_interactive_scan(agent, prompt)
