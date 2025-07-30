import pyautogui
from tkinter import *
from tkinter import ttk
from tkinter import messagebox
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
    pyautogui.mouseDown()

def mouse_up():
    pyautogui.mouseUp()

def left_click():
    pyautogui.click()

# --- GUI and Bot Logic ---
class FishingBotApp(Tk):
    def __init__(self):
        super().__init__()
        self.title("Fishing Bot [OFF]")
        self.geometry("550x200")
        self.resizable(False, False)
        self.attributes("-topmost", True)

        self.running = False
        self.mouse_held = False
        self.last_battling = False
        self.autoclicker_active = False
        self.autoclicker_instance = None
        self.fishes_ctr = 0
        self.click_ctr = 0
        self.reel_ctr = 1
        self.last_toggle = 0

        self.status_label = Label(self, text="Status: OFF")
        self.status_label.pack(pady=5)
        self.region_label = Label(self, text="Region: Detecting...")
        self.region_label.pack(pady=5)
        self.fishes_label = Label(self, text="Fish attempts: 0")
        self.fishes_label.pack(pady=5)

        self.button_container = Frame(self)
        self.button_container.pack()
        self.help_btn = ttk.Button(self.button_container, text="Help", command=self.show_help)
        self.help_btn.grid(row=0, column=0)
        self.autoclicker_btn = ttk.Button(self.button_container, text="Autoclicker", command=self.show_autoclicker)
        self.autoclicker_btn.grid(row=0, column=1)

        self.protocol("WM_DELETE_WINDOW", self.exit_program)

        self.region = self.setup_region()
        self.region_none = self.region == (0, 0, 0, 0)
        self.start_threads()
        self.help_window_instance = None

    def setup_region(self):
        roblox_window = get_roblox_window()
        if roblox_window is None:
            self.region_label.config(text="Region: NONE")
            self.region_none = True
            return (0, 0, 0, 0)
        region_info = calculate_expected_bar_position(roblox_window)
        region = (
            region_info['expected_x'],
            region_info['expected_y'],
            region_info['expected_width'],
            region_info['expected_height']
        )
        self.region_label.config(text=f"Region: {region}")
        self.region_none = False
        return region

    def start_threads(self):
        threading.Thread(target=self.monitor_hotkeys, daemon=True).start()
        threading.Thread(target=self.bot_loop, daemon=True).start()

    def monitor_hotkeys(self):
        while True:
            try:
                if self.autoclicker_active:
                    if keyboard.is_pressed("F6"):
                        now = time.time()
                        if now - self.last_toggle > 0.3:
                            self.autoclicker_instance.toggle_clicking()
                            self.last_toggle = now
                    elif keyboard.is_pressed("F7"):
                        self.autoclicker_instance.force_quit()
                        self.autoclicker_active = False
                        break
                else:
                    if keyboard.is_pressed("F6"):
                        now = time.time()
                        if now - self.last_toggle > 0.3:
                            self.toggle_running()
                            self.last_toggle = now
                    elif keyboard.is_pressed("F7"):
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

    def toggle_running(self):
        if self.region_none:
            messagebox.showerror("Roblox not detected!", "Roblox not detected! (Press F8 when you're ingame)")
            return
        self.running = not self.running
        self.title(f"Fishing Bot [{'ON' if self.running else 'OFF'}]")
        if self.running:
            self.autoclicker_btn.state(['disabled'])
        else:
            self.autoclicker_btn.state(['!disabled'])

    def bot_loop(self):
        while True:
            if self.region_none or not self.running:
                if not self.autoclicker_active:
                    self.status_label.config(text="Status: OFF")
                time.sleep(0.2)
                continue
            try:
                screenshot = pyautogui.screenshot(region=self.region)
                x_pos = find_red_bar_x(screenshot)
                gray_center = find_gray_area_center(screenshot)

                if x_pos is not None and gray_center is not None:
                    self.click_ctr = 0
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
                    self.last_battling = True
                else:
                    if self.last_battling:
                        self.fishes_ctr += 1
                        self.fishes_label.config(text=f"Fish attempts: {self.fishes_ctr}")
                    self.last_battling = False

                    self.status_label.config(text=f"Status: Reeling ({self.reel_ctr})")
                    if self.mouse_held:
                        mouse_up()
                        self.mouse_held = False
                    self.click_ctr += 1
                    if self.click_ctr > 10:
                        self.reel_ctr += 1
                        left_click()
                        self.click_ctr = 0

                time.sleep(0.01)
            except Exception as e:
                print("❌ Bot Error:", e)

    def show_help(self):
        if self.help_window_instance is not None and self.help_window_instance.winfo_exists():
            self.help_window_instance.focus()
            return
        self.freeze_gui()
        self.help_window_instance = Toplevel(self)
        self.help_window_instance.title("Help")
        self.help_window_instance.geometry("500x150")
        self.help_window_instance.resizable(False, False)

        help_text = (
            "F6 = Toggle ON/OFF\n"
            "F7 = Emergency Stop\n"
            "F8 = Recalibrate Region"
        )
        Label(self.help_window_instance, text=help_text, justify=LEFT).pack(padx=15, pady=15, fill=BOTH, expand=True)

        def on_close():
            if self.help_window_instance is not None and self.help_window_instance.winfo_exists():
                self.help_window_instance.destroy()
            self.help_window_instance = None
            self.help_btn.state(['!disabled'])
            self.unfreeze_gui()

        self.help_window_instance.protocol("WM_DELETE_WINDOW", on_close)

    def freeze_gui(self):
        def _disable_all(widget):
            try:
                widget.configure(state='disabled')
            except:
                pass
            for child in widget.winfo_children():
                _disable_all(child)
        _disable_all(self)

    def unfreeze_gui(self):
        def _enable_all(widget):
            try:
                widget.configure(state='normal')
            except:
                pass
            for child in widget.winfo_children():
                _enable_all(child)
        _enable_all(self)

    def show_autoclicker(self):
        import mouse

        self.autoclicker_active = True
        self.title("Fishing Bot [DISABLED]")
        self.status_label.config(text="Status: DISABLED")
        self.freeze_gui()
        autoclicker_window = Toplevel(self)
        autoclicker_window.title("Autoclicker [OFF]")
        autoclicker_window.geometry("350x300")
        autoclicker_window.resizable(False, False)

        interval_var = StringVar(value="0.01")
        button_var = StringVar(value="Left")
        clicking = [False]

        def click_mouse():
            button = 'left' if button_var.get() == "Left" else 'right'
            try:
                interval = float(interval_var.get())
            except ValueError:
                interval = 0.01
            while clicking[0]:
                autoclicker_window.title("Autoclicker [ON]")
                mouse.click(button)
                time.sleep(interval)
            autoclicker_window.title("Autoclicker [OFF]")

        def toggle_clicking():
            clicking[0] = not clicking[0]
            if clicking[0]:
                autoclicker_window.title("Autoclicker [ON]")
                autoclicker_help_btn.state(['disabled'])
                interval_label.configure(state='disabled')
                interval_entry.configure(state='disabled')
                threading.Thread(target=click_mouse, daemon=True).start()
            else:
                autoclicker_window.title("Autoclicker [OFF]")
                autoclicker_help_btn.state(['!disabled'])
                interval_label.configure(state='normal')
                interval_entry.configure(state='normal')

        def force_quit():
            clicking[0] = False
            autoclicker_window.destroy()
            self.autoclicker_active = False
            self.autoclicker_instance = None
            self.title("Fishing Bot [OFF]")
            self.status_label.config(text="Status: OFF")
            self.unfreeze_gui()

        self.autoclicker_instance = type('AutoClickerInstance', (), {
            'toggle_clicking': staticmethod(toggle_clicking),
            'force_quit': staticmethod(force_quit)
        })

        Label(autoclicker_window, text="Click Interval (seconds):").pack(pady=5)
        interval_label = autoclicker_window.children[list(autoclicker_window.children.keys())[-1]]
        interval_entry = Entry(autoclicker_window, textvariable=interval_var)
        interval_entry.pack(pady=5)

        Label(autoclicker_window, text="Mouse Button:").pack(pady=5)
        ttk.Combobox(autoclicker_window, textvariable=button_var,
                    values=["Left", "Right"], state="readonly").pack(pady=5)

        autoclicker_help_btn = ttk.Button(autoclicker_window, text="Help")
        autoclicker_help_btn.pack(pady=10)

        def freeze_autoclicker():
            def _disable_all(widget):
                try:
                    widget.configure(state='disabled')
                except:
                    pass
                for child in widget.winfo_children():
                    _disable_all(child)
            _disable_all(autoclicker_window)

        def unfreeze_autoclicker():
            def _enable_all(widget):
                try:
                    widget.configure(state='normal')
                except:
                    pass
                for child in widget.winfo_children():
                    _enable_all(child)
            _enable_all(autoclicker_window)

        def show_autoclicker_help():
            autoclicker_window.title("Autoclicker [DISABLED]")
            freeze_autoclicker()
            help_window = Toplevel(autoclicker_window)
            help_window.title("Help")
            help_window.geometry("500x150")
            help_window.resizable(False, False)
            help_text = "F6 = Toggle ON/OFF\nF7 = Emergency Stop"
            Label(help_window, text=help_text, justify=LEFT).pack(padx=15, pady=15, fill=BOTH, expand=True)
            def on_close():
                if help_window.winfo_exists():
                    help_window.destroy()
                autoclicker_help_btn.state(['!disabled'])
                autoclicker_window.title("Autoclicker [ON]" if clicking[0] else "Autoclicker [OFF]")
                unfreeze_autoclicker()
            help_window.protocol("WM_DELETE_WINDOW", on_close)

        autoclicker_help_btn.config(command=show_autoclicker_help)
        autoclicker_window.protocol("WM_DELETE_WINDOW", force_quit)

    def exit_program(self):
        try:
            mouse_up()
        except:
            pass
        self.destroy()
        sys.exit()

if __name__ == "__main__":
    app = FishingBotApp()
    app.mainloop()
