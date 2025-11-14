@echo off
REM CodeBox - Global CLI Wrapper for Windows
REM This script allows you to run codebox from anywhere

REM Get the directory where this script is located
set SCRIPT_DIR=%~dp0

REM Run codebox.py with Python, passing all arguments
python "%SCRIPT_DIR%codebox.py" %*
