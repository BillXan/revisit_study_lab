import asyncio
import json
import logging
import os
from typing import Any

from pylsl import StreamInfo, StreamOutlet
from websockets.asyncio.server import serve


HOST = os.getenv("LSL_BRIDGE_HOST", "0.0.0.0")
PORT = int(os.getenv("LSL_BRIDGE_PORT", "8765"))
STREAM_NAME = os.getenv("LSL_STREAM_NAME", "reVISit Markers")
STREAM_TYPE = os.getenv("LSL_STREAM_TYPE", "Markers")
SOURCE_ID = os.getenv("LSL_SOURCE_ID", "revisit-lsl-marker-stream")

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("lsl-bridge")


def create_outlet() -> StreamOutlet:
  info = StreamInfo(
    STREAM_NAME,
    STREAM_TYPE,
    1,
    0,
    "string",
    SOURCE_ID,
  )
  info.desc().append_child_value("manufacturer", "reVISit")
  info.desc().append_child("channels").append_child("channel").append_child_value("label", "marker")
  return StreamOutlet(info)


OUTLET = create_outlet()


def normalize_marker(raw: str) -> str:
  try:
    payload: dict[str, Any] = json.loads(raw)
  except json.JSONDecodeError:
    payload = {"event": "raw_marker", "data": {"value": raw}}

  if "timestamp" not in payload:
    payload["timestamp"] = None

  return json.dumps(payload, separators=(",", ":"), ensure_ascii=False)


async def handle_connection(websocket) -> None:
  peer = websocket.remote_address
  logger.info("Client connected: %s", peer)
  try:
    async for message in websocket:
      marker = normalize_marker(str(message))
      OUTLET.push_sample([marker])
      logger.debug("Published marker: %s", marker)
  finally:
    logger.info("Client disconnected: %s", peer)


async def main() -> None:
  logger.info(
    "Publishing LSL stream '%s' (%s) on ws://%s:%s",
    STREAM_NAME,
    STREAM_TYPE,
    HOST,
    PORT,
  )
  async with serve(handle_connection, HOST, PORT):
    await asyncio.Future()


if __name__ == "__main__":
  asyncio.run(main())
