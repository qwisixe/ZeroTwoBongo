import sys
import tkinter as tk
from PIL import Image, ImageTk
from itertools import count
import os
import json
import hashlib
import random
import subprocess
import time

try:
    import winsound
except ImportError:
    winsound = None

MAIN_GIF = "zero_two.gif"
ALT_GIF = "zero_two_alt.gif"

# Старые файлы теперь используются только как опциональный бэкап при первом запуске
SCORE_FILE = "score.txt"
UPGRADE_FILE = "upgrades.txt"

SAVEGAME_FILE = "savegame.txt"
SETTINGS_FILE = "settings.txt"

# Версия игры и форма сохранения
GAME_VERSION = "v0.4.0"
SAVE_SECRET = "zero_two_super_secret_salt_2026"
SAVE_SCHEMA_VERSION = 2
STATUS_DISPLAY_MS = 2800

# Anti-cheat лимиты (подбирай под баланс)
MAX_SCORE = 10_000_000
MAX_MULTIPLIER = 1_000.0
MAX_ANIM_SPEED = 20.0
MIN_ANIM_SPEED = 0.5
MIN_AUTO_INTERVAL = 100  # мс

THEMES = {
    "pink": {
        "bg": "#ffb6c1",
        "panel": "#ff69b4",
        "button_bg": "#ff1493",
        "button_active": "#ff85c2",
        "text": "#1b1b2f",
    },
    "neon": {
        "bg": "#0f172a",
        "panel": "#0ea5e9",
        "button_bg": "#14b8a6",
        "button_active": "#38bdf8",
        "text": "#f8fafc",
    },
}

TOOLTIPS = {
    "play": "Начать игру",
    "shop": "Открыть магазин улучшений",
    "save": "Сохранить прогресс",
    "settings": "Открыть настройки",
    "menu": "Вернуться в главное меню",
    "hit": "Нажмите или пробел, чтобы ударить",
    "achievements": "Посмотреть достижения",
    "themes": "Выбрать тему оформления",
    "close": "Закрыть окно",
    "buy": "Купить улучшение",
}

RESOURCE_DIR = os.path.abspath(os.path.dirname(__file__))


def get_resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(RESOURCE_DIR, relative_path)

TOOLTIPS = {
    "play": "Начать игру",
    "shop": "Открыть магазин улучшений",
    "save": "Сохранить прогресс",
    "settings": "Открыть настройки",
    "menu": "Вернуться в главное меню",
    "hit": "Ударьте по экрану или нажмите пробел",
    "achievements": "Показать выполненные задания",
    "themes": "Выбрать тему оформления",
    "close": "Закрыть окно",
}


class Tooltip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        widget.bind("<Enter>", self.enter)
        widget.bind("<Leave>", self.leave)

    def enter(self, event=None):
        self.show_tip()

    def leave(self, event=None):
        self.hide_tip()

    def show_tip(self):
        if self.tipwindow or not self.text:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 10
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(
            tw,
            text=self.text,
            justify=tk.LEFT,
            background="#ffffe0",
            relief=tk.SOLID,
            borderwidth=1,
            font=("Arial", 9),
        )
        label.pack(ipadx=4, ipady=2)

    def hide_tip(self):
        if self.tipwindow:
            self.tipwindow.destroy()
            self.tipwindow = None


class ZeroTwoGame(tk.Tk):
    def __init__(self):
        super().__init__()

        # настройки окна по умолчанию
        self.default_width = 1024
        self.default_height = 768
        self.screen_width = self.winfo_screenwidth()
        self.screen_height = self.winfo_screenheight()

        # загрузка настроек (разрешение, тема, звук, автосохранение, полноэкранный режим)
        (
            self.window_width,
            self.window_height,
            self.active_theme,
            self.sound_enabled,
            self.auto_save_enabled,
            self.fullscreen,
        ) = self.load_settings()

        self.title(f"Zero Two Bongo {GAME_VERSION}")
        self.set_geometry(self.window_width, self.window_height)
        self.ensure_desktop_shortcut()

        # состояние игры (дефолт)
        self.score = 0
        self.best_score = 0
        self.multiplier = 1.0
        self.auto_interval_ms = 0
        self.use_alt_skin = False
        self.anim_speed_factor = 1.0
        self.alt_unlocked = False
        self.unlocked_upgrades = {
            "multiplier": 0,
            "autoclick": 0,
            "animation": 0,
            "skins": 0,
            "theme": 0,
        }
        self.quest_progress = {
            "hits": 0,
            "shops_visited": 0,
            "skins_unlocked": 0,
            "themes_unlocked": 0,
        }
        self.status_message = ""
        self.status_after_id = None
        self.combo_streak = 0
        self.last_hit_time = 0.0
        self.total_hits = 0
        self.last_bonus_time = 0.0

        self.current_frame = None
        self.active_keys = set()

        # флаги процессов
        self.animation_running = False
        self.animation_after_id = None
        self.auto_click_running = False

        self.sound_paths = {
            "click": get_resource_path(os.path.join("audio", "click.wav")),
            "hit": get_resource_path(os.path.join("audio", "hit.wav")),
            "purchase": get_resource_path(os.path.join("audio", "purchase.wav")),
            "error": get_resource_path(os.path.join("audio", "error.wav")),
        }

        # пробуем загрузить защищённое сохранение
        if os.path.exists(SAVEGAME_FILE):
            self.load_game_manual()
        else:
            # если нет savegame – пробуем один раз подхватить старые txt и сразу сохранить в новый формат
            self.migrate_from_legacy_files()
            self.save_game_manual()

        self.create_start_screen()

    # ===== темы и стиль =====

    def theme_color(self, role):
        return THEMES.get(self.active_theme, THEMES["pink"]).get(role, "#ffffff")

    def apply_theme(self, widget, role, **kwargs):
        widget.configure(bg=self.theme_color(role), fg=self.theme_color("text"), **kwargs)

    def make_button(self, parent, text, command, width=None, height=None, tooltip_key=None):
        btn = tk.Button(
            parent,
            text=text,
            command=lambda *args, **kwargs: self.on_button_click(command),
            fg="white",
            bg=self.theme_color("button_bg"),
            activebackground=self.theme_color("button_active"),
            activeforeground=self.theme_color("text"),
            relief="raised",
            bd=2,
            font=("Arial", 12, "bold"),
            cursor="hand2",
            padx=10,
            pady=6,
            width=width,
            height=height,
        )
        self.decorate_button(btn)
        if tooltip_key and tooltip_key in TOOLTIPS:
            Tooltip(btn, TOOLTIPS[tooltip_key])
        return btn

    def decorate_button(self, button):
        def on_enter(event):
            button.configure(bg=self.theme_color("button_active"))
        def on_leave(event):
            button.configure(bg=self.theme_color("button_bg"))
        def on_press(event):
            button.configure(relief="sunken")
            self.play_sound("click")
        def on_release(event):
            button.configure(relief="raised")
        button.bind("<Enter>", on_enter)
        button.bind("<Leave>", on_leave)
        button.bind("<ButtonPress-1>", on_press)
        button.bind("<ButtonRelease-1>", on_release)

    def on_button_click(self, command):
        try:
            command()
        except TypeError:
            try:
                command(None)
            except Exception:
                pass

    def play_sound(self, sound_name):
        if not getattr(self, "sound_enabled", True):
            return
        path = self.sound_paths.get(sound_name)
        if not path or not os.path.exists(path):
            return
        if winsound:
            try:
                winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)
            except Exception:
                pass
        else:
            try:
                self.bell()
            except Exception:
                pass

    def show_status(self, message, duration=STATUS_DISPLAY_MS):
        if self.status_after_id is not None:
            self.after_cancel(self.status_after_id)
            self.status_after_id = None
        self.status_message = message
        if hasattr(self, "status_label"):
            self.status_label.config(text=self.status_message)
        self.status_after_id = self.after(duration, self.clear_status)

    def clear_status(self):
        self.status_message = ""
        if hasattr(self, "status_label"):
            self.status_label.config(text=self.status_message)
        self.status_after_id = None

    # ===== работа с окном / настройками =====

    def set_geometry(self, w, h):
        if getattr(self, "fullscreen", False):
            self.attributes("-fullscreen", True)
        else:
            self.attributes("-fullscreen", False)
            self.geometry(f"{w}x{h}+100+100")
        self.minsize(self.default_width, self.default_height)
        self.maxsize(self.screen_width, self.screen_height)
        bg_color = self.theme_color("bg") if hasattr(self, "active_theme") else "#ffb6c1"
        self.configure(bg=bg_color)

    def load_settings(self):
        theme = "pink"
        sound_enabled = True
        auto_save_enabled = True
        fullscreen = False
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    w = min(self.screen_width, max(self.default_width, int(data.get("width", self.default_width))))
                    h = min(self.screen_height, max(self.default_height, int(data.get("height", self.default_height))))
                    theme = str(data.get("theme", theme))
                    if theme not in THEMES:
                        theme = "pink"
                    sound_enabled = bool(data.get("sound_enabled", sound_enabled))
                    auto_save_enabled = bool(data.get("auto_save_enabled", auto_save_enabled))
                    fullscreen = bool(data.get("fullscreen", fullscreen))
                    return w, h, theme, sound_enabled, auto_save_enabled, fullscreen
            except Exception:
                return self.default_width, self.default_height, theme, sound_enabled, auto_save_enabled, fullscreen
        return self.default_width, self.default_height, theme, sound_enabled, auto_save_enabled, fullscreen

    def save_settings(self):
        data = {
            "width": self.window_width,
            "height": self.window_height,
            "theme": self.active_theme,
            "sound_enabled": self.sound_enabled,
            "auto_save_enabled": self.auto_save_enabled,
            "fullscreen": self.fullscreen,
        }
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def get_desktop_path(self):
        try:
            from ctypes import wintypes, windll, create_unicode_buffer
            CSIDL_DESKTOPDIRECTORY = 0x0010
            SHGFP_TYPE_CURRENT = 0
            buf = create_unicode_buffer(wintypes.MAX_PATH)
            res = windll.shell32.SHGetFolderPathW(None, CSIDL_DESKTOPDIRECTORY, None, SHGFP_TYPE_CURRENT, buf)
            if res == 0:
                return buf.value
        except Exception:
            pass
        return os.path.join(os.path.expanduser("~"), "Desktop")

    def create_desktop_shortcut(self, target_path, shortcut_path, icon_path=None):
        try:
            if os.path.exists(shortcut_path):
                return True
            target_path = os.path.normpath(target_path)
            icon_path = os.path.normpath(icon_path) if icon_path else target_path
            ps_script = (
                f"$ws = New-Object -ComObject WScript.Shell; "
                f"$sc = $ws.CreateShortcut('{shortcut_path}'); "
                f"$sc.TargetPath = '{target_path}'; "
                f"$sc.WorkingDirectory = '{os.path.dirname(target_path)}'; "
                f"$sc.IconLocation = '{icon_path},0'; "
                f"$sc.Save();"
            )
            subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], check=True, capture_output=True)
            return True
        except Exception:
            return False

    def ensure_desktop_shortcut(self):
        if not sys.platform.startswith("win"):
            return
        app_path = os.path.abspath(sys.argv[0])
        if not app_path.lower().endswith("zerotwobongo.exe"):
            return
        desktop = self.get_desktop_path()
        if not desktop or not os.path.isdir(desktop):
            return
        shortcut = os.path.join(desktop, "ZeroTwoBongo.lnk")
        icon_file = get_resource_path("ZeroTwoBongo.ico")
        if not os.path.exists(icon_file):
            icon_file = app_path
        self.create_desktop_shortcut(app_path, shortcut, icon_file)

    # ===== миграция со старых txt (один раз) =====

    def migrate_from_legacy_files(self):
        # score
        if os.path.exists(SCORE_FILE):
            try:
                with open(SCORE_FILE, "r", encoding="utf-8") as f:
                    val = f.read().strip()
                    if val:
                        self.score = int(val)
            except Exception:
                self.score = 0

        # upgrades
        if os.path.exists(UPGRADE_FILE):
            try:
                with open(UPGRADE_FILE, "r", encoding="utf-8") as f:
                    line = f.read().strip()
                    if line:
                        parts = line.split(";")
                        self.multiplier = float(parts[0])
                        self.auto_interval_ms = int(parts[1])
                        use_alt = parts[2] == "1"
                        self.anim_speed_factor = float(parts[3])
                        self.alt_unlocked = parts[4] == "1" if len(parts) > 4 else False
                        # если ALT не куплен, MAIN по умолчанию
                        self.use_alt_skin = use_alt and self.alt_unlocked
            except Exception:
                pass

        # применяем anti-cheat лимиты к мигрированным данным
        self.apply_anti_cheat_limits()

    # ===== стартовый экран =====

    def create_start_screen(self):
        self._switch_frame(bg=self.theme_color("bg"))

        title = tk.Label(
            self.current_frame,
            text="Zero Two Bongo",
            fg=self.theme_color("text"),
            bg=self.theme_color("bg"),
            font=("Arial", 28, "bold"),
        )
        title.pack(pady=(40, 20))

        subtitle = tk.Label(
            self.current_frame,
            text="Нажимай, прокачивай и открывай новые скины!",
            fg=self.theme_color("text"),
            bg=self.theme_color("bg"),
            font=("Arial", 14),
        )
        subtitle.pack(pady=(0, 30))

        menu_frame = tk.Frame(self.current_frame, bg=self.theme_color("bg"))
        menu_frame.pack()

        play_button = self.make_button(menu_frame, "Играть", self.start_game, width=18, tooltip_key="play")
        play_button.pack(pady=8)

        shop_button = self.make_button(menu_frame, "Магазин", self.open_shop, width=18, tooltip_key="shop")
        shop_button.pack(pady=8)

        quest_button = self.make_button(menu_frame, "Задания", self.open_achievements, width=18, tooltip_key="achievements")
        quest_button.pack(pady=8)

        settings_button = self.make_button(menu_frame, "Настройки", self.open_settings, width=18, tooltip_key="settings")
        settings_button.pack(pady=8)

        themes_button = self.make_button(menu_frame, "Темы", self.open_theme_picker, width=18, tooltip_key="themes")
        themes_button.pack(pady=8)

        exit_button = self.make_button(menu_frame, "Выход", self.quit_game, width=18, tooltip_key="close")
        exit_button.pack(pady=8)

    def show_devs(self):
        self._switch_frame(bg=self.theme_color("bg"))

        label = tk.Label(
            self.current_frame,
            text=f"Главный разработчик - qwisixe\nВерсия игры: {GAME_VERSION}",
            fg=self.theme_color("text"),
            bg=self.theme_color("bg"),
            font=("Arial", 22, "bold"),
            justify="center",
        )
        label.pack(expand=True)

        back_button = self.make_button(self.current_frame, "Назад", self.create_start_screen, width=16)
        back_button.pack(pady=20)

    def quit_game(self):
        self.on_close()

    # ===== запуск игры =====

    def start_game(self):
        # сброс анимации и авто-кликера
        self.stop_animation()
        self.auto_click_running = False

        self._switch_frame(bg=self.theme_color("bg"))

        self.image_label = tk.Label(self.current_frame, bg=self.theme_color("bg"))
        self.image_label.pack(expand=True, fill=tk.BOTH)

        # нижняя панель
        self.panel = tk.Frame(self.current_frame, bg=self.theme_color("panel"), height=100)
        self.panel.pack(fill=tk.X, side=tk.BOTTOM)

        # загрузка кадров и запуск анимации
        self.load_gif_frames()
        self.current_frame_index = 0
        self.animation_running = True
        self.animate()

        # счёт
        self.score_label = tk.Label(
            self.panel,
            text=self.score_text(),
            fg=self.theme_color("text"),
            bg=self.theme_color("panel"),
            font=("Arial", 14, "bold"),
        )
        self.score_label.pack(side=tk.LEFT, padx=10)

        self.status_label = tk.Label(
            self.panel,
            text=self.status_message,
            fg=self.theme_color("text"),
            bg=self.theme_color("panel"),
            font=("Arial", 11),
        )
        self.status_label.pack(side=tk.LEFT, padx=10)

        button_frame = tk.Frame(self.panel, bg=self.theme_color("panel"))
        button_frame.pack(side=tk.RIGHT, padx=5)

        self.save_button = self.make_button(button_frame, "Сохранить", self.save_game_manual, width=10)
        self.save_button.pack(side=tk.LEFT, padx=3)

        self.settings_button = self.make_button(button_frame, "⚙", self.open_settings, width=4)
        self.settings_button.pack(side=tk.LEFT, padx=3)

        self.menu_button = self.make_button(button_frame, "Меню", self.back_to_menu, width=10)
        self.menu_button.pack(side=tk.LEFT, padx=3)

        self.shop_button = self.make_button(button_frame, "Магазин", self.open_shop, width=10)
        self.shop_button.pack(side=tk.LEFT, padx=3)

        self.hit_button = self.make_button(self.panel, "Hit!", self.on_hit, width=10, tooltip_key="hit")
        self.hit_button.config(font=("Arial", 14, "bold"), bd=3)
        self.hit_button.pack(side=tk.RIGHT, padx=10, pady=6)

        self.bind("<KeyPress>", self.on_key_press)
        self.bind("<KeyRelease>", self.on_key_release)

        # авто-кликер
        self.start_auto_clicker()

        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def back_to_menu(self):
        # при выходе в меню сохраняем через защищённую систему
        self.save_game_manual()
        self.stop_animation()
        self.auto_click_running = False
        self.create_start_screen()

    # ===== переключение экранов =====

    def _switch_frame(self, bg):
        if self.current_frame is not None:
            self.current_frame.destroy()
        frame = tk.Frame(self, bg=bg)
        frame.pack(fill=tk.BOTH, expand=True)
        self.current_frame = frame

    # ===== GIF / анимация =====

    def load_gif_frames(self):
        # MAIN по умолчанию, ALT только если куплен и выбран
        if self.use_alt_skin and self.alt_unlocked and os.path.exists(get_resource_path(ALT_GIF)):
            gif_path = get_resource_path(ALT_GIF)
            alt_mode = True
        else:
            gif_path = get_resource_path(MAIN_GIF)
            alt_mode = False

        try:
            pil_image = Image.open(gif_path)
        except Exception as e:
            raise RuntimeError(f"Не удалось открыть GIF {gif_path}: {e}")

        self.frames = []
        try:
            for i in count(0):
                pil_image.seek(i)
                frame = pil_image.copy().resize((400, 400))
                photo = ImageTk.PhotoImage(frame)
                self.frames.append(photo)
        except EOFError:
            pass

        if not self.frames:
            raise RuntimeError("GIF не содержит кадров или не поддерживается.")

        base_delay = pil_image.info.get("duration", 100) / 1000.0

        speed_factor = self.anim_speed_factor
        if alt_mode:
            speed_factor *= 1.5  # ALT чуть быстрее

        self.base_delay = max(0.02, base_delay / speed_factor)

    def stop_animation(self):
        self.animation_running = False
        if self.animation_after_id is not None:
            try:
                self.after_cancel(self.animation_after_id)
            except Exception:
                pass
            self.animation_after_id = None

    def restart_animation(self):
        # надёжный перезапуск [web:163][web:168]
        self.stop_animation()
        self.load_gif_frames()
        self.current_frame_index = 0
        self.animation_running = True
        self.animate()

    def animate(self):
        if not self.animation_running:
            return
        if not hasattr(self, "frames") or not self.frames:
            return

        self.image_label.config(image=self.frames[self.current_frame_index])
        self.image_label.image = self.frames[self.current_frame_index]

        self.current_frame_index = (self.current_frame_index + 1) % len(self.frames)
        delay_ms = int(self.base_delay * 1000)
        self.animation_after_id = self.after(delay_ms, self.animate)

    # ===== подпись и защита savegame =====

    def make_checksum(self, payload_str: str) -> str:
        h = hashlib.sha256()
        h.update((payload_str + SAVE_SECRET).encode("utf-8"))
        return h.hexdigest()

    def apply_anti_cheat_limits(self):
        # простые лимиты против накруток [web:243][web:244][web:245][web:247]
        if self.score < 0 or self.score > MAX_SCORE:
            self.score = 0
        if self.multiplier <= 0 or self.multiplier > MAX_MULTIPLIER:
            self.multiplier = 1.0
        if self.anim_speed_factor < MIN_ANIM_SPEED or self.anim_speed_factor > MAX_ANIM_SPEED:
            self.anim_speed_factor = 1.0
        if self.auto_interval_ms < 0:
            self.auto_interval_ms = 0
        elif self.auto_interval_ms != 0 and self.auto_interval_ms < MIN_AUTO_INTERVAL:
            self.auto_interval_ms = MIN_AUTO_INTERVAL

        if self.active_theme not in THEMES:
            self.active_theme = "pink"

        # если ALT не куплен, насильно MAIN
        if not self.alt_unlocked:
            self.use_alt_skin = False

    def record_hit(self):
        now = time.monotonic()
        if now - self.last_hit_time <= 1.2:
            self.combo_streak += 1
        else:
            self.combo_streak = 1
        self.last_hit_time = now
        self.total_hits += 1
        self.quest_progress["hits"] = self.total_hits

        self.add_score(1, source="hit")

        if self.combo_streak >= 5 and now - self.last_bonus_time >= 5:
            bonus = 2 * self.combo_streak
            self.add_score(bonus, source="combo")
            self.show_status(f"Combo x{self.combo_streak}! +{bonus} Score")
            self.last_bonus_time = now

        self.check_achievements()

        if random.random() < 0.08:
            bonus = random.randint(5, 15)
            self.add_score(bonus, source="event")
            self.show_status(f"Случайный бонус: +{bonus} Score")

    def check_achievements(self):
        if self.total_hits >= 1 and not self.quest_progress.get("first_hit", False):
            self.quest_progress["first_hit"] = True
            self.show_status("Достижение: Первый удар!", duration=STATUS_DISPLAY_MS)
        if self.total_hits >= 100 and not self.quest_progress.get("century_hits", False):
            self.quest_progress["century_hits"] = True
            self.show_status("Достижение: 100 ударов!", duration=STATUS_DISPLAY_MS)
        if self.score >= 1000 and not self.quest_progress.get("silver_score", False):
            self.quest_progress["silver_score"] = True
            self.show_status("Достижение: 1000 Score!", duration=STATUS_DISPLAY_MS)
        if self.alt_unlocked and not self.quest_progress.get("alt_skin", False):
            self.quest_progress["alt_skin"] = True
            self.show_status("Достижение: ALT Skin разблокирован!", duration=STATUS_DISPLAY_MS)

    def save_game_manual(self, show_notification=True):
        # сохраняем состояние
        payload = {
            "score": self.score,
            "best_score": self.best_score,
            "multiplier": self.multiplier,
            "auto_interval_ms": self.auto_interval_ms,
            "sound_enabled": self.sound_enabled,
            "auto_save_enabled": self.auto_save_enabled,
            "use_alt_skin": self.use_alt_skin,
            "anim_speed_factor": self.anim_speed_factor,
            "alt_unlocked": self.alt_unlocked,
            "active_theme": self.active_theme,
            "unlocked_upgrades": self.unlocked_upgrades,
            "quest_progress": self.quest_progress,
            "combo_streak": self.combo_streak,
            "total_hits": self.total_hits,
            "last_bonus_time": self.last_bonus_time,
        }

        try:
            payload_str = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
            checksum = self.make_checksum(payload_str)
            wrapper = {
                "version": SAVE_SCHEMA_VERSION,
                "data": payload,
                "checksum": checksum,
            }
            with open(SAVEGAME_FILE, "w", encoding="utf-8") as f:
                json.dump(wrapper, f, ensure_ascii=False)
        except Exception:
            pass

        # если есть панель (в игре), показываем уведомление
        if show_notification and hasattr(self, "panel"):
            info = tk.Label(
                self.panel,
                text="Игра сохранена",
                fg=self.theme_color("text"),
                bg=self.theme_color("panel"),
                font=("Arial", 10, "bold"),
            )
            info.pack(side=tk.LEFT, padx=5)
            self.after(2000, info.destroy)

    def load_game_manual(self):
        if not os.path.exists(SAVEGAME_FILE):
            return
        try:
            with open(SAVEGAME_FILE, "r", encoding="utf-8") as f:
                wrapper = json.load(f)

            payload = wrapper.get("data", {})
            checksum_file = wrapper.get("checksum", "")

            payload_str = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
            checksum_calc = self.make_checksum(payload_str)

            if checksum_file != checksum_calc:
                return

            self.score = int(payload.get("score", self.score))
            self.best_score = int(payload.get("best_score", self.best_score))
            self.multiplier = float(payload.get("multiplier", self.multiplier))
            self.auto_interval_ms = int(payload.get("auto_interval_ms", self.auto_interval_ms))
            self.sound_enabled = bool(payload.get("sound_enabled", self.sound_enabled))
            self.auto_save_enabled = bool(payload.get("auto_save_enabled", self.auto_save_enabled))
            self.use_alt_skin = bool(payload.get("use_alt_skin", self.use_alt_skin))
            self.anim_speed_factor = float(payload.get("anim_speed_factor", self.anim_speed_factor))
            self.alt_unlocked = bool(payload.get("alt_unlocked", self.alt_unlocked))
            self.active_theme = str(payload.get("active_theme", self.active_theme))
            if self.active_theme not in THEMES:
                self.active_theme = "pink"

            self.unlocked_upgrades = payload.get("unlocked_upgrades", self.unlocked_upgrades)
            if not isinstance(self.unlocked_upgrades, dict):
                self.unlocked_upgrades = {
                    "multiplier": 0,
                    "autoclick": 0,
                    "animation": 0,
                    "skins": 0,
                    "theme": 0,
                }

            self.quest_progress = payload.get("quest_progress", self.quest_progress)
            if not isinstance(self.quest_progress, dict):
                self.quest_progress = {
                    "hits": 0,
                    "shops_visited": 0,
                    "skins_unlocked": 0,
                    "themes_unlocked": 0,
                }

            self.combo_streak = int(payload.get("combo_streak", self.combo_streak))
            self.total_hits = int(payload.get("total_hits", self.total_hits))
            self.last_bonus_time = float(payload.get("last_bonus_time", self.last_bonus_time))

            self.apply_anti_cheat_limits()

        except Exception:
            self.score = 0
            self.multiplier = 1.0
            self.auto_interval_ms = 0
            self.use_alt_skin = False
            self.anim_speed_factor = 1.0
            self.alt_unlocked = False
            self.active_theme = "pink"
            self.unlocked_upgrades = {
                "multiplier": 0,
                "autoclick": 0,
                "animation": 0,
                "skins": 0,
                "theme": 0,
            }
            self.quest_progress = {
                "hits": 0,
                "shops_visited": 0,
                "skins_unlocked": 0,
                "themes_unlocked": 0,
            }
            self.combo_streak = 0
            self.total_hits = 0
            self.last_bonus_time = 0.0

    # ===== текст счёта =====

    def score_text(self):
        best = f"  Best: {self.best_score}" if self.best_score else ""
        return f"Score: {self.score}  (x{self.multiplier:.1f}){best}"

    def update_score_label(self):
        self.score_label.config(text=self.score_text())

    def add_score(self, amount, source=None):
        gained = int(amount * self.multiplier)
        self.score += gained
        self.apply_anti_cheat_limits()
        self.best_score = max(self.best_score, self.score)
        self.update_score_label()
        if source == "hit":
            self.show_status(f"Hit! +{gained}")
        elif source == "combo":
            self.show_status(f"Combo bonus +{gained}")
        elif source == "event":
            self.show_status(f"Случайный бонус +{gained}")

    # ===== события =====

    def on_hit(self):
        self.play_sound("hit")
        self.record_hit()

    def on_key_press(self, event):
        if event.keysym in {"space", "Return"} and event.keysym not in self.active_keys:
            self.active_keys.add(event.keysym)
            self.play_sound("hit")
            self.record_hit()

    def on_key_release(self, event):
        self.active_keys.discard(event.keysym)

    def on_close(self):
        # при выходе сохраняем только защищённый savegame + настройки
        self.save_game_manual()
        self.save_settings()
        self.stop_animation()
        self.auto_click_running = False
        self.destroy()

    # ===== авто-кликер =====

    def start_auto_clicker(self):
        if self.auto_interval_ms and self.auto_interval_ms > 0:
            self.auto_click_running = True
            self.after(self.auto_interval_ms, self.auto_click_tick)

    def auto_click_tick(self):
        if not self.auto_click_running:
            return
        self.add_score(1)
        self.after(self.auto_interval_ms, self.auto_click_tick)

    # ===== магазин =====

    def open_shop(self):
        shop = tk.Toplevel(self)
        shop.title("Shop")
        shop.geometry("360x420+760+120")
        shop.configure(bg="#ffb6c1")

        info = tk.Label(
            shop,
            text=self.shop_info_text(),
            fg="#1b1b2f",
            bg="#ffb6c1",
            font=("Arial", 11),
            justify="left",
        )
        info.pack(pady=10)

        btn_x2 = self.make_button(shop, "Купить x2 множитель (100 Score)", lambda: self.buy_multiplier(shop, info, 2.0, 100), width=26, tooltip_key="buy")
        btn_x2.pack(pady=5)

        btn_x4 = self.make_button(shop, "Купить x4 множитель (250 Score)", lambda: self.buy_multiplier(shop, info, 4.0, 250), width=26, tooltip_key="buy")
        btn_x4.pack(pady=5)

        btn_auto = self.make_button(shop, "Автокликер / ускорение (150 Score)", lambda: self.buy_autoclick(shop, info, 150), width=26, tooltip_key="buy")
        btn_auto.pack(pady=5)

        btn_skin = self.make_button(shop, "Купить ALT скин (200 Score)", lambda: self.buy_skin(shop, info, 200), width=26, tooltip_key="buy")
        btn_skin.pack(pady=5)

        btn_inventory = self.make_button(shop, "Инвентарь скинов", lambda: self.open_skin_inventory(shop, info), width=26, tooltip_key="buy")
        btn_inventory.pack(pady=5)

        btn_theme = self.make_button(shop, "Купить НЕОН тему (500 Score)", lambda: self.buy_theme(shop, info, 500), width=26, tooltip_key="buy")
        btn_theme.pack(pady=5)

        btn_anim = self.make_button(shop, "Ускорить анимацию (x+0.5) (120 Score)", lambda: self.buy_anim_speed(shop, info, 120), width=26, tooltip_key="buy")
        btn_anim.pack(pady=5)

        close_btn = self.make_button(shop, "Закрыть", shop.destroy, width=26, tooltip_key="close")
        close_btn.pack(pady=10)

    def shop_info_text(self):
        return (
            f"Score: {self.score}\n"
            f"Множитель: x{self.multiplier:.1f}\n"
            f"Автокликер: "
            f"{'ON (' + str(self.auto_interval_ms) + ' ms)' if self.auto_interval_ms else 'OFF'}\n"
            f"Скин: {'ALT' if self.use_alt_skin else 'MAIN'}\n"
            f"ALT разблокирован: {'YES' if self.alt_unlocked else 'NO'}\n"
            f"Тема: {self.active_theme.upper()}\n"
            f"Скорость анимации: x{self.anim_speed_factor:.1f}"
        )

    def refresh_shop_info(self, label):
        label.config(text=self.shop_info_text())

    def buy_multiplier(self, shop_window, info_label, factor, cost):
        if self.score >= cost:
            self.score -= cost
            self.multiplier *= factor
            self.apply_anti_cheat_limits()
            self.update_score_label()
            self.save_game_manual()
            self.refresh_shop_info(info_label)
            msg = tk.Label(
                shop_window,
                text=f"Множитель увеличен! Теперь x{self.multiplier:.1f}.",
                fg="#1b1b2f",
                bg="#ffb6c1",
                font=("Arial", 11),
            )
            msg.pack(pady=3)
        else:
            self._not_enough_score(shop_window)

    def buy_autoclick(self, shop_window, info_label, cost):
        if self.score >= cost:
            self.score -= cost
            if not self.auto_interval_ms:
                self.auto_interval_ms = 1000
                self.start_auto_clicker()
            else:
                self.auto_interval_ms = max(MIN_AUTO_INTERVAL, int(self.auto_interval_ms * 0.7))
            self.apply_anti_cheat_limits()
            self.update_score_label()
            self.save_game_manual()
            self.refresh_shop_info(info_label)
            msg = tk.Label(
                shop_window,
                text=f"Автокликер улучшен! Интервал: {self.auto_interval_ms} ms.",
                fg="#1b1b2f",
                bg="#ffb6c1",
                font=("Arial", 11),
            )
            msg.pack(pady=3)
        else:
            self._not_enough_score(shop_window)

    def buy_skin(self, shop_window, info_label, cost):
        if self.alt_unlocked:
            msg = tk.Label(
                shop_window,
                text="ALT уже куплен. Используй инвентарь скинов.",
                fg="#1b1b2f",
                bg="#ffb6c1",
                font=("Arial", 11),
            )
            msg.pack(pady=3)
            return

        if self.score >= cost:
            self.score -= cost
            self.alt_unlocked = True
            self.use_alt_skin = True
            self.restart_animation()
            self.apply_anti_cheat_limits()
            self.update_score_label()
            self.save_game_manual()
            self.refresh_shop_info(info_label)
            msg = tk.Label(
                shop_window,
                text="Скин куплен! ALT теперь навсегда доступен.",
                fg="#1b1b2f",
                bg="#ffb6c1",
                font=("Arial", 11),
            )
            msg.pack(pady=3)
        else:
            self._not_enough_score(shop_window)

    def open_skin_inventory(self, shop_window, info_label):
        inv = tk.Toplevel(shop_window)
        inv.title("Инвентарь скинов")
        inv.geometry("260x220+820+160")
        inv.configure(bg="#ffb6c1")

        title = tk.Label(
            inv,
            text="Выбор скина",
            fg="#1b1b2f",
            bg="#ffb6c1",
            font=("Arial", 14, "bold"),
        )
        title.pack(pady=10)

        btn_main = tk.Button(
            inv,
            text="MAIN",
            fg="white",
            bg="#ff1493",
            activebackground="#ff85c2",
            activeforeground="white",
            relief="raised",
            bd=2,
            font=("Arial", 11, "bold"),
            cursor="hand2",
            command=lambda: self.set_skin(inv, info_label, use_alt=False),
        )
        btn_main.pack(pady=5)

        if self.alt_unlocked:
            btn_alt = tk.Button(
                inv,
                text="ALT",
                fg="white",
                bg="#ff1493",
                activebackground="#ff85c2",
                activeforeground="white",
                relief="raised",
                bd=2,
                font=("Arial", 11, "bold"),
                cursor="hand2",
                command=lambda: self.set_skin(inv, info_label, use_alt=True),
            )
            btn_alt.pack(pady=5)
        else:
            info_alt = tk.Label(
                inv,
                text="ALT ещё не куплен в магазине.",
                fg="#1b1b2f",
                bg="#ffb6c1",
                font=("Arial", 11),
            )
            info_alt.pack(pady=5)

        close_btn = tk.Button(
            inv,
            text="Закрыть",
            command=inv.destroy,
            fg="white",
            bg="#ff1493",
            activebackground="#ff85c2",
            activeforeground="white",
            relief="raised",
            bd=2,
            font=("Arial", 11, "bold"),
            cursor="hand2",
        )
        close_btn.pack(pady=10)

    def set_skin(self, inv_window, info_label, use_alt):
        if use_alt and not self.alt_unlocked:
            inv_window.destroy()
            return

        self.use_alt_skin = use_alt
        self.restart_animation()
        self.apply_anti_cheat_limits()
        self.update_score_label()
        self.save_game_manual()
        self.refresh_shop_info(info_label)
        inv_window.destroy()

    def buy_anim_speed(self, shop_window, info_label, cost):
        if self.score >= cost:
            self.score -= cost
            self.anim_speed_factor += 0.5
            self.unlocked_upgrades["animation"] += 1
            self.apply_anti_cheat_limits()
            self.restart_animation()
            self.update_score_label()
            self.save_game_manual()
            self.refresh_shop_info(info_label)
            msg = tk.Label(
                shop_window,
                text=f"Анимация ускорена! x{self.anim_speed_factor:.1f}.",
                fg=self.theme_color("text"),
                bg=self.theme_color("bg"),
                font=("Arial", 11),
            )
            msg.pack(pady=3)
        else:
            self._not_enough_score(shop_window)

    def _not_enough_score(self, shop_window):
        msg = tk.Label(
            shop_window,
            text="Недостаточно Score.",
            fg=self.theme_color("text"),
            bg=self.theme_color("bg"),
            font=("Arial", 11),
        )
        msg.pack(pady=3)

    def buy_theme(self, shop_window, info_label, cost):
        if self.score >= cost:
            self.score -= cost
            self.active_theme = "neon"
            self.unlocked_upgrades["theme"] += 1
            self.quest_progress["themes_unlocked"] = self.unlocked_upgrades["theme"]
            self.apply_anti_cheat_limits()
            self.save_game_manual()
            self.update_score_label()
            self.refresh_shop_info(info_label)
            self.show_status("Тема НЕОН куплена и применена!")
        else:
            self._not_enough_score(shop_window)

    def open_achievements(self):
        ach_win = tk.Toplevel(self)
        ach_win.title("Задания")
        ach_win.geometry("360x340+760+140")
        ach_win.configure(bg=self.theme_color("bg"))

        title = tk.Label(
            ach_win,
            text="Задания и достижения",
            fg=self.theme_color("text"),
            bg=self.theme_color("bg"),
            font=("Arial", 16, "bold"),
        )
        title.pack(pady=10)

        achievements = [
            ("Первый удар", self.quest_progress.get("first_hit", False)),
            ("100 ударов", self.quest_progress.get("century_hits", False)),
            ("1000 Score", self.quest_progress.get("silver_score", False)),
            ("ALT Skin", self.quest_progress.get("alt_skin", False)),
        ]

        for text, unlocked in achievements:
            label = tk.Label(
                ach_win,
                text=f"{text}: {'✓' if unlocked else '✗'}",
                fg=self.theme_color("text"),
                bg=self.theme_color("bg"),
                font=("Arial", 12),
                anchor="w",
                justify="left",
            )
            label.pack(fill=tk.X, padx=16, pady=4)

        close_btn = self.make_button(ach_win, "Закрыть", ach_win.destroy, width=24)
        close_btn.pack(pady=16)

    def open_theme_picker(self):
        theme_win = tk.Toplevel(self)
        theme_win.title("Выбор темы")
        theme_win.geometry("320x260+780+160")
        theme_win.configure(bg=self.theme_color("bg"))

        title = tk.Label(
            theme_win,
            text="Выберите тему",
            fg=self.theme_color("text"),
            bg=self.theme_color("bg"),
            font=("Arial", 16, "bold"),
        )
        title.pack(pady=10)

        for theme_name in THEMES:
            btn = self.make_button(
                theme_win,
                theme_name.upper(),
                lambda name=theme_name: self.apply_theme_choice(theme_win, name),
                width=24,
            )
            btn.pack(pady=5)

        close_btn = self.make_button(theme_win, "Закрыть", theme_win.destroy, width=24)
        close_btn.pack(pady=12)

    # ===== окно настроек =====

    def open_settings(self):
        settings_win = tk.Toplevel(self)
        settings_win.title("Настройки")
        settings_win.geometry("320x300+820+180")
        settings_win.configure(bg=self.theme_color("bg"))

        title = tk.Label(
            settings_win,
            text="Настройки",
            fg=self.theme_color("text"),
            bg=self.theme_color("bg"),
            font=("Arial", 16, "bold"),
        )
        title.pack(pady=10)

        subtitle = tk.Label(
            settings_win,
            text="Разрешение окна",
            fg=self.theme_color("text"),
            bg=self.theme_color("bg"),
            font=("Arial", 12),
        )
        subtitle.pack(pady=(0, 6))

        resolutions = [
            ("1024 x 768", 1024, 768),
            ("1280 x 800", 1280, 800),
            ("1366 x 768", 1366, 768),
            ("1440 x 900", 1440, 900),
            ("1600 x 900", 1600, 900),
            ("1920 x 1080", 1920, 1080),
            ("Полноэкранный", self.screen_width, self.screen_height),
        ]

        for text, w, h in resolutions:
            if w > self.screen_width or h > self.screen_height:
                continue
            btn = self.make_button(settings_win, text, lambda width=w, height=h: self.apply_resolution(settings_win, width, height), width=22)
            btn.pack(pady=4)

        theme_label = tk.Label(
            settings_win,
            text="Тема интерфейса",
            fg=self.theme_color("text"),
            bg=self.theme_color("bg"),
            font=("Arial", 12),
        )
        theme_label.pack(pady=(14, 6))

        for theme_name in THEMES:
            btn = self.make_button(
                settings_win,
                theme_name.upper(),
                lambda name=theme_name: self.apply_theme_choice(settings_win, name),
                width=22,
            )
            btn.pack(pady=4)

        label_options = tk.Label(
            settings_win,
            text="Дополнительные опции",
            fg=self.theme_color("text"),
            bg=self.theme_color("bg"),
            font=("Arial", 12),
        )
        label_options.pack(pady=(12, 4))

        sound_var = tk.BooleanVar(value=self.sound_enabled)
        sound_checkbox = tk.Checkbutton(
            settings_win,
            text="Включить звук",
            variable=sound_var,
            command=lambda: self.set_sound_option(sound_var.get()),
            fg=self.theme_color("text"),
            bg=self.theme_color("bg"),
            selectcolor=self.theme_color("panel"),
            activebackground=self.theme_color("bg"),
            highlightthickness=0,
            bd=0,
        )
        sound_checkbox.pack(anchor="w", padx=20, pady=2)

        autosave_var = tk.BooleanVar(value=self.auto_save_enabled)
        autosave_checkbox = tk.Checkbutton(
            settings_win,
            text="Автосохранение",
            variable=autosave_var,
            command=lambda: self.set_autosave_option(autosave_var.get()),
            fg=self.theme_color("text"),
            bg=self.theme_color("bg"),
            selectcolor=self.theme_color("panel"),
            activebackground=self.theme_color("bg"),
            highlightthickness=0,
            bd=0,
        )
        autosave_checkbox.pack(anchor="w", padx=20, pady=2)

        fullscreen_var = tk.BooleanVar(value=self.fullscreen)
        fullscreen_checkbox = tk.Checkbutton(
            settings_win,
            text="Полноэкранный режим",
            variable=fullscreen_var,
            command=lambda: self.set_fullscreen_option(fullscreen_var.get()),
            fg=self.theme_color("text"),
            bg=self.theme_color("bg"),
            selectcolor=self.theme_color("panel"),
            activebackground=self.theme_color("bg"),
            highlightthickness=0,
            bd=0,
        )
        fullscreen_checkbox.pack(anchor="w", padx=20, pady=2)

        close_btn = self.make_button(settings_win, "Закрыть", settings_win.destroy, width=22)
        close_btn.pack(pady=12)

    def apply_resolution(self, settings_win, width, height):
        self.window_width = width
        self.window_height = height
        self.fullscreen = False
        self.set_geometry(width, height)
        self.save_settings()
        settings_win.destroy()

    def apply_theme_choice(self, settings_win, theme_name):
        if theme_name in THEMES:
            self.active_theme = theme_name
            self.theme = theme_name
            self.set_geometry(self.window_width, self.window_height)
            self.save_settings()
            settings_win.destroy()
            self.show_status(f"Тема применена: {theme_name.upper()}")

    def set_sound_option(self, enabled):
        self.sound_enabled = bool(enabled)
        self.save_settings()
        self.show_status("Звук включён" if self.sound_enabled else "Звук выключен")

    def set_autosave_option(self, enabled):
        self.auto_save_enabled = bool(enabled)
        self.save_settings()
        self.show_status("Автосохранение включено" if self.auto_save_enabled else "Автосохранение отключено")

    def set_fullscreen_option(self, enabled):
        self.fullscreen = bool(enabled)
        self.set_geometry(self.window_width, self.window_height)
        self.save_settings()
        self.show_status("Полноэкранный режим включён" if self.fullscreen else "Оконный режим")


if __name__ == "__main__":
    app = ZeroTwoGame()
    app.mainloop()