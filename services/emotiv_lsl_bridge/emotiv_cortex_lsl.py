import argparse
import json
import os
import ssl
import sys
from itertools import count
from typing import Any

from pylsl import StreamInfo, StreamOutlet
from websocket import WebSocketConnectionClosedException, create_connection


EPOC_PLUS_CHANNELS = [
    "AF3",
    "F7",
    "F3",
    "FC5",
    "T7",
    "P7",
    "O1",
    "O2",
    "P8",
    "T8",
    "FC6",
    "F4",
    "F8",
    "AF4",
]


class CortexBridge:
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        participant_id: str,
        visit_id: str,
        cortex_url: str,
        sampling_rate: float,
    ) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.participant_id = participant_id
        self.visit_id = visit_id
        self.cortex_url = cortex_url
        self.sampling_rate = sampling_rate
        self.ws = None
        self.ids = count(1)
        self.cortex_token: str | None = None
        self.session_id: str | None = None
        self.outlet: StreamOutlet | None = None

    def connect(self) -> None:
        print(f"Connecting to Cortex at {self.cortex_url} ...")
        self.ws = create_connection(
            self.cortex_url,
            sslopt={"cert_reqs": ssl.CERT_NONE},
            timeout=10,
        )

    def call(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        if self.ws is None:
            raise RuntimeError("Cortex websocket is not connected.")

        request_id = next(self.ids)
        payload: dict[str, Any] = {
            "jsonrpc": "2.0",
            "method": method,
            "id": request_id,
        }
        if params is not None:
            payload["params"] = params

        self.ws.send(json.dumps(payload))

        while True:
            response = json.loads(self.ws.recv())
            if response.get("id") != request_id:
                continue
            if "error" in response:
                raise RuntimeError(f"Cortex {method} failed: {json.dumps(response['error'])}")
            return response

    def initialize_cortex(self) -> None:
        self.call("requestAccess", {
            "clientId": self.client_id,
            "clientSecret": self.client_secret,
        })

        auth = self.call("authorize", {
            "clientId": self.client_id,
            "clientSecret": self.client_secret,
        })
        self.cortex_token = auth["result"]["cortexToken"]

        headsets = self.call("queryHeadsets")
        headset_list = headsets.get("result", [])
        if not headset_list:
            raise RuntimeError("No Emotiv headset found. Start EMOTIV Launcher/App and connect the EPOC+ first.")

        headset_id = headset_list[0]["id"]
        print(f"Using headset: {headset_id}")

        self.call("controlDevice", {
            "command": "connect",
            "headset": headset_id,
        })

        session = self.call("createSession", {
            "cortexToken": self.cortex_token,
            "headset": headset_id,
            "status": "active",
        })
        self.session_id = session["result"]["id"]
        print(f"Cortex session: {self.session_id}")

    def initialize_lsl(self) -> None:
        stream_name = f"Emotiv_EPOCPlus_{self.participant_id}_{self.visit_id}"
        source_id = f"emotiv_epocplus_{self.participant_id}_{self.visit_id}"
        info = StreamInfo(
            stream_name,
            "EEG",
            len(EPOC_PLUS_CHANNELS),
            self.sampling_rate,
            "float32",
            source_id,
        )

        info.desc().append_child_value("manufacturer", "Emotiv")
        info.desc().append_child_value("model", "EPOC+")
        info.desc().append_child_value("participant_id", self.participant_id)
        info.desc().append_child_value("visit_id", self.visit_id)

        channels = info.desc().append_child("channels")
        for label in EPOC_PLUS_CHANNELS:
            channel = channels.append_child("channel")
            channel.append_child_value("label", label)
            channel.append_child_value("unit", "uV")
            channel.append_child_value("type", "EEG")

        self.outlet = StreamOutlet(info)
        print(f"Publishing LSL stream: {stream_name}")

    def stream(self) -> None:
        if self.cortex_token is None or self.session_id is None or self.outlet is None or self.ws is None:
            raise RuntimeError("Bridge is not initialized.")

        self.call("subscribe", {
            "cortexToken": self.cortex_token,
            "session": self.session_id,
            "streams": ["eeg"],
        })

        print("Streaming EEG to LSL. Press Ctrl+C to stop.")
        print("If this fails with an authorization/subscription error, raw EEG is not enabled for this Emotiv account/license.")

        try:
            while True:
                response = json.loads(self.ws.recv())
                if "eeg" not in response:
                    continue

                packet = response["eeg"]
                eeg_values = packet[2:16]
                if len(eeg_values) != len(EPOC_PLUS_CHANNELS):
                    continue

                self.outlet.push_sample([float(value) for value in eeg_values])
        except KeyboardInterrupt:
            print("\nStopping Emotiv LSL bridge.")
        except WebSocketConnectionClosedException as exc:
            raise RuntimeError("Cortex websocket closed.") from exc
        finally:
            try:
                self.call("unsubscribe", {
                    "cortexToken": self.cortex_token,
                    "session": self.session_id,
                    "streams": ["eeg"],
                })
            except Exception:
                pass
            self.ws.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stream Emotiv EPOC+ Cortex EEG data to LSL.")
    parser.add_argument("--client-id", default=os.getenv("EMOTIV_CLIENT_ID"))
    parser.add_argument("--client-secret", default=os.getenv("EMOTIV_CLIENT_SECRET"))
    parser.add_argument("--participant-id", default=os.getenv("LAB_PARTICIPANT_ID", "LAB_001"))
    parser.add_argument("--visit-id", default=os.getenv("LAB_VISIT_ID", "VISIT_001"))
    parser.add_argument("--cortex-url", default=os.getenv("EMOTIV_CORTEX_URL", "wss://localhost:6868"))
    parser.add_argument("--sampling-rate", type=float, default=float(os.getenv("EMOTIV_SAMPLING_RATE", "128")))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.client_id or not args.client_secret:
        print("Missing Cortex credentials. Set EMOTIV_CLIENT_ID and EMOTIV_CLIENT_SECRET.", file=sys.stderr)
        return 2

    bridge = CortexBridge(
        client_id=args.client_id,
        client_secret=args.client_secret,
        participant_id=args.participant_id,
        visit_id=args.visit_id,
        cortex_url=args.cortex_url,
        sampling_rate=args.sampling_rate,
    )
    bridge.connect()
    bridge.initialize_cortex()
    bridge.initialize_lsl()
    bridge.stream()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
