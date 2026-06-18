# Local Lab Setup With reVISit, LSL, Emotiv EPOC+, Tobii Pro Fusion, And LabRecorder

This is the recommended setup for the lab computer when EEG, eye tracking, and reVISit task events must be synchronized.

Run the study on the same Windows lab PC that records the data. The website/API can run in Docker, but the LSL marker bridge should run natively on Windows so LabRecorder can reliably discover it.

## Target Architecture

```text
Windows lab PC
├─ Docker: reVISit website + HAIC API
├─ Native Python: reVISit WebSocket-to-LSL marker bridge
├─ Emotiv EPOC+ software or Python Cortex-to-LSL bridge
├─ Tobii Pro Fusion software or Tobii-to-LSL bridge
└─ LabRecorder records all LSL streams into one .xdf file
```

Expected LabRecorder streams:

```text
reVISit Markers
Emotiv EEG stream
Tobii gaze stream
```

## Why The LSL Bridge Runs Natively

The study config uses:

```json
"lsl": {
  "enabled": true,
  "url": "ws://127.0.0.1:8765"
}
```

In a browser, `127.0.0.1` means the machine running the browser. If the study is opened on the lab PC, the bridge must listen on the lab PC. LSL discovery also uses local networking/multicast, which is more reliable outside Docker, especially on Windows.

Docker is still useful for hosting the website and HAIC API locally.

## 1. Clone And Prepare The Repo

Open PowerShell on the Windows lab PC:

```powershell
git clone <repository-url> revisit_study_lab
cd revisit_study_lab
```

If the repo already exists:

```powershell
cd revisit_study_lab
git pull
```

## 2. Start The Website And HAIC API With Docker

The default Docker Compose setup starts `study` and `haic-api`. The `lsl-bridge` service is intentionally behind the optional `lsl-docker` profile and is not started by default.

```powershell
docker compose up --build -d
```

Check:

```powershell
docker compose ps
```

Open the study locally:

```text
http://localhost:8080/HAIC_study/?Lab_participant_ID=LAB_001
```

For each participant, change the ID:

```text
http://localhost:8080/HAIC_study/?Lab_participant_ID=LAB_002
http://localhost:8080/HAIC_study/?Lab_participant_ID=LAB_003
```

## 3. Start The reVISit LSL Marker Bridge Natively

Open a second PowerShell terminal:

```powershell
cd revisit_study_lab
py -m pip install -r services\lsl_bridge\requirements.txt
py services\lsl_bridge\app.py
```

Expected output:

```text
Publishing LSL stream 'reVISit Markers' (Markers) on ws://0.0.0.0:8765
```

Keep this terminal open during recording.

## 4. Start Emotiv EPOC+ As An LSL Stream

Without an EmotivPRO / raw EEG license, raw EPOC+ EEG may not be available. First verify whether your Emotiv account/device can expose raw EEG through the Cortex API.

Preferred options:

1. If available, use EmotivPRO's built-in LSL outlet and enable raw EEG.
2. Otherwise, use a Python Cortex-to-LSL bridge.

The bridge must create an LSL stream with type `EEG`. If the Cortex API rejects subscription to the `eeg` stream, the current Emotiv license does not expose raw EEG.

Minimum Python packages for a custom bridge:

```powershell
py -m pip install -r services\emotiv_lsl_bridge\requirements.txt
```

Start EMOTIV Launcher/App first and connect the EPOC+.

Then set your Cortex app credentials in PowerShell:

```powershell
$env:EMOTIV_CLIENT_ID="your_client_id"
$env:EMOTIV_CLIENT_SECRET="your_client_secret"
$env:LAB_PARTICIPANT_ID="LAB_001"
$env:LAB_VISIT_ID="VISIT_001"
```

Run the bridge:

```powershell
py services\emotiv_lsl_bridge\emotiv_cortex_lsl.py
```

Expected output includes:

```text
Publishing LSL stream: Emotiv_EPOCPlus_LAB_001_VISIT_001
Streaming EEG to LSL. Press Ctrl+C to stop.
```

Before running participants, confirm the EEG stream appears in LabRecorder.

If the script fails during `subscribe` with an authorization or stream error, the current Emotiv account/license does not expose raw EEG through Cortex. In that case, the recording cannot include raw EPOC+ EEG unless a suitable Emotiv license or another supported acquisition route is available.

## 5. Start Tobii Pro Fusion As An LSL Stream

Start the Tobii Pro Fusion software/driver first and confirm the eye tracker is connected and calibrated.

Then start a Tobii-to-LSL outlet. Depending on the installed Tobii software, this can be:

- a Tobii Pro SDK based Python bridge,
- an existing Tobii LSL outlet utility,
- or a lab-provided Tobii integration.

The goal is that LabRecorder sees a gaze stream, commonly with type `Gaze` or `EyeTracking`.

Before running participants, confirm gaze samples appear in LabRecorder.

## 6. Start LabRecorder

Open LabRecorder and click **Update**.

Select all relevant streams:

```text
reVISit Markers
Emotiv EEG stream
Tobii gaze stream
```

Set the output filename, for example:

```text
LAB_001.xdf
```

Start recording before the participant begins the study.

## 7. Dry Run Checklist

Do this before the first real participant:

1. Start Docker website/API.
2. Start the native reVISit marker bridge.
3. Start Emotiv-to-LSL.
4. Start Tobii-to-LSL.
5. Open LabRecorder and select all streams.
6. Start recording.
7. Open `http://localhost:8080/HAIC_study/?Lab_participant_ID=LAB_TEST`.
8. Click through two or three study pages.
9. Stop recording.
10. Verify the `.xdf` contains all streams.

The `reVISit Markers` stream should include events such as:

```text
trial_start
trial_end
iframe_pageLoaded
iframe_guessSubmitted
```

## 8. Analysis Route

If using local browser storage, the analysis page must be opened from the same origin as the study:

```text
http://localhost:8080/analysis/stats/HAIC_study/summary
```

If data were collected via another host, such as an IP address or VM domain, browser localStorage will be separate.

## 9. Optional Docker LSL Bridge

The Dockerized LSL bridge exists but is not recommended for Windows acquisition sessions:

```powershell
docker compose --profile lsl-docker up --build -d lsl-bridge
```

Use this only for development. For real recordings, prefer the native Python bridge.

## 10. Stop Services

Stop Docker services:

```powershell
docker compose down
```

Stop native bridges with `Ctrl+C` in their terminals.
