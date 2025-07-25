#!/usr/bin/env python3

import pyautogui
from tkinter import *
from tkinter import ttk
import threading
import time
import subprocess
import numpy as np
from PIL import Image
from pynput import keyboard
from Xlib import display
import sys

# --- Constants ---
BAR_X_RATIO = 0.30
BAR_Y_RATIO = 0.82
BAR_WIDTH_RATIO = 0.40
BAR_HEIGHT_RATIO = 0.06

# --- Utility Functions ---
def get_roblox_window():
    try:
        result = subprocess.check_output(['wmctrl', '-l']).decode()
        for line in result.splitlines():
            if 'sober' in line.lower():
                parts = line.split()
                win_id = parts[0]
                x, y, width, height = 0, 0, 800, 600
                geom = subprocess.check_output(['xwininfo', '-id', win_id]).decode()
                for l in geom.splitlines():
                    if "Absolute upper-left X" in l:
                        x = int(l.split(":")[1])
                    elif "Absolute upper-left Y" in l:
                        y = int(l.split(":")[1])
                    elif "Width" in l:
                        width = int(l.split(":")[1])
                    elif "Height" in l:
                        height = int(l.split(":")[1])
                return {'hwnd': win_id, 'left': x, 'top': y, 'width': width, 'height': height}
    except Exception as e:
        print("⚠️ Roblox window not found:", e)
    return None

def get_screen_info():
    d = display.Display()
    screen = d.screen()
    return {'width': screen.width_in_pixels, 'height': screen.height_in_pixels, 'scaling': 1.0}

def calculate_expected_bar_position(window_info=None):
    if window_info:
        width = window_info['width']
        height = window_info['height']
        offset_x = window_info['left']
        offset_y = window_info['top']
    else:
        info = get_screen_info()
        width, height = info['width'], info['height']
        offset_x = offset_y = 0

    return {
        'expected_x': int(width * BAR_X_RATIO) + offset_x,
        'expected_y': int(height * BAR_Y_RATIO) + offset_y,
        'expected_width': int(width * BAR_WIDTH_RATIO),
        'expected_height': int(height * BAR_HEIGHT_RATIO)
    }

def find_red_bar_x(image):
    data = np.array(image)
    red_mask = (data[:, :, 0] > 200) & (data[:, :, 1] < 100) & (data[:, :, 2] < 100)
    red_indices = np.column_stack(np.where(red_mask))
    if len(red_indices) == 0:
        return None
    return np.mean(red_indices[:, 1])

def find_gray_area_center(image):
    data = np.array(image)
    gray_mask = (
        (data[:, :, 0] > 100) & (data[:, :, 0] < 180) &
        (np.abs(data[:, :, 0] - data[:, :, 1]) < 10) &
        (np.abs(data[:, :, 1] - data[:, :, 2]) < 10)
    )
    gray_indices = np.column_stack(np.where(gray_mask))
    if len(gray_indices) == 0:
        return None
    min_x = np.min(gray_indices[:, 1])
    max_x = np.max(gray_indices[:, 1])
    return (min_x + max_x) / 2

def mouse_down():
    subprocess.call(['xdotool', 'mousedown', '1'])

def mouse_up():
    subprocess.call(['xdotool', 'mouseup', '1'])

def left_click():
    subprocess.call(['xdotool', 'click', '1'])

# --- Main App Class ---
class FishingBotApp(Tk):
    def __init__(self):
        super().__init__()
        self.title("Fishing Bot [OFF]")
        self.geometry("550x150")
        self.resizable(False, False)
        self.attributes("-topmost", True)

        self.running = False
        self.mouse_held = False
        self.fisch_ctr = 0
        self.reel_ctr = 1

        self.status_label = Label(self, text="Status: OFF")
        self.status_label.pack(pady=5)
        self.region_label = Label(self, text="Region: Detecting...")
        self.region_label.pack(pady=5)

        self.button_container = Frame(self)
        self.button_container.pack()
        ttk.Button(self.button_container, text="Help", command=self.show_help).grid(row=0, column=0)

        self.protocol("WM_DELETE_WINDOW", self.exit_program)

        self.region = self.setup_region()
        self.start_threads()
        self.start_hotkey_listener()

    def setup_region(self):
        roblox_window = get_roblox_window()
        region_info = calculate_expected_bar_position(roblox_window)
        region = (
            region_info['expected_x'],
            region_info['expected_y'],
            region_info['expected_width'],
            region_info['expected_height']
        )
        self.region_label.config(text=f"Region: {region}")
        return region

    def start_threads(self):
        threading.Thread(target=self.bot_loop, daemon=True).start()

    def start_hotkey_listener(self):
        def on_press(key):
            try:
                if key == keyboard.Key.f6:
                    self.toggle_running()
                elif key == keyboard.Key.f7:
                    self.exit_program()
                elif key == keyboard.Key.f8:
                    self.region = self.setup_region()
            except:
                pass
        listener = keyboard.Listener(on_press=on_press)
        listener.daemon = True
        listener.start()

    def toggle_running(self):
        self.running = not self.running
        self.title(f"Fishing Bot [{'ON' if self.running else 'OFF'}]")

    def bot_loop(self):
        while True:
            if not self.running:
                self.status_label.config(text="Status: OFF")
                time.sleep(0.1)
                continue
            try:
                screenshot = pyautogui.screenshot(region=self.region)
                x_pos = find_red_bar_x(screenshot)
                gray_center = find_gray_area_center(screenshot)

                if x_pos is not None and gray_center is not None:
                    self.fisch_ctr = 0
                    self.reel_ctr = 1
                    aggressive_threshold = get_screen_info()['width'] * BAR_X_RATIO * 0.03
                    if x_pos > (gray_center + aggressive_threshold):
                        self.status_label.config(text="Status: Battling (>>)")
                        if not self.mouse_held:
                            mouse_down()
                            self.mouse_held = True
                    else:
                        self.status_label.config(text="Status: Battling (<<)")
                        if self.mouse_held:
                            mouse_up()
                            self.mouse_held = False
                else:
                    self.status_label.config(text=f"Status: Reeling ({self.reel_ctr})")
                    if self.mouse_held:
                        mouse_up()
                        self.mouse_held = False
                    self.fisch_ctr += 1
                    if self.fisch_ctr > 10:
                        self.reel_ctr += 1
                        left_click()
                        self.fisch_ctr = 0

                time.sleep(0.01)
            except Exception as e:
                print("❌ Bot Error:", e)

    def show_help(self):
        help_window = Toplevel(self)
        help_window.title("Help")
        help_window.geometry("500x150")
        help_window.resizable(False, False)

        help_text = (
            "F6 = Toggle ON/OFF\n"
            "F7 = Emergency Stop\n"
            "F8 = Recalibrate Region"
        )
        Label(help_window, text=help_text, justify=LEFT).pack(padx=15, pady=15, fill=BOTH, expand=True)

    def exit_program(self):
        try:
            mouse_up()
        except:
            pass
        self.destroy()
        sys.exit()

# --- Run ---
if __name__ == "__main__":
    app = FishingBotApp()
    app.mainloop()
