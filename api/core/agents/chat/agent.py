from ..base import BaseAgent, AgentMessage

from utils import get_current_datetime, get_processing_time_ms

class ChatAgent(BaseAgent):
    def __init__(self):
        super().__init__()
        self.logger.info(f"ChatAgent初始化完成: {self.agent_id}")

    async def process_message(self, message: AgentMessage) -> AgentMessage:
        pass