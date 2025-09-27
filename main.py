from dotenv import load_dotenv

load_dotenv()

from deepagents import create_deep_agent


from utils.system_check import check_system
from utils.installer import install_dependencies

SYSTEM_INFO = check_system()
install_dependencies(
    SYSTEM_INFO["missing_binaries"], SYSTEM_INFO["missing_python_packages"]
)

from agents.pentest import build_agent, run_interactive_scan


if __name__ == "__main__":
    print("=== DeepAgents HITL demo runner ===")
    agent = build_agent()

    # Operator must explicitly confirm they have permission to test the target.
    ok = (
        input(
            "Do you confirm you have authorization to test systems you will specify? [yes/no]: "
        )
        .strip()
        .lower()
    )
    if ok not in ("y", "yes"):
        print("Authorization not confirmed. Exiting.")
        exit(1)

    # Example prompt (modify as desired)
    prompt = input(
        "Enter the security testing instruction for the agent (e.g. 'Scan 192.168.1.100 for open ports and vulnerabilities'):\n"
    )

    run_interactive_scan(agent, prompt)
