# Azure Speech TTS Setup

This project can use Azure Speech TTS as the preferred cloud synthesis backend,
with automatic fallback to `edge_tts` when Azure is unavailable or not
configured.

## Environment Variables

Set these in your shell or `.env` loader before starting the app:

```powershell
$env:EGB_TTS_AZURE_ENABLED="1"
$env:EGB_TTS_AZURE_KEY="<your-speech-key>"
$env:EGB_TTS_AZURE_REGION="<your-speech-region>"
```

Optional:

```powershell
$env:EGB_TTS_AZURE_ENDPOINT="https://<your-custom-endpoint>.cognitiveservices.azure.com/"
```

Notes:

- Use either `EGB_TTS_AZURE_KEY + EGB_TTS_AZURE_REGION`, or
  `EGB_TTS_AZURE_KEY + EGB_TTS_AZURE_ENDPOINT`.
- Azure uses the same neural voice IDs already used by the project, such as
  `ar-EG-SalmaNeural`, `ar-EG-ShakirNeural`, and
  `en-US-AndrewMultilingualNeural`.
- If Azure synthesis fails at runtime, the engine falls back to `edge_tts`,
  and if that fails after cloud-first selection it still attempts local SAPI as
  a best-effort recovery on Windows.

## Recommended Arabic Voice

For a more natural Arabic voice, prefer:

- `ar-EG-SalmaNeural`

Current defaults remain managed by `settings/settings_manager.py`.

## Dependency

Install the SDK in the active virtual environment:

```powershell
venv\Scripts\python.exe -m pip install azure-cognitiveservices-speech
```

## Quick Verify

Run the app after exporting the environment variables:

```powershell
venv\Scripts\python.exe main.py
```

When Azure is active, the console logs should include:

```text
[TTS] Backend selected=azure_speech ...
```
