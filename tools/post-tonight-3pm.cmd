@echo off
REM Nudges the Tonight on Discord workflow at 3pm Bradenton time, from this PC.
REM GitHub's own scheduler only executes a handful of the runs it is asked for, and
REM never at a predictable minute, so a Windows scheduled task does the timing instead.
REM No secrets live here: it uses the GitHub CLI login already on this machine, and the
REM Discord webhook stays a GitHub secret. The workflow still applies its own rules, so
REM nothing is posted twice and nothing is posted on a night with nothing on.
set GH="%LOCALAPPDATA%\Microsoft\WinGet\Packages\GitHub.cli_Microsoft.Winget.Source_8wekyb3d8bbwe\bin\gh.exe"
%GH% workflow run tonight.yml --repo Ruptzy/kava-club -f mode=auto
