from dataclasses import dataclass

from openai.types.chat import ChatCompletionToolParam


@dataclass
class ToolArgument:
    name: str
    type: str
    description: str
    required: bool = True


@dataclass
class ToolDefinition:
    name: str
    description: str
    arguments: list[ToolArgument]

    def to_openai_tool(self) -> ChatCompletionToolParam:
        """转换为 OpenAI function calling 格式"""
        properties = {}
        required = []

        for arg in self.arguments:
            prop = {
                "type": arg.type,
                "description": arg.description,
            }

            # OpenAI 要求 array 类型必须有 items 定义
            if arg.type == "array":
                prop["items"] = {"type": "string"}  # 默认为字符串数组

            properties[arg.name] = prop

            if arg.required:
                required.append(arg.name)

        tool: ChatCompletionToolParam = {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }

        return tool


@dataclass
class AgentGoal:
    id: str
    category_tag: str
    agent_name: str
    agent_friendly_description: str
    tools: list[ToolDefinition]
    description: str = "Description of the tools purpose and overall goal"
    starter_prompt: str = "Initial prompt to start the conversation"
    example_conversation_history: str = "Example conversation history to help the AI agent understand the context of the conversation"