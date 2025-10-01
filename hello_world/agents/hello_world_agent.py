from typing import Any, Dict

from qurrent import Agent, Message, llmcallable


class HelloWorldAgent(Agent):
    # Example for how to pass custom arguments when creating the agent
    # @classmethod
    # async def create(
    #     cls, yaml_config_path: str, workflow_instance_id: UUID, custom_argument: str
    # ) -> "HelloWorldAgent":
    #     self = await super().create(yaml_config_path, workflow_instance_id)
    #     self.custom_argument = custom_argument
    #     return self

    @llmcallable
    async def hello_world_function(self, content_to_print: str) -> str:
        """
        Args: "content_to_print" (str): The content to print
        Description: This function prints the content that is passed to it.
        """
        return content_to_print

    async def print_hello_world_gpt_response(
        self,
    ) -> Dict[str, Any]:
        self.message_thread.append(
            Message(role="user", content="Respond with hello world, do not use actions")
        )

        return await self()
