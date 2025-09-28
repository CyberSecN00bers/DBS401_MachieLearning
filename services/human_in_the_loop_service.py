from typing import Optional, Dict, NotRequired, Union, Any, List
from services.io_service import safe_parse_int_input, print_menu, notify
import json


class HumanInTheLoopService:

    @staticmethod
    def prompt_human_for_resume_cli(
        proposed_tool_call: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        menu_title = "Please choose an action:"
        menu_items = [
            "accept         -> allow the tool to run as-is",
            "edit           -> edit which tool/args to run",
            "response       -> do NOT run tool, instead append a textual response to the agent",
            "abort          -> stop the agent entirely",
        ]
        print_menu(menu_items, menu_title)

        choice = safe_parse_int_input(">", min_value=1, max_value=len(menu_items))
        if choice == 1:
            return [{"type": "accept"}]
        elif choice == 2:
            print(
                'Enter edited tool call JSON. Example: {"action": "nmap_tool", "args": {"target": "10.0.0.5", "arguments": "-sV -p 1433"}}'
            )
            raw = input("Edited call JSON: ").strip()
            try:
                payload = json.loads(raw)
                if "action" not in payload or "args" not in payload:
                    raise ValueError("must include 'action' and 'args' keys")
                return [{"type": "edit", "args": payload}]
            except Exception as e:
                print("Invalid JSON or format:", e)
                return [
                    {
                        "type": "response",
                        "args": "Operator provided invalid edit; aborting tool call.",
                    }
                ]
        elif choice == 3:
            text = input("Enter textual response (this will NOT run the tool): ")
            return [{"type": "response", "args": text}]
        else:
            return [{"type": "response", "args": "Operator aborted the test run."}]
