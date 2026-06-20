# Vision Integration

This project now routes `recognize_face` and `recognize_emotion` through the shared `vision` backend in the sibling project `Assistive-Vision-System`.

## What Changed

- `recognize_face` now uses the real face pipeline from `Assistive-Vision-System`
- `recognize_emotion` now uses the real emotion pipeline from `Assistive-Vision-System`
- both capabilities share one adapter/controller boundary in `controllers/vision_controller.py`
- the old mock execution path for face/emotion is no longer the default runtime backend

## Default Project Path

The runtime looks for the vision project at:

```text
D:\EGB_FUNCTIONS\Assistive-Vision-System
```

You can override it with:

```powershell
$env:EGB_VISION_PROJECT_PATH="D:\path\to\Assistive-Vision-System"
```

## Required Runtime Dependencies

Install the core vision packages into the same `venv` used by `voice_assistant`:

```powershell
venv\Scripts\python.exe -m pip install opencv-python numpy scikit-image tensorflow deepface mtcnn tf-keras
```

If you only want the minimum path first, start with:

```powershell
venv\Scripts\python.exe -m pip install opencv-python numpy scikit-image tensorflow
```

Notes:

- `deepface` improves face identification quality, but the adapter can still initialize a lighter fallback embedding path without it.
- `mtcnn` improves face detection for emotion analysis, but the emotion pipeline can fall back to Haar cascade detection if `mtcnn` is missing.

## Runtime Inputs

Optional overrides:

```powershell
$env:EGB_VISION_CAMERA_INDEX="1"
$env:EGB_VISION_FRAME_WARMUP="3"
```

The underlying vision project still honors its own environment variables such as:

```powershell
$env:AVS_MODEL_PATH="D:\EGB_FUNCTIONS\Assistive-Vision-System\model\emotion_fixed.h5"
```

## Behavior

- if the vision backend is available, face/emotion commands use the real camera/model path
- if the camera, model, or dependencies are unavailable, the assistant returns a safe structured failure instead of fake recognition data
- follow-up emotion recognition is only armed after a successful identified face result

## Quick Validation

```powershell
venv\Scripts\python.exe -m pytest tests\unit\test_vision_controller.py tests\unit\test_capability_registry.py tests\unit\test_resolver.py
venv\Scripts\python.exe main.py
```
