# ⚡ TCF Transcriber Updated (PyTorch-Free Edition)

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Engine: faster--whisper](https://img.shields.io/badge/Engine-faster--whisper_(CTranslate2)-red.svg)](https://github.com/SYSTRAN/faster-whisper)
[![PyTorch: Not Required](https://img.shields.io/badge/PyTorch-Dropped_(0MB)-brightgreen.svg)](#architecture)
[![Author: Zaid](https://img.shields.io/badge/Author-Zaid-purple.svg)](#author)

An ultra-optimized, lightweight edition of **TCF Transcriber** that completely **eliminates the heavy PyTorch dependency**. Powered by `faster-whisper` and the `CTranslate2` high-efficiency inference engine.

---

## 🚀 Why This Updated Edition?

| Metric | Original (`openai-whisper`) | **TCF Transcriber Updated (`faster-whisper`)** |
|---|---|---|
| **PyTorch Dependency** | Required (~1.5 GB - 2.5 GB) | **Completely Removed (0 MB)** 🚫 |
| **Inference Speed** | 1x Baseline | **Up to 4x Faster** ⚡ |
| **RAM / VRAM Usage** | ~1.5 GB - 2.5 GB | **~500 MB (via INT8 Quantization)** 📉 |
| **Compiled `.exe` Size** | ~1.8 GB - 2.5 GB | **~150 MB - 250 MB** 📦 |
| **CPU Performance** | Moderate | **Highly optimized AVX-512 / AVX2 kernels** |
| **Transcription Accuracy** | High | **Identical accuracy (exact same weights)** |

---

## 💰 100% Free & Offline Transcription

* **Zero Cloud Costs:** Transcriptions are executed locally on CPU or CUDA GPU with zero cost and no subscription.
* **Optional Cloud Refinement:** OpenAI GPT-4o semantic refinement and English translation remain available as optional toggles for users who provide an API key in the app.

---

## ✨ Features

- ⚡ **PyTorch-Free CTranslate2 Backend:** Runs directly using pre-quantized C++ inference libraries.
- 🎛️ **Quantization Selector:** Choose between `int8` (fastest & minimal RAM for CPU), `float16`, `int8_float16`, or `float32`.
- 🎧 **Supported Whisper Models:** `tiny`, `base`, `small`, `medium`, `large-v2`, `large-v3`, and `distil-large-v3`.
- 📦 **Automated Batch Folder Processing:** Recursive search, natural sorting (`Q1, Q2, Q10`), and intermediate crash-proof autosaving (`__progress.xlsx` & `__progress.csv`).
- 🛡️ **End-of-Clip Silence Padding:** Automatically appends 3.0 seconds of audio silence to prevent sentence cutoff during pauses.
- 📋 **Live Interactive Results Table:** Inspect transcribed rows in real-time, copy text to clipboard, and export immediately.
- 🎨 **Modern ttkbootstrap GUI:** Equipped with high-resolution app icon and dark/light themes.

---

## 🛠️ System Requirements

1. **Python 3.10 to 3.13**
2. **FFmpeg** in PATH (Install on Windows: `winget install ffmpeg`)
3. *(Optional)* **OpenAI API Key** (only for cloud refinement/translation)

---

## 🚀 Quick Start

### 1. Windows One-Click Launcher
Double-click **`run.bat`**.

It automatically:
- Verifies Python and FFmpeg.
- Sets up an isolated virtual environment (`.venv`).
- Installs lightweight dependencies from `requirements.txt` (without downloading heavy PyTorch wheels!).
- Launches the application.

### 2. PowerShell
```powershell
.\run.ps1
```

### 3. Manual Run
```bash
cd TCF_Transcriber_Updated
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

---

## 📦 Compiling Portable Standalone Executable (`.exe`)

Run:
```cmd
build_exe.bat
```

Because `torch` is completely excluded (`--exclude-module torch`), PyInstaller produces a vastly more compact executable inside:
```
dist\TCF Transcriber Updated\TCF Transcriber Updated.exe
```

---

## 📄 Output Data Schema

Exported Excel (`.xlsx`) and CSV (`.csv`) files contain:

| Column | Description |
|---|---|
| `filename` | Name of the source audio file |
| `text` | Fast local transcript produced by Faster-Whisper |
| `corrected_text` | *(Optional)* Homophone-corrected French transcript via GPT-4o |
| `translation_en` | *(Optional)* English translation via GPT-4o |

---

## 📜 License

Released under the [MIT License](LICENSE).

---

## 👤 Author

Developed by **ACE**.

