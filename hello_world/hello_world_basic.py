# basic example for starting the workflow (must have config.yaml in the root directory) #
import traceback
from datetime import datetime

import uvloop
from agents.hello_world_agent import HelloWorldAgent
from loguru import logger as _logger
from qurrent import (
    ImageContent,
    Message,
    QurrentConfig,
    TextContent,
    Workflow,
    console_agent,
    observable,
)


class HelloWorldBasic(Workflow):
    def __init__(self, config: QurrentConfig) -> None:
        super().__init__(config)

        self.hello_world_agent: HelloWorldAgent

    @classmethod
    async def create(cls, config: QurrentConfig) -> "HelloWorldBasic":
        self = await super().create(config)

        self.hello_world_agent = await HelloWorldAgent.create(
            yaml_config_path="./hello_world/agents/config/hello_world_agent.yaml",
            workflow_instance_id=self.workflow_instance_id,
        )

        self.hello_world_agent.set_important_information(
            role="user",
            content="Always include a smiley face emoji at the beginning of your response. No matter what the user asks.",
            index=-1,
        )

        self.hello_world_agent.message_thread.substitute_variables(
            {
                "todays_date": f"Today's date is {datetime.now().strftime('%Y-%m-%d')}",
            }
        )
        return self

    async def run(self) -> None:
        await self.save_identifier(
            {"workflow_instance_id": str(self.workflow_instance_id)}
        )
        await self.hello_world()

        # this is how we can save an output for a whole workflow
        await self.save_to_console(
            type="output",
            content="Successfully completed the 3 examples for the hello world workflow!",
        )

    @console_agent
    async def hello_world(self) -> None:
        """This is a simple Hello World Agent that showcases some basics for Qurrent Workflows"""
        await self.direct_agent_action()

        await self.agent_taking_actions()

        await self.image_content_example()

    @observable
    async def direct_agent_action(self) -> str:
        """This is a simple example of how to use a direct agent action"""
        response = await self.hello_world_agent.print_hello_world_gpt_response()
        _logger.info(f"Direct agent action: {response['response']}")

        await self.save_to_console(
            type="observable_output",
            content=f"Direct agent action was used with response: {response['response']}",
        )
        return response["response"]

    @observable
    async def agent_taking_actions(self) -> None:
        """This is a simple example showing an agent taking actions"""
        self.hello_world_agent.message_thread.append(
            Message(
                role="user",
                content="Respond with hello world using actions.",
            )
        )

        # Run the agent (this will do the LLM call and immediately return the response)
        response = await self.hello_world_agent()
        _logger.info(f"Response: {response}")

        # Get the action results (this will wait for the action to complete and return the result)
        action_result = await self.hello_world_agent.get_all_action_results()
        _logger.info(f"Using actions: {action_result}")

        await self.save_to_console(
            type="observable_output", content=f"The action result is: {action_result}"
        )

    @observable
    async def image_content_example(self) -> None:
        """
        Here we take in a model name, provide it with an image of a C program, and ask it to tell us what the output of the program would be.
        This is a simple example that shows how models are able to process image content.
        """
        message = Message(
            role="user",
            content=[
                TextContent(
                    "What would the output of this C program be? Make sure to respond in JSON format."
                ),
                ImageContent.from_url(
                    "https://i0.wp.com/www.agilenative.com/wp-content/uploads/2017/01/001-Agile-Hello-World.png"
                ),
            ],
        )
        self.hello_world_agent.message_thread.append(message)
        response = await self.hello_world_agent()
        message = f"Successfully demonstrated image content: {response['response']}"
        _logger.info(message)

        await self.save_to_console(
            type="observable_output",
            content=message,
        )


async def main() -> None:
    qconfig = await QurrentConfig.from_file("config.yaml")

    hello_world = await HelloWorldBasic.create(config=qconfig)

    try:
        await hello_world.run()
    except Exception as e:
        _logger.error(f"Error: {e} \n{traceback.format_exc()}")
        await hello_world.save_to_console(
            type="error", content="This workflow wasn't able to complete successfully"
        )
        await hello_world.close(status="failed")
    else:
        await hello_world.close(status="completed")


if __name__ == "__main__":
    uvloop.run(main())
