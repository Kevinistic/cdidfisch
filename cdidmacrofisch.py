import pyautogui
from tkinter import *
from tkinter import ttk
import threading
import time
import keyboard
import numpy as np
from PIL import Image
import win32gui
import win32api
import ctypes
import sys

# --- Utility Functions ---
BAR_X_RATIO = 0.30
BAR_Y_RATIO = 0.82
BAR_WIDTH_RATIO = 0.40
BAR_HEIGHT_RATIO = 0.06

def get_roblox_window():
    def enum_windows_callback(hwnd, windows):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if 'roblox' in title.lower():
                windows.append((hwnd, title))
    windows = []
    win32gui.EnumWindows(enum_windows_callback, windows)
    if windows:
        hwnd, title = windows[0]
        rect = win32gui.GetWindowRect(hwnd)
        return {
            'hwnd': hwnd,
            'title': title,
            'left': rect[0],
            'top': rect[1],
            'width': rect[2] - rect[0],
            'height': rect[3] - rect[1]
        }
    return None

def get_screen_info():
    screen_width = win32api.GetSystemMetrics(0)
    screen_height = win32api.GetSystemMetrics(1)
    try:
        user32 = ctypes.windll.user32
        user32.SetProcessDPIAware()
        dc = user32.GetDC(0)
        dpi_x = ctypes.windll.gdi32.GetDeviceCaps(dc, 88)
        user32.ReleaseDC(0, dc)
        scaling_factor = dpi_x / 96.0
    except:
        scaling_factor = 1.0
    return {'width': screen_width, 'height': screen_height, 'scaling': scaling_factor}

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
    avg_x = np.mean(red_indices[:, 1])
    return avg_x

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
    center_x = (min_x + max_x) / 2
    return center_x

# --- GUI and Bot Logic ---
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
        self.last_toggle = 0
        self.reel_ctr = 1

        self.status_label = Label(self, text="Status: OFF")
        self.status_label.pack(pady=5)
        self.region_label = Label(self, text="Region: Detecting...")
        self.region_label.pack(pady=5)

        self.button_container = Frame(self)
        self.button_container.pack()
        ttk.Button(self.button_container, text="Help", command=self.show_help).grid(row=0, column=0)
        ttk.Button(self.button_container, text="Credits", command=self.show_credit).grid(row=0, column=1)

        self.protocol("WM_DELETE_WINDOW", self.exit_program)

        self.region = self.setup_region()
        self.start_threads()

    def setup_region(self):
        roblox_window = get_roblox_window()
        if not roblox_window:
            print("⚠️ Roblox window not found, defaulting to full screen")
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
        threading.Thread(target=self.monitor_hotkeys, daemon=True).start()
        threading.Thread(target=self.bot_loop, daemon=True).start()

    def monitor_hotkeys(self):
        while True:
            try:
                if keyboard.is_pressed("F6"):
                    now = time.time()
                    if now - self.last_toggle > 0.3:
                        self.running = not self.running
                        self.last_toggle = now
                        self.title(f"Fishing Bot [{'ON' if self.running else 'OFF'}]")
                elif keyboard.is_pressed("F7"):
                    self.running = False
                    self.exit_program()
                    break
                elif keyboard.is_pressed("F8"):
                    now = time.time()
                    if now - self.last_toggle > 0.3:
                        self.region = self.setup_region()
                        self.last_toggle = now

            except:
                pass
            time.sleep(0.05)

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

                    screen_info = get_screen_info()
                    width = screen_info['width']
                    aggressive_threshold = width * BAR_X_RATIO * 0.03  # 3% as threshold, adjust as needed
                    if x_pos > (gray_center + aggressive_threshold):
                        self.status_label.config(text="Status: Battling (>>)")
                        if not self.mouse_held:
                            pyautogui.mouseDown()
                            self.mouse_held = True
                    else:
                        self.status_label.config(text="Status: Battling (<<)")
                        if self.mouse_held:
                            pyautogui.mouseUp()
                            self.mouse_held = False
                else:
                    self.status_label.config(text=f"Status: Reeling ({self.reel_ctr})")
                    if self.mouse_held:
                        pyautogui.mouseUp()
                        self.mouse_held = False
                    self.fisch_ctr += 1
                    if self.fisch_ctr > 10:
                        self.reel_ctr += 1
                        pyautogui.leftClick()
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
            "Press F6: Toggle ON/OFF\n"
            "Press F7: Emergency stop\n"
            "Press F8: Recalibrate fishing bar region\n"
        )

        label = Label(help_window, text=help_text, justify=LEFT, anchor="nw")
        label.pack(padx=15, pady=15, fill=BOTH, expand=True)

    def show_credit(self):
        credit_window = Toplevel(self)
        credit_window.title("Credits")
        credit_window.geometry("550x150")
        credit_window.resizable(False, False)

        credit_text = (
            "@cn3z on Discord: programming logic and GUI\n"
            "@.dar_. on Discord: dynamic scaling\n"
        )

        label = Label(credit_window, text=credit_text, justify=LEFT, anchor="nw")
        label.pack(padx=15, pady=15, fill=BOTH, expand=True)

    def exit_program(self):
        try:
            pyautogui.mouseUp()
        except:
            pass
        self.destroy()
        sys.exit()

if __name__ == "__main__":
    app = FishingBotApp()
    app.mainloop()
