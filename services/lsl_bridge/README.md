# LSL Marker Stream

This service publishes reVISit study markers to Lab Streaming Layer through a small WebSocket bridge.

Browsers cannot create native LSL outlets directly. The frontend sends marker JSON to this bridge over WebSocket, and the bridge publishes each message as one sample on a single-channel LSL marker stream.

## Run The Bridge

For acquisition sessions, run the bridge on the same machine/network namespace as the LSL recorder whenever possible:

```sh
cd services/lsl_bridge
python3 -m pip install -r requirements.txt
python3 app.py
```

With Docker Compose, for development only:

```sh
docker compose --profile lsl-docker up --build lsl-bridge
```

Docker is convenient for the WebSocket endpoint, but native execution can be more reliable for LSL discovery because LSL uses multicast networking.

The default browser WebSocket URL is:

```txt
ws://127.0.0.1:8765
```

The default LSL stream is:

```txt
name: reVISit Markers
type: Markers
source_id: revisit-lsl-marker-stream
```

You can override the stream metadata with:

```sh
LSL_STREAM_NAME="My Study Markers" \
LSL_STREAM_TYPE="Markers" \
LSL_SOURCE_ID="my-study-markers" \
VITE_LSL_ENABLED=true \
docker compose up --build study lsl-bridge
```

## Enable Per Study

Instead of rebuilding with `VITE_LSL_ENABLED=true`, a study can enable markers in `uiConfig`:

```json
{
  "uiConfig": {
    "lsl": {
      "enabled": true,
      "url": "ws://127.0.0.1:8765"
    }
  }
}
```

## Marker Shape

Each LSL sample is a JSON string with this general shape:

```json
{
  "event": "trial_start",
  "timestamp": 1760000000000,
  "studyId": "HAIC_study",
  "participantId": "participant-1",
  "component": "intro",
  "identifier": "intro_0",
  "trialOrder": "0",
  "data": {}
}
```

Built-in events include `trial_start`, `trial_end`, `study_unload`, and iframe events prefixed with `iframe_`.

Custom HTML tasks can publish iframe markers with:

```js
Revisit.postEvent("guess_submitted", { round: 1, attempt: 2 });
```

That becomes an LSL event named `iframe_guess_submitted`.
