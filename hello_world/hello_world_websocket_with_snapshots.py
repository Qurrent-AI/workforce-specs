# basic example for starting the workflow from a generic web socket server
import asyncio
import json
import ssl
import traceback
from typing import Any, Optional, Set
from uuid import UUID

import uvloop
from agents.hello_world_agent import HelloWorldAgent
from loguru import logger as _logger
from qurrent import (
    Ingress,
    Message,
    QurrentConfig,
    Workflow,
    console_agent,
    events,
    load_workflow_snapshot,
    observable,
    spawn_task,
)
from websockets import WebSocketServerProtocol, serve
from websockets.exceptions import ConnectionClosedError


class GenericWebSocketIntegration:
    """WebSocket server for sending and receiving events to/from connected clients

    This example can be tested with the messenger demo: https://github.com/Qurrent-AI/messenger-demo
    """

    def __init__(
        self,
        ingress: Ingress,
        url: str = "localhost",
        port: int = 5678,
    ) -> None:
        _logger.info(f"Starting websocket server on {url}:{port}")
        self.ingress = ingress
        self.url = url
        self.port = port
        self.clients: Set[WebSocketServerProtocol] = set()

    @staticmethod
    async def start(config: QurrentConfig) -> "GenericWebSocketIntegration":
        """Start the websocket server"""
        ws = GenericWebSocketIntegration(
            config["INGRESS"],
            config["WS_URL"],
            config["WS_PORT"],
        )

        certificate_path = config.get("WS_CERTIFICATE_PATH")
        private_key_path = config.get("WS_PRIVATE_KEY_PATH")

        ssl_context = None
        if certificate_path and private_key_path:
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ssl_context.load_cert_chain(
                certfile=certificate_path, keyfile=private_key_path
            )

        spawn_task(ws._serve(ssl_context), is_main=True)

        return ws

    async def send(self, source_id: Any, message: str) -> None:
        """Send a message with a source id to all connected clients"""
        obj = {
            "source_id": source_id,
            "message": message,
        }
        await self._send_event_to_clients(json.dumps(obj))

    async def _send_event_to_clients(self, event: str) -> None:
        """Send an event to all connected clients"""
        for client in self.clients:
            await client.send(event)

    async def _serve(self, ssl_context: Optional[ssl.SSLContext]) -> None:
        """Start serving the websocket"""
        async with serve(self.handler, self.url, self.port, ssl=ssl_context):
            await asyncio.Future()  # run forever

    async def handler(self, websocket: WebSocketServerProtocol, path: str) -> None:
        """Register new clients and handle messages"""
        self.clients.add(websocket)
        await self._receive_messages(websocket)
        await self._close_connection(websocket)

    async def _receive_messages(self, websocket: WebSocketServerProtocol) -> None:
        """Receive and handle messages from the websocket"""
        try:
            async for message in websocket:
                if isinstance(message, bytes):
                    message = message.decode("utf-8")

                await self._process_message(websocket, message)
        except ConnectionClosedError:
            pass

    async def _process_message(
        self, websocket: WebSocketServerProtocol, message: str
    ) -> None:
        """Process a single message received from the websocket"""

        try:
            message_obj = json.loads(message)
        except json.JSONDecodeError:
            _logger.debug("Invalid JSON")
            return

        if "source_id" not in message_obj:
            _logger.debug("Missing source_id")
            return

        if "message" not in message_obj:
            _logger.debug("Missing message")
            return

        event = events.GenericWebhookEvent(
            workflow_instance_id=None,  # Set to None, will be determined by Ingress
            source_id=message_obj["source_id"],
            data={"message": message_obj["message"]},
        )

        await self.ingress.add_event(event)

    async def _close_connection(self, websocket: WebSocketServerProtocol) -> None:
        """Close the websocket connection and remove the client"""
        if websocket.open:
            await websocket.close()
        self.clients.remove(websocket)

    async def link(self, workflow_instance_id: UUID, source_id: Any) -> None:
        """Link a source id to a workflow instance id"""
        await self.ingress.register_source(source_id, workflow_instance_id)

    async def unlink(self, source_id: Any) -> None:
        """Remove a source id from the registry"""
        await self.ingress.unregister_source(source_id)


class HelloWorldWebSocketSnapshot(Workflow):
    def __init__(self, config: QurrentConfig) -> None:
        super().__init__(config)

        self.hello_world_agent: HelloWorldAgent

    @classmethod
    async def create(cls, config: QurrentConfig) -> "HelloWorldWebSocketSnapshot":
        self = await super().create(config)

        self.hello_world_agent = await HelloWorldAgent.create(
            yaml_config_path="./hello_world/agents/config/hello_world_agent.yaml",
            workflow_instance_id=self.workflow_instance_id,
        )
        return self

    @console_agent
    async def hello_world_chat(self, input_message: str) -> str:
        """This is a simple chat agent that can be used to test the websocket integration and the snapshot functionality"""
        response = await self.generate_response(input_message)
        return response

    @observable
    async def generate_response(self, input_message: str) -> str:
        """This is a simple observable agent that can be used to test the websocket integration and the snapshot functionality"""
        self.hello_world_agent.message_thread.append(
            Message(role="user", content=input_message)
        )
        response = await self.hello_world_agent()
        await self.save_to_console(
            type="observable_output",
            content=f"Input message: {input_message}\nThe agent responded with: {response['response']}\nNext steps: Wait for user input",
        )
        return response["response"]

    async def run(
        self,
        ws: GenericWebSocketIntegration,
        event: events.BaseEvent,
        input_message: str,
    ) -> bool:
        while True:
            if not input_message:
                secondary_event = await self.ingress.get_workflow_event(
                    self.workflow_instance_id
                )
                input_message = secondary_event["data"]["message"]
            if input_message == "end":
                print("Ending workflow")
                return True

            response = await self.hello_world_chat(input_message)
            # Send the action response back over the websocket
            await ws.send(event["source_id"], response)

            input_message = ""
            await self.save_snapshot()


def process_event(
    event: events.GenericWebhookEvent,
) -> Optional[str]:
    # get input message from event
    input_message = event["data"]["message"]

    if input_message:
        return input_message
    else:
        return None


async def handle_event(
    ws: GenericWebSocketIntegration,
    event: events.GenericWebhookEvent,
    config: QurrentConfig,
    new_workflow_needed: bool,
) -> None:
    workflow_instance_id = event.get("workflow_instance_id")
    workflow: Optional[HelloWorldWebSocketSnapshot] = None

    if new_workflow_needed:
        _logger.info("Starting new workflow instance")
        workflow = await HelloWorldWebSocketSnapshot.create(config=config)
        await ws.link(workflow.workflow_instance_id, event["source_id"])
    else:
        _logger.info(f"Resuming workflow instance {workflow_instance_id}")
        workflow = await load_workflow_snapshot(
            config=config,
            workflow_class=HelloWorldWebSocketSnapshot,
            workflow_instance_id=workflow_instance_id,
        )
        if not workflow:
            _logger.error(f"Workflow instance {workflow_instance_id} not found")
            return

    try:
        input_message = process_event(event)
        if not input_message:
            _logger.debug("Event does not contain a message")
            return

        success = await workflow.run(ws, event, input_message)
        if success:
            await workflow.close(status="completed")
            await workflow.delete_snapshot()
            await ws.unlink(event["source_id"])
    except Exception as e:
        await workflow.save_to_console(
            type="error", content=f"{e} \n{traceback.format_exc()}"
        )
        await workflow.close(status="failed")
        await ws.unlink(event["source_id"])


async def main() -> None:
    qconfig = await QurrentConfig.from_file("config.yaml")
    ws = await GenericWebSocketIntegration.start(qconfig)
    ingress: Ingress = qconfig["INGRESS"]

    while True:
        _logger.info("Waiting for event")
        event, new_workflow_needed = await ingress.get_start_event(use_snapshots=True)
        spawn_task(
            handle_event(ws, event, qconfig, new_workflow_needed),
            is_main=True,
        )


if __name__ == "__main__":
    uvloop.run(main())
