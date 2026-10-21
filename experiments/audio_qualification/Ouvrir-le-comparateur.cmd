@echo off
cd /d "%~dp0..\.."
".venv\Scripts\pythonw.exe" -m experiments.audio_qualification.app
