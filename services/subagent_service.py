from typing import Optional, Dict, NotRequired, Union, Any, List
from langchain_core.language_models import LanguageModelLike
from langchain_core.tools import BaseTool
from langchain.agents.middleware import HumanInTheLoopMiddleware


class SubAgentService:

    @staticmethod
    def create_subagent_enable_all_human_in_the_loop(
        name: str,
        description: str,
        prompt: str,
        tools: Optional[List[BaseTool]] = None,
        model: Optional[Union[LanguageModelLike, dict[str, Any]]] = None,
    ):
        tool_configs = {tool.__name__: True for tool in tools} if tools else None
        return SubAgentService.create_subagent_with_human_in_the_loop(
            name, description, prompt, tools, model, tool_configs
        )

    @staticmethod
    def create_subagent_with_human_in_the_loop(
        name: str,
        description: str,
        prompt: str,
        tools: Optional[List[BaseTool]] = None,
        model: Optional[Union[LanguageModelLike, Dict[str, Any]]] = None,
        tool_configs: Optional[Dict[str, bool]] = None,
    ):
        sub_agent = {
            "name": name,
            "description": description,
            "prompt": prompt,
        }
        if tools:
            sub_agent["tools"] = tools
        if model:
            sub_agent["model"] = model

        # Tool config convert to HumanInTheLoop middleware
        if tool_configs:
            sub_agent["middleware"] = [
                HumanInTheLoopMiddleware(interrupt_on=tool_configs)
            ]
        return sub_agent
