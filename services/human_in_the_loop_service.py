from typing import Optional, Dict, NotRequired, Union, Any, List
from services.io_service import safe_parse_int_input, print_menu, notify, LogLevel
import json


class HumanInTheLoopService:

    @staticmethod
    def prompt_human_for_resume_cli(
        proposed_tool_call: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Prompt operator for decision on tool execution.
        
        Args:
            proposed_tool_call: Optional details about the proposed tool call
            
        Returns:
            List of resume actions
        """
        menu_title = "\n╔════════════════════════════════════════════════════════════════╗"
        print(menu_title)
        print("║           🔐 HUMAN-IN-THE-LOOP APPROVAL REQUIRED              ║")
        print("╚════════════════════════════════════════════════════════════════╝\n")
        
        menu_items = [
            "✅ Accept       → Allow the tool to run as proposed",
            "✏️  Edit         → Modify tool arguments before execution",
            "💬 Response     → Skip tool execution and provide text response",
            "🛑 Abort        → Stop the agent completely"
        ]
        print_menu(menu_items, "Please choose an action:")

        choice = safe_parse_int_input("\n> ", min_value=1, max_value=len(menu_items))
        
        if choice == 1:
            notify("✅ Tool execution approved", LogLevel.SUCCESS)
            return [{"type": "accept"}]
            
        elif choice == 2:
            print("\n" + "─" * 70)
            print("📝 Edit Tool Call")
            print("─" * 70)
            print('Format: {"action": "tool_name", "args": {"param": "value"}}')
            print('Example: {"action": "nmap_tool", "args": {"target": "192.168.1.1", "ports": "80,443"}}')
            print("─" * 70 + "\n")
            
            raw = input("Enter edited JSON: ").strip()
            try:
                payload = json.loads(raw)
                if "action" not in payload or "args" not in payload:
                    raise ValueError("must include 'action' and 'args' keys")
                notify("✏️  Tool call edited", LogLevel.INFO)
                return [{"type": "edit", "args": payload}]
            except Exception as e:
                notify(f"❌ Invalid JSON: {e}", LogLevel.ERROR)
                return [
                    {
                        "type": "response",
                        "args": "Operator provided invalid edit; aborting tool call.",
                    }
                ]
                
        elif choice == 3:
            print("\n" + "─" * 70)
            text = input("💬 Enter your response to the agent: ").strip()
            notify("💬 Response provided (tool skipped)", LogLevel.INFO)
            return [{"type": "response", "args": text}]
            
        else:
            notify("🛑 Agent execution aborted by operator", LogLevel.WARN)
            return [{"type": "response", "args": "Operator aborted the test run."}]
