# basic example for starting the workflow from a generic web server
import traceback
from typing import Dict
from uuid import UUID

import uvloop
from loguru import logger as _logger
from quart import Response, request
from qurrent import (
    HTTPMethod,
    Ingress,
    QurrentConfig,
    WebServer,
    events,
    spawn_task,
)

from hello_world.hello_world_basic import HelloWorldBasic


class GenericWebServerIntegration:
    def __init__(self, ingress: Ingress):
        self.ingress = ingress

    @staticmethod
    async def start(
        config: QurrentConfig,
        host: str = "0.0.0.0",
        port: int = 8000,
        webhook_endpoint: str = "/start",
    ) -> "GenericWebServerIntegration":
        self = GenericWebServerIntegration(config.get("INGRESS"))

        server = await WebServer.start(host, port)

        @server.route(webhook_endpoint, methods=[HTTPMethod.POST])
        async def webhook_listener() -> Response:
            data: Dict = await request.get_json()

            await self.process_webhook(data)

            return Response(status=200)

        return self

    async def process_webhook(self, data: Dict) -> None:
        source_id = data.get("source_id")
        workflow_instance_id = self.ingress.get_workflow_for_source(source_id)

        event = events.GenericWebhookEvent(
            workflow_instance_id=workflow_instance_id,
            data=data,
        )
        await self.ingress.add_event(event)

    def link(self, workflow_instance_id: UUID, source_id: UUID) -> None:
        self.ingress.register_source(source_id, workflow_instance_id)

    def unlink(self, source_id: UUID) -> None:
        self.ingress.unregister_source(source_id)


async def handle_event(event: events.BaseEvent, config: QurrentConfig) -> None:
    _logger.info(f"Received message in handle event: {event}")

    hello_world = await HelloWorldBasic.create(config=config)

    try:
        await hello_world.hello_world()
    except Exception as e:
        await hello_world.save_to_console(
            type="error", content=f"{e} \n{traceback.format_exc()}"
        )
        await hello_world.close(status="failed")
    else:
        await hello_world.close(status="completed")


async def main() -> None:
    qconfig = await QurrentConfig.from_file("config.yaml")

    await GenericWebServerIntegration.start(qconfig)

    ingress: Ingress = qconfig["INGRESS"]

    while True:
        event, _ = await ingress.get_start_event()
        spawn_task(handle_event(event, qconfig), is_main=True)


if __name__ == "__main__":
    uvloop.run(main())
