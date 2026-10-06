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
# ---------------------------
def get_openai_client(api_key: str) -> OpenAI:
    key = api_key.strip() or os.getenv("OPENAI_API_KEY", "").strip()
    if not key:
        raise ValueError("OpenAI API key is missing. Please provide it in the Settings tab.")
    return OpenAI(api_key=key)

def semantic_correct_fr(text_fr: str, client: OpenAI, model_name: str = "gpt-4o") -> str:
    if not text_fr.strip():
        return ""
    resp = client.chat.completions.create(
        model=model_name,
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an expert French transcription editor.\n"
                    "Hard rules:\n"
                    "- Fix homophones / similar-sounding word mistakes.\n"
                    "- NEVER delete or summarize information. Keep all sentences exactly as they are.\n"
                    "- Do NOT rewrite style, do NOT simplify.\n"
                    "- Preserve numbers, dates, names exactly as in the original."
                )
            },
            {"role": "user", "content": f"Correct this French transcript:\n\n{text_fr}"}
        ]
    )
    return resp.choices[0].message.content.strip()

def translate_fr_to_en(text_fr: str, client: OpenAI, model_name: str = "gpt-4o") -> str:
    if not text_fr.strip():
        return ""
    resp = client.chat.completions.create(
        model=model_name,
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": "Translate the French text into English. Preserve meaning entirely. Do not omit any details or sentences."
            },
            {"role": "user", "content": text_fr}
        ]
    )
    return resp.choices[0].message.content.strip()

# ---------------------------
# Main GUI Application
# ---------------------------
class TranscriberAppUpdated:
    def __init__(self, root: ttk.Window):
        self.root = root
        self.root.title("TCF Transcriber Updated (Lightweight & PyTorch-Free)")
        self.root.geometry("1080x730")
        self.root.minsize(920, 600)

        # Set application icon
        icon_path = Path(__file__).parent / "app_icon.ico"
        if icon_path.exists():
            try:
                self.root.iconbitmap(str(icon_path))
            except Exception:
                pass

        self.cfg = load_user_config()
        self.stop_requested = False
        self.worker = None
        self.msg_queue = queue.Queue()

        # Check CUDA availability via CTranslate2
        self.cuda_available = ctranslate2.get_cuda_device_count() > 0

        # Variables
        self.input_dir = ttk.StringVar(value=self.cfg.get("last_input_dir", ""))
        self.output_dir = ttk.StringVar(value=self.cfg.get("last_output_dir", ""))
        self.output_base = ttk.StringVar(value=self.cfg.get("output_base", "tcf_transcripts"))
        self.recursive = ttk.BooleanVar(value=self.cfg.get("recursive", False))

        self.whisper_model = ttk.StringVar(value=self.cfg.get("whisper_model", "small"))
        self.language_hint = ttk.StringVar(value=self.cfg.get("language", "fr"))
        self.device_var = ttk.StringVar(value=self.cfg.get("device", "auto"))
        self.compute_type_var = ttk.StringVar(value=self.cfg.get("compute_type", "int8"))

        self.do_correction = ttk.BooleanVar(value=self.cfg.get("do_correction", False))
        self.do_translation = ttk.BooleanVar(value=self.cfg.get("do_translation", False))
        self.do_csv = ttk.BooleanVar(value=self.cfg.get("save_csv", True))

        self.api_key_var = ttk.StringVar(value=self.cfg.get("api_key", ""))
        self.openai_model_var = ttk.StringVar(value=self.cfg.get("openai_model", "gpt-4o"))
        self.initial_prompt_var = ttk.StringVar(value=self.cfg.get("initial_prompt", DEFAULT_PROMPT))
        self.audio_pad_var = ttk.DoubleVar(value=self.cfg.get("audio_pad_seconds", 3.0))

        self.status_text = ttk.StringVar(value="Ready (PyTorch-Free)")
        self.found_files_text = ttk.StringVar(value="0 audio files detected")

        self.last_saved_excel = None
        self.results_data = []

        self._build_ui()
        self._check_system()
        self._schedule_queue_processing()

        self.input_dir.trace_add("write", lambda *_: self.update_file_count())
        self.recursive.trace_add("write", lambda *_: self.update_file_count())
        self.update_file_count()

    def _build_ui(self):
        header = ttk.Frame(self.root, padding=(18, 12, 18, 8))
        header.pack(fill=X)

        title_box = ttk.Frame(header)
        title_box.pack(side=LEFT)
        ttk.Label(title_box, text="⚡ TCF Transcriber Updated", font=("Segoe UI", 17, "bold"), bootstyle="primary").pack(anchor=W)
        dev_info = "CUDA GPU Ready" if self.cuda_available else "High-Speed CPU Mode"
        ttk.Label(title_box, text=f"PyTorch-Free CTranslate2 Engine • 4x Inference Speed • {dev_info}", font=("Segoe UI", 9), bootstyle="secondary").pack(anchor=W)

        status_box = ttk.Frame(header)
        status_box.pack(side=RIGHT, fill=Y)
        self.status_badge = ttk.Label(status_box, textvariable=self.status_text, font=("Segoe UI", 10, "bold"), bootstyle="success-inverse", padding=(8, 4))
        self.status_badge.pack(side=RIGHT)

        ttk.Separator(self.root).pack(fill=X, padx=12, pady=(0, 6))

        notebook = ttk.Notebook(self.root, padding=8)
        notebook.pack(fill=BOTH, expand=True)

        self.tab_transcribe = ttk.Frame(notebook, padding=12)
        self.tab_results = ttk.Frame(notebook, padding=12)
        self.tab_settings = ttk.Frame(notebook, padding=12)

        notebook.add(self.tab_transcribe, text=" 📂 Batch Transcribe ")
        notebook.add(self.tab_results, text=" 📋 Live Results ")
        notebook.add(self.tab_settings, text=" ⚙️ Settings & Performance ")

        self._build_transcribe_tab()
        self._build_results_tab()
        self._build_settings_tab()

    def _build_transcribe_tab(self):
        f = self.tab_transcribe

        paths_card = ttk.Labelframe(f, text="Folders & Output", padding=12, bootstyle="primary")
        paths_card.pack(fill=X, pady=(0, 10))
        paths_card.grid_columnconfigure(1, weight=1)

        ttk.Label(paths_card, text="Input Folder:", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky=W, pady=4)
        ttk.Entry(paths_card, textvariable=self.input_dir).grid(row=0, column=1, sticky=EW, padx=8, pady=4)
        btn_in = ttk.Button(paths_card, text="Browse...", command=self.browse_input, bootstyle="secondary-outline", width=10)
        btn_in.grid(row=0, column=2, padx=4, pady=4)

        ttk.Label(paths_card, text="Output Folder:", font=("Segoe UI", 9, "bold")).grid(row=1, column=0, sticky=W, pady=4)
        ttk.Entry(paths_card, textvariable=self.output_dir).grid(row=1, column=1, sticky=EW, padx=8, pady=4)
        btn_out = ttk.Button(paths_card, text="Browse...", command=self.browse_output, bootstyle="secondary-outline", width=10)
        btn_out.grid(row=1, column=2, padx=4, pady=4)

        sub_row = ttk.Frame(paths_card)
        sub_row.grid(row=2, column=0, columnspan=3, sticky=EW, pady=(6, 0))
        
        ttk.Label(sub_row, text="File Prefix:").pack(side=LEFT)
        ttk.Entry(sub_row, textvariable=self.output_base, width=20).pack(side=LEFT, padx=(6, 16))

        ttk.Checkbutton(sub_row, text="Include subfolders recursively", variable=self.recursive, bootstyle="round-toggle").pack(side=LEFT)

        self.lbl_count = ttk.Label(sub_row, textvariable=self.found_files_text, font=("Segoe UI", 9, "italic"), bootstyle="success")
        self.lbl_count.pack(side=RIGHT)

        opts_card = ttk.Labelframe(f, text="Faster-Whisper & Precision Controls", padding=12, bootstyle="info")
        opts_card.pack(fill=X, pady=(0, 10))
        for i in range(6):
            opts_card.grid_columnconfigure(i, weight=1)

        ttk.Label(opts_card, text="Model Size:").grid(row=0, column=0, sticky=W, pady=2)
        model_cb = ttk.Combobox(opts_card, textvariable=self.whisper_model, values=["tiny", "base", "small", "medium", "large-v2", "large-v3", "distil-large-v3"], state="readonly", width=12)
        model_cb.grid(row=0, column=1, sticky=W, padx=4, pady=2)

        ttk.Label(opts_card, text="Language:").grid(row=0, column=2, sticky=W, pady=2)
        lang_cb = ttk.Combobox(opts_card, textvariable=self.language_hint, values=["fr", "en", "auto", "es", "de", "it", "ar"], state="readonly", width=10)
        lang_cb.grid(row=0, column=3, sticky=W, padx=4, pady=2)

        ttk.Label(opts_card, text="Quantization:").grid(row=0, column=4, sticky=W, pady=2)
        quant_cb = ttk.Combobox(opts_card, textvariable=self.compute_type_var, values=["int8", "float16", "int8_float16", "float32"], state="readonly", width=12)
        quant_cb.grid(row=0, column=5, sticky=W, padx=4, pady=2)

        sep2 = ttk.Separator(opts_card)
        sep2.grid(row=1, column=0, columnspan=6, sticky=EW, pady=8)

        ttk.Checkbutton(opts_card, text="Semantic correction (OpenAI GPT-4o)", variable=self.do_correction, bootstyle="success-round-toggle").grid(row=2, column=0, columnspan=2, sticky=W)
        ttk.Checkbutton(opts_card, text="Translate to English (OpenAI GPT-4o)", variable=self.do_translation, bootstyle="info-round-toggle").grid(row=2, column=2, columnspan=2, sticky=W)
        ttk.Checkbutton(opts_card, text="Also export CSV (.csv)", variable=self.do_csv, bootstyle="secondary-round-toggle").grid(row=2, column=4, columnspan=2, sticky=W)

        ctrl_card = ttk.Frame(f, padding=(0, 4))
        ctrl_card.pack(fill=X, pady=(0, 8))

        self.start_btn = ttk.Button(ctrl_card, text="▶ Start Batch", command=self.start, bootstyle="success", width=14)
        self.start_btn.pack(side=LEFT, padx=(0, 6))

        self.stop_btn = ttk.Button(ctrl_card, text="⏹ Stop Batch", command=self.stop, bootstyle="danger", state=DISABLED, width=14)
        self.stop_btn.pack(side=LEFT, padx=6)

        self.open_out_btn = ttk.Button(ctrl_card, text="📁 Open Output", command=self.open_output_dir, bootstyle="secondary-outline")
        self.open_out_btn.pack(side=LEFT, padx=6)

        self.progress_lbl = ttk.Label(ctrl_card, text="0%", font=("Segoe UI", 9, "bold"))
        self.progress_lbl.pack(side=RIGHT, padx=(8, 0))

        self.progress = ttk.Progressbar(ctrl_card, length=320, mode="determinate", bootstyle="success-striped")
        self.progress.pack(side=RIGHT, padx=4)

        log_frame = ttk.Labelframe(f, text="Activity Log", padding=8, bootstyle="secondary")
        log_frame.pack(fill=BOTH, expand=True)

        log_tools = ttk.Frame(log_frame)
        log_tools.pack(fill=X, pady=(0, 4))
        ttk.Label(log_tools, text="Real-time execution log:", font=("Segoe UI", 8), bootstyle="secondary").pack(side=LEFT)
        ttk.Button(log_tools, text="Clear Log", command=self.clear_log, bootstyle="link", padding=0).pack(side=RIGHT)

        self.log = ttk.Text(log_frame, height=9, wrap="word", font=("Consolas", 9))
        scroll = ttk.Scrollbar(log_frame, orient=VERTICAL, command=self.log.yview)
        self.log.configure(yscrollcommand=scroll.set, state="disabled")
        scroll.pack(side=RIGHT, fill=Y)
        self.log.pack(side=LEFT, fill=BOTH, expand=True)

    def _build_results_tab(self):
        f = self.tab_results

        top_actions = ttk.Frame(f)
        top_actions.pack(fill=X, pady=(0, 6))

        ttk.Label(top_actions, text="Transcribed Items:", font=("Segoe UI", 11, "bold")).pack(side=LEFT)
        ttk.Button(top_actions, text="Copy Selected Text", command=self.copy_selected_text, bootstyle="secondary-outline").pack(side=RIGHT, padx=4)
        ttk.Button(top_actions, text="Export to Excel Now", command=self.manual_export_excel, bootstyle="success-outline").pack(side=RIGHT, padx=4)

        cols = ("filename", "text", "corrected_text", "translation_en")
        self.tree = ttk.Treeview(f, columns=cols, show="headings", selectmode="browse", height=10)
        self.tree.heading("filename", text="Filename")
        self.tree.heading("text", text="Faster-Whisper Raw Text")
        self.tree.heading("corrected_text", text="Semantic Corrected (FR)")
        self.tree.heading("translation_en", text="Translation (EN)")

        self.tree.column("filename", width=120, anchor=W)
        self.tree.column("text", width=340, anchor=W)
        self.tree.column("corrected_text", width=300, anchor=W)
        self.tree.column("translation_en", width=260, anchor=W)

        tree_scroll = ttk.Scrollbar(f, orient=VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scroll.set)
        tree_scroll.pack(side=RIGHT, fill=Y)
        self.tree.pack(fill=BOTH, expand=True, pady=(0, 6))

        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)

        inspect_frame = ttk.Labelframe(f, text="Selected Item Detail", padding=8, bootstyle="info")
        inspect_frame.pack(fill=X, pady=(4, 0))

        self.inspect_text = ttk.Text(inspect_frame, height=5, wrap="word", font=("Segoe UI", 9))
        self.inspect_text.pack(fill=BOTH, expand=True)
        self.inspect_text.configure(state="disabled")

    def _build_settings_tab(self):
        f = self.tab_settings

        api_card = ttk.Labelframe(f, text="OpenAI API Configuration (for Optional Refinement)", padding=12, bootstyle="primary")
        api_card.pack(fill=X, pady=(0, 10))
        api_card.grid_columnconfigure(1, weight=1)

        ttk.Label(api_card, text="API Key:").grid(row=0, column=0, sticky=W, pady=6)
        
        key_box = ttk.Frame(api_card)
        key_box.grid(row=0, column=1, sticky=EW, padx=8, pady=6)
        key_box.grid_columnconfigure(0, weight=1)

        self.api_entry = ttk.Entry(key_box, textvariable=self.api_key_var, show="*")
        self.api_entry.grid(row=0, column=0, sticky=EW)

        self.show_key_var = ttk.BooleanVar(value=False)
        def toggle_key_show():
            self.api_entry.configure(show="" if self.show_key_var.get() else "*")

        ttk.Checkbutton(key_box, text="Show", variable=self.show_key_var, command=toggle_key_show).grid(row=0, column=1, padx=(6, 0))

        ttk.Button(api_card, text="Save Key", command=self.save_api_key_action, bootstyle="success-outline").grid(row=0, column=2, padx=4)

        ttk.Label(api_card, text="Model:").grid(row=1, column=0, sticky=W, pady=6)
        openai_models = ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "o3-mini"]
        model_menu = ttk.Combobox(api_card, textvariable=self.openai_model_var, values=openai_models, state="readonly", width=18)

# [WIP: Thread-safe queue]
