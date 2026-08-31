# Auto Translator Manager

Auto Translator Manager is an offline game translation tool. It allows users to translate visual novels and RPGs from their original language into a target language using local translation engines and translation memory.

## Supported Engines

The application currently supports automatic translation for games built on the following engines:
- RenPy
- Unity (Mono and IL2CPP)
- RPG Maker

## Current Limitations

- Bakin Engine is NOT currently supported.
- The system heavily relies on SQLite for caching and translation memory, which has been optimized for performance through hard-delete operations.
- Translating Unity games requires the application to inject BepInEx payloads dynamically.

## Architecture Overview

The software is structured with a Python backend managing translation pipelines, thread pools, and SQLite databases. The frontend is built using HTML, CSS, and Vanilla JavaScript with a responsive Dark/Light mode UI.

- Backend: Python 3, FastAPI / WSGI Server, SQLite.
- Frontend: Vanilla JS, CSS Variables, Modular JavaScript features.

## Installation and Usage

1. Run the application using the provided executable or by running the start script.
2. Ensure you do not close the terminal window while the application UI is running in your web browser.
3. Add a game by selecting its executable file. The engine will be automatically detected.
4. Click Start to begin the translation extraction and processing pipeline.
