# CDID Fishing Macro
mancing mania, mantap!<br/>
currently this only works on windows/linux, mac support is unlikely unless this turns into a real minigame

## Prerequisites
### Windows
1. have python in ur pc https://www.python.org/downloads/ (or download from windows store)
2. open terminal
3. install libraries:
   ```bash
   pip install pyautogui keyboard numpy pillow pywin32
### Linux
1. install system dependencies:
   ```bash
   sudo apt update
   sudo apt install wmctrl xdotool x11-utils python3-tk python3-pil.imagetk
2. (IMPORTANT!) create and activate venv (you can rename macro_env):
   ```bash
   python3 -m venv macro_env
   source macro_env/bin/activate
3. install python dependencies on venv:
   ```bash
   pip install pyautogui numpy pillow pynput python-xlib

## Installation
1. click any versions above depending on your OS
2. click 'Download raw file'
3. (FOR LINUX) edit the first line of the program, directing it to your venv's python

## Help
If macro feels too janky, edit aggressive_threshold value in line 185 (win)/177 (linux)

## Credits
- @cn3z on Discord: programming logic, GUI, and Linux support<br/>
- @.dar_. on Discord: dynamic scaling
   
## Contribution
this is currently a solo project, and it'll stay that way for a long time. unless, you can convince me otherwise. let me know in Discord (@cn3z). you can fork it if u want
