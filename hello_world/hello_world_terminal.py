# basic example for creating a terminal and running a simple HTTP server on it
import traceback
from typing import Dict, List, Tuple
from uuid import UUID

import uvloop
from loguru import logger as _logger
from qurrent import (
    ActionResult,
    Agent,
    FileIOMixin,
    Message,
    QurrentConfig,
    Terminal,
    Workflow,
)


# Adding FileIOMixin to the agent allows it to read and write files, and use the terminal
class HelloWorldAgent(Agent, FileIOMixin):
    def __init__(
        self,
        yaml_config_path: str,
        workflow_instance_id: UUID,
    ) -> None:
        super().__init__(
            yaml_config_path=yaml_config_path,
            workflow_instance_id=workflow_instance_id,
        )

        # Need to keep track of terminals, this must be added to the agent
        self.terminals: Dict[str, Terminal] = {}

    async def call_with_message(
        self, message: str
    ) -> Tuple[str, Dict[str, List[ActionResult]]]:
        self.message_thread.append(Message(role="user", content=message))
        response = await self()
        action_output = await self.get_all_action_results()
        _logger.info(
            f"Direct agent function: {response}\nAction output: {action_output}"
        )
        return response, action_output


class HelloWorldTerminal(Workflow):
    def __init__(self, config: QurrentConfig) -> None:
        super().__init__(config)

        self.hello_world_agent: HelloWorldAgent

    @classmethod
    async def create(cls, config: QurrentConfig) -> "HelloWorldTerminal":
        self = await super().create(config)

        self.hello_world_agent = await HelloWorldAgent.create(
            yaml_config_path="./hello_world/agents/config/hello_world_agent.yaml",
            workflow_instance_id=self.workflow_instance_id,
        )
        return self

    async def run(self) -> bool:
        """
        # Multiple calls to the agent
        await self.hello_world_agent.call_with_message(
            "Create a simple flask app file to print Hello World"
        )

        await self.hello_world_agent.call_with_message(
            "Create a terminal and serve the HTTP server"
        )

        await self.hello_world_agent.call_with_message(
            "Make a request to the server using curl using a new terminal"
        )

        await self.hello_world_agent.call_with_message(
            "Close the server"
        )
        """

        # Agents can take many actions in one call
        await self.hello_world_agent.call_with_message(
            """Create a simple flask app file to print Hello World on port 8080.
            Then create a terminal and serve the HTTP server.
            Make a request to the server using curl using a new terminal.
            Close the server."""
        )

        # When a command times out
        _, action_out = await self.hello_world_agent.call_with_message(
            "In this terminal, run a command that will never finish, set a timeout of 5 seconds"
        )

        for action_name, action_resp in action_out.items():
            _logger.info(f"Action: {action_name}, Response: {action_resp}")
            if isinstance(action_resp, dict) and "error" in action_resp:
                # Call a terminal evaluator here, for example to help find out what went wrong
                _logger.info(f"Error: {action_resp['error']}")

        return True


async def main() -> None:
    qconfig = await QurrentConfig.from_file("config.yaml")

    hello_world = await HelloWorldTerminal.create(config=qconfig)

    try:
        await hello_world.run()
    except Exception as e:
        await hello_world.save_to_console(
            type="error", content=f"{e} \n{traceback.format_exc()}"
        )
        await hello_world.close(status="failed")
    else:
        await hello_world.close(status="completed")


if __name__ == "__main__":
    uvloop.run(main())
