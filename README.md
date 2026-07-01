# NOVA — Desktop Voice Assistant

A real Windows desktop voice assistant built for an HCI semester project. NOVA understands
typed and spoken commands and performs actual desktop actions — opening apps, checking
system stats, managing files and notes — while demonstrating core Human-Computer
Interaction principles throughout the interface.

## Overview

NOVA is a PySide6 desktop application backed by a LangGraph workflow. Every command —
whether typed or spoken — flows through the same pipeline: parse the intent, check if it
needs confirmation, execute the real action, generate a response, speak it aloud, and save
it to history. The UI never freezes because voice recording, transcription, and command
execution all run on background threads.

## Features

- Type or speak commands — understood by a real local LLM (Llama 3.2 3B via Ollama),
  not rigid pattern matching, so phrasing, casing, and typos don't break it
- Genuine conversation — greet NOVA, ask how it's doing, and it replies naturally
  instead of "command not understood"
- Offline speech-to-text using Faster-Whisper (no internet, no API key)
- Text-to-speech responses with a working Stop button
- Real desktop actions: open Notepad, Calculator, File Explorer, browser searches
- Live system stats: CPU, RAM, battery, time — refreshed every second
- Real screenshots saved to disk
- File and folder management sandboxed to a safe workspace folder
- Notes saved in SQLite, with create/show/delete
- Confirmation dialog before any delete action — asked only once the LLM has
  actually understood you mean to delete something, not on a keyword match
- Full command history saved and shown in a side panel
- Non-blocking UI — recording, transcription, and LLM classification never freeze the window

## Technologies

| Layer | Technology |
|---|---|
| GUI | PySide6 |
| Workflow | LangGraph (StateGraph) |
| Language understanding | OpenAI (gpt-4o-mini) if configured, otherwise local Llama 3.2 3B via Ollama |
| Speech-to-text | Faster-Whisper (offline) |
| Text-to-speech | pyttsx3 |
| Audio recording | sounddevice |
| System info | psutil |
| Screenshots | Pillow (ImageGrab) |
| Database | SQLite |
| Testing | pytest |

## Choosing a language model — OpenAI or local Ollama

NOVA supports two ways to understand your commands. It automatically uses
whichever one is configured, checking OpenAI first.

### Option A — OpenAI (smarter, needs internet, tiny per-command cost)

1. Copy `.env.example` to `.env`
2. Add your OpenAI key:
   ```
   OPENAI_API_KEY=sk-...your-key-here...
   ```
3. That's it — NOVA detects the key automatically on launch.

Never commit your real `.env` file or share your key — it's already excluded
in `.gitignore`.

### Option B — Ollama (free forever, fully offline)

1. Download and install Ollama from [ollama.com](https://ollama.com)
2. Pull the model:
   ```bash
   ollama pull llama3.2:3b
   ```
3. Make sure Ollama is running (`ollama serve`, or it auto-starts on Windows)
4. Leave `OPENAI_API_KEY` blank in `.env` — NOVA will use Ollama automatically

NOVA tells you on launch which one it's using, or warns you if neither is
reachable.

## HCI Principles Demonstrated

**Visibility of system status** — the status badge always shows Idle, Listening,
Transcribing, Thinking, Executing, Speaking, Completed, or Error, so the user always knows
what NOVA is doing.

**Immediate feedback** — every command produces a visible chat response and a spoken
response within a second or two of completion.

**User control and freedom** — Stop Speaking interrupts NOVA mid-sentence; Clear resets
the conversation at any time.

**Error prevention and recovery** — delete actions always require explicit Yes/No
confirmation before anything is removed.

**Voice and text accessibility** — every feature works identically whether typed or
spoken, giving users a choice of interaction mode.

**Consistency** — the same color-coded response pattern (NOVA in purple, You in teal)
and the same pipeline runs for every command type.

**Clear success and error messaging** — responses explicitly state what happened
("Folder created", "File not found") rather than silent failures.

## Project Structure

```
nova-assistant/
├── main.py                      entry point
├── requirements.txt
├── ui/
│   ├── main_window.py           the full PySide6 interface
│   └── styles.py                dark blue/purple theme
├── graph/
│   ├── state.py                 LangGraph state definition
│   └── workflow.py               receive → parse → confirm → execute → respond → save
├── tools/
│   ├── application_tools.py     notepad, calculator, explorer
│   ├── browser_tools.py         google/youtube search
│   ├── system_tools.py          cpu, ram, battery, screenshot
│   ├── file_tools.py            create/read/list/delete files
│   └── note_tools.py            notes backed by SQLite
├── voice/
│   ├── recorder.py              microphone capture
│   ├── speech_to_text.py        Faster-Whisper wrapper
│   └── text_to_speech.py        pyttsx3 wrapper with stop support
├── database/
│   └── database.py              SQLite schema + queries
├── utils/
│   ├── command_parser.py        rule-based intent matching
│   └── workers.py               QThread workers for non-blocking execution
└── tests/
    ├── test_parser.py
    ├── test_database.py
    └── test_tools.py
```

## Setup Instructions

Requires Python 3.11+ on Windows.

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

The first time you use a voice command, Faster-Whisper will download its model
(~150MB for the "base" model). This needs an internet connection once; after that,
everything runs fully offline.

## How to Run

```bash
python main.py
```

The NOVA window opens. Type a command and press Send, or click the microphone button,
speak, then click it again to stop and transcribe.

## Supported Commands

**Applications**
`open notepad` · `open calculator` · `open file explorer` · `open browser`

**Search**
`search google for <query>` · `search youtube for <query>`

**System info**
`show cpu usage` · `show ram usage` · `show battery` · `what time is it` · `take screenshot`

**Files** (sandboxed to the `workspace/` folder)
`create folder <name>` · `create file <name>` · `read file <name>` · `list files` ·
`delete file <name>` *(asks for confirmation)*

**Notes**
`create note saying <content>` · `show my notes` · `delete note` *(asks for confirmation)*

**Assistant controls**
`stop speaking` · `clear chat`

## Testing Guide

Run the automated test suite:

```bash
pytest tests/ -v
```

This covers the command parser (intent matching, argument extraction, confirmation
flags), the database layer (notes, history, settings), and the file tools (safe
filenames, create/read/delete).

### Manual testing checklist

- [ ] App launches without errors
- [ ] Typing "open notepad" actually opens Notepad
- [ ] Typing "open calculator" actually opens Calculator
- [ ] Microphone records and the status changes to Listening
- [ ] Clicking the mic again stops recording and shows Transcribing
- [ ] Transcribed text appears in the input box and executes automatically
- [ ] "show cpu usage" reports a real percentage matching Task Manager
- [ ] "show ram usage" reports a real percentage matching Task Manager
- [ ] "take screenshot" creates a real PNG file in the `screenshots/` folder
- [ ] "create folder HCI Project" creates a real folder in `workspace/`
- [ ] "create note saying presentation is on Monday" saves and "show my notes" displays it
- [ ] "delete file <name>" shows a Yes/No dialog before deleting
- [ ] Clicking No on the confirmation dialog cancels the deletion
- [ ] NOVA speaks every response aloud
- [ ] "stop speaking" interrupts NOVA mid-sentence
- [ ] Side panel CPU/RAM/Battery/Time values update every second
- [ ] Recent commands list updates after each command
- [ ] UI stays responsive (not frozen) during recording and transcription
- [ ] "clear chat" empties the conversation area

## Known Limitations

- Faster-Whisper's "base" model favors speed over accuracy — background noise can
  affect transcription quality
- File operations are intentionally sandboxed to the `workspace/` folder for safety;
  NOVA cannot delete files anywhere else on the system
- pyttsx3 voice quality depends on the voices installed on the Windows machine
- Command understanding is rule-based pattern matching, not free-form natural language —
  commands need to roughly match the supported phrasings

## Future Improvements

- Add wake-word detection ("Hey NOVA") for hands-free activation
- Support multi-step commands and follow-up questions
- Add a settings panel to choose TTS voice and Whisper model size
- Expand the file tools to support more file types (PDF, images)
- Add light mode as a theme option
