# basic example for starting the workflow (must have config.yaml in the root directory unless you specify a different path) #

import uvloop
from agents.hello_world_agent import HelloWorldAgent
from loguru import logger as _logger
from qurrent import Ingress, Message, QurrentConfig, Slack, Workflow, events, spawn_task


class HelloWorldSlack(Workflow):
    def __init__(self, config: QurrentConfig) -> None:
        super().__init__(config)

        self.hello_world_agent: HelloWorldAgent

    @classmethod
    async def create(cls, config: QurrentConfig) -> "HelloWorldSlack":
        self = await super().create(config)

        self.hello_world_agent = await HelloWorldAgent.create(
            yaml_config_path="./hello_world/agents/config/hello_world_agent.yaml",
            workflow_instance_id=self.workflow_instance_id,
        )
        return self

    async def run(self, slack_bot: Slack, event: events.BaseEvent) -> None:
        channel_id = slack_bot.get_channel_id_from_event(event)

        response = await self.hello_world_agent.print_hello_world_gpt_response()
        _logger.info(f"Direct agent function: {response}")

        await slack_bot.send_message(
            channel_id,
            response["response"],
        )

        self.hello_world_agent.message_thread.append(
            Message(
                role="user",
                content="Respond with hello world using actions.",
            )
        )
        response = await self.hello_world_agent()
        _logger.info(f"Using actions: {response['response']}")

        action_id = response["actions"][0]["action_id"]
        action_result = await self.hello_world_agent.get_action_result(action_id)

        await slack_bot.send_message(
            channel_id,
            f"{response['response']} {action_result}",
        )

        while True:
            user_response = await self.ingress.get_workflow_event(
                self.workflow_instance_id
            )
            if user_response["message"].lower() == "end":
                return
            _logger.info(f"Received message: {user_response}")
            self.hello_world_agent.message_thread.append(
                Message(role="user", content=user_response["message"])
            )
            response = await self.hello_world_agent()
            action_output = ""
            if "actions" in response and response["actions"]:
                action_id = response["actions"][0]["action_id"]
                action_output = await self.hello_world_agent.get_action_result(
                    action_id
                )

            await slack_bot.send_message(
                channel_id,
                f"{response['response']} {action_output}",
            )


async def handle_event(
    slack_bot: Slack,
    event: events.SlackMessage,
    config: QurrentConfig,
) -> None:
    _logger.info(f"Received message in handle event: {event}")

    hello_world = await HelloWorldSlack.create(config=config)
    channel_id = slack_bot.get_channel_id_from_event(event)

    await slack_bot.link(
        hello_world.workflow_instance_id,
        channel_id=channel_id,
        user_id=event["user_id"],
    )

    try:
        _logger.info(
            f"Running new workflow instance {hello_world.workflow_instance_id}"
        )
        await hello_world.run(slack_bot, event)
    except Exception as e:
        await slack_bot.send_message(
            channel_id,
            "An error occurred while running the workflow. Please try again later.",
        )
        await hello_world.save_to_console(type="error", content=f"{e}")
        await hello_world.close(status="failed")
    else:
        await hello_world.close(status="completed")

    await slack_bot.unlink(channel_id=channel_id, user_id=event["user_id"])


async def main() -> None:
    qconfig = await QurrentConfig.from_file("config.yaml")

    slack_bot = await Slack.start(qconfig)
    ingress: Ingress = qconfig["INGRESS"]

    while True:
        event, _ = await ingress.get_start_event()
        spawn_task(handle_event(slack_bot, event, qconfig), is_main=True)


if __name__ == "__main__":
    uvloop.run(main())
