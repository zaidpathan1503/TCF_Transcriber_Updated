"""
TCF Transcriber Updated (PyTorch-Free Edition)
Author: Zaid
Version: 2.0.0

High-performance, lightweight batch audio transcription & translation desktop app.
Powered by faster-whisper (CTranslate2) with zero PyTorch dependency.
Up to 4x faster execution and drastically smaller footprint.
"""

__author__ = "Zaid"
__version__ = "2.0.0"

import os
import sys
import json
import queue
import threading
import time
from pathlib import Path
import re
import subprocess

import numpy as np
import pandas as pd
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from tkinter import filedialog, messagebox

# Optional dotenv support
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import ctranslate2
from faster_whisper import WhisperModel
from openai import OpenAI

def load_audio_file(file_path: str, sr: int = 16000) -> np.ndarray:
    """
    Robust audio loader using FFmpeg directly via subprocess.
    Avoids PyAV 'metadata_errors' compatibility bug on newer av releases.
    """
    cmd = [
        "ffmpeg",
        "-nostdin",
        "-threads", "0",
        "-i", str(file_path),
        "-f", "s16le",
        "-ac", "1",
        "-acodec", "pcm_s16le",
        "-ar", str(sr),
        "-"
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, check=True)
        return np.frombuffer(proc.stdout, np.int16).flatten().astype(np.float32) / 32768.0
    except Exception as e:
        try:
            from faster_whisper.audio import decode_audio
            return decode_audio(str(file_path), sampling_rate=sr)
        except Exception:
            raise RuntimeError(f"Failed to load audio with FFmpeg: {e}")

# ---------------------------
# Constants & Defaults
# ---------------------------
CONFIG_FILE = Path(__file__).parent / "config.json"
AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".mp4", ".webm", ".mpeg", ".mpga", ".aac", ".flac", ".ogg"}
DEFAULT_PROMPT = "Écoutez le document sonore et la question. Choisissez la bonne réponse. Merci."

DEFAULT_CONFIG = {
    "whisper_model": "small",
    "language": "fr",
    "compute_type": "int8",
    "device": "auto",
    "openai_model": "gpt-4o",
    "api_key": "",
    "save_csv": True,
    "recursive": False,
    "do_correction": False,
    "do_translation": False,
    "theme": "flatly",
    "initial_prompt": DEFAULT_PROMPT,
    "audio_pad_seconds": 3.0,
    "last_input_dir": "",
    "last_output_dir": "",
    "output_base": "tcf_transcripts"
}

def load_user_config() -> dict:
    config = DEFAULT_CONFIG.copy()
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                config.update(saved)
        except Exception:
            pass
    if not config.get("api_key"):
        config["api_key"] = os.getenv("OPENAI_API_KEY", "")
    return config

def save_user_config(config: dict):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Warning: could not save config: {e}")

def natural_sort_key(path: Path):
    return [
        int(text) if text.isdigit() else text.lower()
        for text in re.split(r"(\d+)", path.name)
    ]

def list_audio_files(folder: Path, recursive: bool) -> list[Path]:
    if not folder.exists() or not folder.is_dir():
        return []
    if recursive:
        files = [p for p in folder.rglob("*") if p.is_file() and p.suffix.lower() in AUDIO_EXTS]
    else:
        files = [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in AUDIO_EXTS]
    return sorted(files, key=natural_sort_key)

def next_incremented_excel(output_dir: Path, base_name: str) -> Path:
    base = (base_name or "tcf_transcripts").strip()
    n = 1
    while True:
        candidate = output_dir / f"{base}_{n}.xlsx"
        if not candidate.exists():
            return candidate
        n += 1

def check_ffmpeg() -> bool:
    try:
        res = subprocess.run(["ffmpeg", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return res.returncode == 0
    except FileNotFoundError:
        return False

# ---------------------------
# OpenAI Helpers

# [WIP: Transcription engine integration]
