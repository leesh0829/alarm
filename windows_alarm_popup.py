import json
import os
import threading
import time
from datetime import datetime
import tkinter as tk
from tkinter import messagebox, ttk

CONFIG_FILE = "alarm_schedule.json"
CHECK_INTERVAL_SECONDS = 15
WINDOW_GEOMETRY = "420x180"
DEFAULT_POSITION = "center"  # center | bottom_right


DEFAULT_CONFIG = {
    "position": "center",
    "alarms": [
        {
            "date": "2026-03-12",
            "times": ["09:00", "13:30", "18:00"],
            "title": "알람",
            "message": "확인할 작업이 있어요.",
        }
    ],
}


class AlarmApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw()  # 메인창 숨김
        self.triggered = set()
        self.lock = threading.Lock()
        self.config = self.load_config()
        self.running = True

    def load_config(self):
        if not os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(DEFAULT_CONFIG, f, ensure_ascii=False, indent=2)
            return DEFAULT_CONFIG

        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            messagebox.showerror(
                "설정 파일 오류",
                f"{CONFIG_FILE} 파일을 읽을 수 없습니다.\n형식을 확인하세요.",
            )
            return DEFAULT_CONFIG

    def reload_config(self):
        with self.lock:
            self.config = self.load_config()

    def get_due_alarms(self, now):
        due = []
        date_str = now.strftime("%Y-%m-%d")
        current_minute = now.strftime("%H:%M")

        alarms = self.config.get("alarms", [])
        for item in alarms:
            if item.get("date") != date_str:
                continue

            for t in item.get("times", []):
                alarm_key = f"{item.get('date')}|{t}|{item.get('title', '알람')}|{item.get('message', '')}"
                if t == current_minute and alarm_key not in self.triggered:
                    due.append({
                        "key": alarm_key,
                        "title": item.get("title", "알람"),
                        "message": item.get("message", "확인할 작업이 있어요."),
                    })
        return due

    def mark_triggered(self, key):
        with self.lock:
            self.triggered.add(key)

    def show_popup(self, title, message):
        popup = tk.Toplevel(self.root)
        popup.title(title)
        popup.attributes("-topmost", True)
        popup.resizable(False, False)
        popup.geometry(WINDOW_GEOMETRY)
        popup.configure(bg="#f7f7f7")

        frame = ttk.Frame(popup, padding=16)
        frame.pack(fill="both", expand=True)

        title_label = ttk.Label(frame, text=title, font=("Malgun Gothic", 14, "bold"))
        title_label.pack(anchor="w", pady=(0, 10))

        message_label = ttk.Label(
            frame,
            text=message,
            font=("Malgun Gothic", 11),
            wraplength=360,
            justify="left",
        )
        message_label.pack(anchor="w", fill="x")

        button_frame = ttk.Frame(frame)
        button_frame.pack(fill="x", pady=(18, 0))

        close_button = ttk.Button(button_frame, text="닫기", command=popup.destroy)
        close_button.pack(side="right")

        popup.update_idletasks()
        self.place_popup(popup)
        popup.lift()
        popup.focus_force()

    def place_popup(self, popup):
        popup.update_idletasks()
        width = popup.winfo_width()
        height = popup.winfo_height()
        screen_w = popup.winfo_screenwidth()
        screen_h = popup.winfo_screenheight()

        position = self.config.get("position", DEFAULT_POSITION)

        if position == "bottom_right":
            x = screen_w - width - 30
            y = screen_h - height - 70
        else:
            x = (screen_w // 2) - (width // 2)
            y = (screen_h // 2) - (height // 2)

        popup.geometry(f"{width}x{height}+{x}+{y}")

    def scheduler_loop(self):
        last_checked_minute = None

        while self.running:
            self.reload_config()
            now = datetime.now()
            current_minute = now.strftime("%Y-%m-%d %H:%M")

            if current_minute != last_checked_minute:
                due_alarms = self.get_due_alarms(now)
                for alarm in due_alarms:
                    self.mark_triggered(alarm["key"])
                    self.root.after(0, self.show_popup, alarm["title"], alarm["message"])
                last_checked_minute = current_minute

            time.sleep(CHECK_INTERVAL_SECONDS)

    def run(self):
        thread = threading.Thread(target=self.scheduler_loop, daemon=True)
        thread.start()
        self.root.mainloop()
        self.running = False


if __name__ == "__main__":
    app = AlarmApp()
    app.run()
