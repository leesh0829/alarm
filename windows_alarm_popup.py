import argparse
import json
import os
import subprocess
import threading
import time
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import messagebox, ttk

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "alarm_schedule.json")
PID_FILE = os.path.join(BASE_DIR, "alarm_app.pid")
STOP_FILE = os.path.join(BASE_DIR, "alarm_app.stop")
CHECK_INTERVAL_SECONDS = 15
WINDOW_GEOMETRY = "460x220"
DEFAULT_POSITION = "center"  # center | bottom_right

WEEKDAY_MAP = {
    "mon": 0,
    "monday": 0,
    "월": 0,
    "화": 1,
    "tue": 1,
    "tuesday": 1,
    "수": 2,
    "wed": 2,
    "wednesday": 2,
    "목": 3,
    "thu": 3,
    "thursday": 3,
    "금": 4,
    "fri": 4,
    "friday": 4,
    "토": 5,
    "sat": 5,
    "saturday": 5,
    "일": 6,
    "sun": 6,
    "sunday": 6,
}


DEFAULT_CONFIG = {
    "position": "center",
    "alarms": [
        {
            "type": "daily",
            "times": ["09:00", "13:30", "18:00"],
            "title": "매일 알람",
            "message": "확인할 작업이 있어요.",
        },
        {
            "type": "weekday",
            "weekdays": ["mon", "wed", "fri"],
            "times": ["08:40"],
            "title": "운동 알람",
            "message": "운동 갈 시간이에요!",
        },
        {
            "type": "once",
            "date": "2026-03-12",
            "times": ["15:00"],
            "title": "단일 알람",
            "message": "오늘만 울리는 알람",
        },
    ],
}


def show_message(kind, title, message):
    root = tk.Tk()
    root.withdraw()
    try:
        if kind == "error":
            messagebox.showerror(title, message, parent=root)
        else:
            messagebox.showinfo(title, message, parent=root)
    finally:
        root.destroy()


def read_pid():
    if not os.path.exists(PID_FILE):
        return None

    try:
        with open(PID_FILE, "r", encoding="utf-8") as f:
            value = f.read().strip()
    except OSError:
        return None

    if not value.isdigit():
        return None
    return int(value)


def write_pid(pid):
    with open(PID_FILE, "w", encoding="utf-8") as f:
        f.write(str(pid))


def remove_file(path):
    try:
        os.remove(path)
    except FileNotFoundError:
        pass


def is_process_running(pid):
    if not pid or pid <= 0:
        return False

    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def ensure_single_instance():
    existing_pid = read_pid()
    current_pid = os.getpid()

    if existing_pid and existing_pid != current_pid and is_process_running(existing_pid):
        raise RuntimeError(f"이미 실행 중입니다. PID: {existing_pid}")

    remove_file(STOP_FILE)
    write_pid(current_pid)


def request_stop():
    with open(STOP_FILE, "w", encoding="utf-8") as f:
        f.write(str(time.time()))


def stop_running_app(timeout_seconds=10):
    pid = read_pid()
    if not pid:
        return False, "실행 중인 알람 앱이 없습니다."

    if not is_process_running(pid):
        remove_file(PID_FILE)
        remove_file(STOP_FILE)
        return False, "이미 종료된 프로세스였습니다. PID 파일만 정리했습니다."

    request_stop()

    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if not is_process_running(pid):
            remove_file(PID_FILE)
            remove_file(STOP_FILE)
            return True, "알람 앱을 종료했습니다."
        time.sleep(0.2)

    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    result = subprocess.run(
        ["taskkill", "/PID", str(pid), "/T", "/F"],
        capture_output=True,
        text=True,
        creationflags=creation_flags,
        check=False,
    )

    remove_file(PID_FILE)
    remove_file(STOP_FILE)

    if result.returncode == 0:
        return True, "알람 앱을 종료했습니다."
    return False, "알람 앱 종료에 실패했습니다. 작업 관리자에서 확인해 주세요."


def get_status_message():
    pid = read_pid()
    if not pid:
        return "알람 앱이 실행 중이 아닙니다."
    if not is_process_running(pid):
        remove_file(PID_FILE)
        remove_file(STOP_FILE)
        return "실행 중이 아닌 이전 PID 파일을 정리했습니다."
    return f"알람 앱이 실행 중입니다. PID: {pid}"


class AlarmApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw()  # 메인창 숨김
        self.triggered = set()
        self.snoozed = []
        self.lock = threading.Lock()
        self.config = self.load_config()
        self.running = True

    def normalize_weekdays(self, raw_weekdays):
        normalized = []
        for day in raw_weekdays:
            if isinstance(day, int) and 0 <= day <= 6:
                normalized.append(day)
                continue

            key = str(day).strip().lower()
            if key not in WEEKDAY_MAP:
                raise ValueError(f"지원하지 않는 요일 값: {day}")
            normalized.append(WEEKDAY_MAP[key])

        return sorted(set(normalized))

    def normalize_times(self, raw_times):
        if not isinstance(raw_times, list) or not raw_times:
            raise ValueError("times는 최소 1개 이상의 HH:MM 문자열 리스트여야 합니다.")

        normalized = []
        for time_value in raw_times:
            candidate = str(time_value).strip().replace(",", ":")
            try:
                t = datetime.strptime(candidate, "%H:%M")
            except ValueError as exc:
                raise ValueError(f"잘못된 시간 형식: {time_value}") from exc
            normalized.append(t.strftime("%H:%M"))

        return sorted(set(normalized))

    def validate_and_normalize_config(self, data):
        if not isinstance(data, dict):
            raise ValueError("설정 루트는 객체(JSON object)여야 합니다.")

        position = data.get("position", DEFAULT_POSITION)
        if position not in {"center", "bottom_right"}:
            raise ValueError("position은 center 또는 bottom_right 만 허용됩니다.")

        alarms = data.get("alarms")
        if not isinstance(alarms, list) or not alarms:
            raise ValueError("alarms는 최소 1개 이상의 리스트여야 합니다.")

        normalized_alarms = []
        for idx, alarm in enumerate(alarms):
            if not isinstance(alarm, dict):
                raise ValueError(f"alarms[{idx}]는 객체여야 합니다.")

            alarm_type = alarm.get("type")
            if alarm_type is None:
                alarm_type = "once" if "date" in alarm else "daily"

            if alarm_type not in {"once", "daily", "weekday"}:
                raise ValueError(f"alarms[{idx}].type은 once/daily/weekday 중 하나여야 합니다.")

            normalized_alarm = {
                "type": alarm_type,
                "times": self.normalize_times(alarm.get("times", [])),
                "title": str(alarm.get("title", "알람")).strip() or "알람",
                "message": str(alarm.get("message", "확인할 작업이 있어요.")).strip() or "확인할 작업이 있어요.",
            }

            if alarm_type == "once":
                date_value = alarm.get("date")
                if not date_value:
                    raise ValueError(f"alarms[{idx}]는 once 타입일 때 date가 필요합니다.")
                try:
                    datetime.strptime(str(date_value), "%Y-%m-%d")
                except ValueError as exc:
                    raise ValueError(f"alarms[{idx}].date 형식은 YYYY-MM-DD 이어야 합니다.") from exc
                normalized_alarm["date"] = str(date_value)

            if alarm_type == "weekday":
                weekdays = alarm.get("weekdays")
                if not isinstance(weekdays, list) or not weekdays:
                    raise ValueError(f"alarms[{idx}]는 weekday 타입일 때 weekdays 리스트가 필요합니다.")
                normalized_alarm["weekdays"] = self.normalize_weekdays(weekdays)

            normalized_alarms.append(normalized_alarm)

        return {"position": position, "alarms": normalized_alarms}

    def load_config(self):
        if not os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(DEFAULT_CONFIG, f, ensure_ascii=False, indent=2)
            return self.validate_and_normalize_config(DEFAULT_CONFIG)

        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            return self.validate_and_normalize_config(loaded)
        except Exception as exc:
            messagebox.showerror(
                "설정 파일 오류",
                f"{CONFIG_FILE} 파일을 읽을 수 없거나 형식이 잘못되었습니다.\n\n{exc}",
            )
            return self.validate_and_normalize_config(DEFAULT_CONFIG)

    def reload_config(self):
        with self.lock:
            self.config = self.load_config()

    def is_alarm_due_today(self, alarm, now):
        alarm_type = alarm.get("type")
        if alarm_type == "daily":
            return True
        if alarm_type == "once":
            return alarm.get("date") == now.strftime("%Y-%m-%d")
        if alarm_type == "weekday":
            return now.weekday() in alarm.get("weekdays", [])
        return False

    def get_due_alarms(self, now):
        due = []
        current_minute = now.strftime("%H:%M")
        occurrence_date = now.strftime("%Y-%m-%d")

        alarms = self.config.get("alarms", [])
        for idx, item in enumerate(alarms):
            if not self.is_alarm_due_today(item, now):
                continue

            for t in item.get("times", []):
                alarm_key = f"{occurrence_date}|{idx}|{t}|{item.get('title', '알람')}"
                if t == current_minute and alarm_key not in self.triggered:
                    due.append(
                        {
                            "key": alarm_key,
                            "title": item.get("title", "알람"),
                            "message": item.get("message", "확인할 작업이 있어요."),
                        }
                    )
        return due

    def get_due_snoozed(self, now):
        due = []
        with self.lock:
            remaining = []
            for item in self.snoozed:
                if item["due"] <= now:
                    due.append(item)
                else:
                    remaining.append(item)
            self.snoozed = remaining
        return due

    def schedule_snooze(self, title, message, minutes=5):
        due_at = datetime.now() + timedelta(minutes=minutes)
        with self.lock:
            self.snoozed.append({"due": due_at, "title": title, "message": message})

    def mark_triggered(self, key):
        with self.lock:
            self.triggered.add(key)
            if len(self.triggered) > 5000:
                self.triggered = set(sorted(self.triggered)[-2000:])

    def show_popup(self, title, message):
        popup = tk.Toplevel(self.root)
        popup.title(title)
        popup.attributes("-topmost", True)
        popup.resizable(False, False)
        popup.geometry(WINDOW_GEOMETRY)
        popup.configure(bg="#f7f7f7")

        frame = ttk.Frame(popup, padding=16)
        frame.pack(fill="both", expand=True)

        badge = ttk.Label(frame, text="⏰", font=("Malgun Gothic", 20, "bold"))
        badge.pack(anchor="w")

        title_label = ttk.Label(frame, text=title, font=("Malgun Gothic", 14, "bold"))
        title_label.pack(anchor="w", pady=(2, 8))

        message_label = ttk.Label(
            frame,
            text=message,
            font=("Malgun Gothic", 11),
            wraplength=390,
            justify="left",
        )
        message_label.pack(anchor="w", fill="x")

        help_label = ttk.Label(frame, text="지금 할 일이라면 바로 처리하세요.", font=("Malgun Gothic", 9))
        help_label.pack(anchor="w", pady=(8, 0))

        button_frame = ttk.Frame(frame)
        button_frame.pack(fill="x", pady=(16, 0))

        snooze_button = ttk.Button(
            button_frame,
            text="5분 후 다시",
            command=lambda: (self.schedule_snooze(title, message, 5), popup.destroy()),
        )
        snooze_button.pack(side="left")

        close_button = ttk.Button(button_frame, text="닫기", command=popup.destroy)
        close_button.pack(side="right")

        popup.bind("<Escape>", lambda _event: popup.destroy())

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
            if os.path.exists(STOP_FILE):
                self.root.after(0, self.shutdown)
                break

            self.reload_config()
            now = datetime.now()
            current_minute = now.strftime("%Y-%m-%d %H:%M")

            for snoozed_alarm in self.get_due_snoozed(now):
                self.root.after(0, self.show_popup, snoozed_alarm["title"], snoozed_alarm["message"])

            if current_minute != last_checked_minute:
                due_alarms = self.get_due_alarms(now)
                for alarm in due_alarms:
                    self.mark_triggered(alarm["key"])
                    self.root.after(0, self.show_popup, alarm["title"], alarm["message"])
                last_checked_minute = current_minute

            time.sleep(CHECK_INTERVAL_SECONDS)

    def shutdown(self):
        if not self.running:
            return
        self.running = False
        remove_file(STOP_FILE)
        if self.root.winfo_exists():
            self.root.quit()
            self.root.destroy()

    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self.shutdown)
        thread = threading.Thread(target=self.scheduler_loop, daemon=True)
        thread.start()
        self.root.mainloop()
        self.running = False
        remove_file(PID_FILE)
        remove_file(STOP_FILE)


def parse_args():
    parser = argparse.ArgumentParser(description="Windows alarm popup app")
    parser.add_argument(
        "command",
        nargs="?",
        choices=["start", "stop", "status"],
        default="start",
        help="start: 실행, stop: 종료, status: 상태 확인",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    if args.command == "stop":
        ok, message = stop_running_app()
        print(message)
        show_message("info" if ok else "error", "알람 종료", message)
    elif args.command == "status":
        message = get_status_message()
        print(message)
        show_message("info", "알람 상태", message)
    else:
        try:
            ensure_single_instance()
            app = AlarmApp()
            app.run()
        except RuntimeError as exc:
            message = str(exc)
            print(message)
            show_message("info", "알람 실행", message)
