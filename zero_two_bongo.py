import tkinter as tk
from PIL import Image, ImageTk
from itertools import count
import os
import json

MAIN_GIF = "zero_two.gif"
ALT_GIF = "zero_two_alt.gif"

SCORE_FILE = "score.txt"
UPGRADE_FILE = "upgrades.txt"
SAVEGAME_FILE = "savegame.txt"
SETTINGS_FILE = "settings.txt"


class ZeroTwoGame(tk.Tk):
    def __init__(self):
        super().__init__()

        # настройки окна по умолчанию
        self.default_width = 640
        self.default_height = 640

        # загрузка настроек (разрешение)
        self.window_width, self.window_height = self.load_settings()

        self.title("Zero Two Bongo")
        self.set_geometry(self.window_width, self.window_height)

        # состояние игры
        self.score = self.load_score()
        (
            self.multiplier,
            self.auto_interval_ms,
            self.use_alt_skin,
            self.anim_speed_factor,
            self.alt_unlocked,
        ) = self.load_upgrades()

        self.current_frame = None

        # флаги процессов
        self.animation_running = False
        self.auto_click_running = False

        self.create_start_screen()

    # ===== работа с окном / настройками =====

    def set_geometry(self, w, h):
        # фиксируем размер окна
        self.geometry(f"{w}x{h}+100+100")
        self.minsize(w, h)
        self.maxsize(w, h)
        self.configure(bg="#ffb6c1")

    def load_settings(self):
        # формат settings.txt: JSON с {"width": int, "height": int}
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    w = int(data.get("width", self.default_width))
                    h = int(data.get("height", self.default_height))
                    return w, h
            except Exception:
                return self.default_width, self.default_height
        return self.default_width, self.default_height

    def save_settings(self):
        data = {"width": self.window_width, "height": self.window_height}
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f)
        except Exception:
            pass

    # ===== стартовый экран =====

    def create_start_screen(self):
        self._switch_frame(bg="#ffb6c1")

        title = tk.Label(
            self.current_frame,
            text="Zero Two Bongo",
            fg="#1b1b2f",
            bg="#ffb6c1",
            font=("Arial", 26, "bold"),
        )
        title.pack(pady=40)

        play_button = tk.Button(
            self.current_frame,
            text="Играть",
            command=self.start_game,
            fg="white",
            bg="#ff1493",
            activebackground="#ff85c2",
            activeforeground="white",
            relief="raised",
            bd=3,
            font=("Arial", 18, "bold"),
            cursor="hand2",
            padx=40,
            pady=10,
        )
        play_button.pack(pady=10)

        dev_button = tk.Button(
            self.current_frame,
            text="Разработчики",
            command=self.show_devs,
            fg="white",
            bg="#ff1493",
            activebackground="#ff85c2",
            activeforeground="white",
            relief="raised",
            bd=3,
            font=("Arial", 18, "bold"),
            cursor="hand2",
            padx=40,
            pady=10,
        )
        dev_button.pack(pady=10)

        exit_button = tk.Button(
            self.current_frame,
            text="Выход",
            command=self.quit_game,
            fg="white",
            bg="#ff1493",
            activebackground="#ff85c2",
            activeforeground="white",
            relief="raised",
            bd=3,
            font=("Arial", 18, "bold"),
            cursor="hand2",
            padx=40,
            pady=10,
        )
        exit_button.pack(pady=10)

    def show_devs(self):
        self._switch_frame(bg="#ffb6c1")

        label = tk.Label(
            self.current_frame,
            text="Главный разработчик - qwisixe",
            fg="red",
            bg="#ffb6c1",
            font=("Arial", 22, "bold"),
        )
        label.pack(expand=True)

        back_button = tk.Button(
            self.current_frame,
            text="Назад",
            command=self.create_start_screen,
            fg="white",
            bg="#ff1493",
            activebackground="#ff85c2",
            activeforeground="white",
            relief="raised",
            bd=3,
            font=("Arial", 14, "bold"),
            cursor="hand2",
            padx=20,
            pady=5,
        )
        back_button.pack(pady=20)

    def quit_game(self):
        self.on_close()

    # ===== запуск игры =====

    def start_game(self):
        # при входе в игру сброс флагов
        self.animation_running = False
        self.auto_click_running = False

        self._switch_frame(bg="#1b1b2f")

        self.image_label = tk.Label(self.current_frame, bg="#1b1b2f")
        self.image_label.pack(expand=True, fill=tk.BOTH)

        # нижняя панель
        self.panel = tk.Frame(self.current_frame, bg="#ff69b4", height=80)
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
            fg="white",
            bg="#ff69b4",
            font=("Arial", 14, "bold"),
        )
        self.score_label.pack(side=tk.LEFT, padx=10)

        # Shop
        self.shop_button = tk.Button(
            self.panel,
            text="Shop",
            command=self.open_shop,
            fg="#1b1b2f",
            bg="#ffc0cb",
            activebackground="#ffdde8",
            activeforeground="#1b1b2f",
            relief="ridge",
            bd=2,
            font=("Arial", 12, "bold"),
            cursor="hand2",
            padx=10,
            pady=3,
        )
        self.shop_button.pack(side=tk.LEFT, padx=5)

        # кнопка Сохранить
        self.save_button = tk.Button(
            self.panel,
            text="Сохранить",
            command=self.save_game_manual,
            fg="#1b1b2f",
            bg="#ffe4f2",
            activebackground="#ffd0ec",
            activeforeground="#1b1b2f",
            relief="ridge",
            bd=2,
            font=("Arial", 11, "bold"),
            cursor="hand2",
            padx=8,
            pady=3,
        )
        self.save_button.pack(side=tk.LEFT, padx=5)

        # кнопка Настройки (⚙)
        self.settings_button = tk.Button(
            self.panel,
            text="⚙",
            command=self.open_settings,
            fg="#1b1b2f",
            bg="#ffc0cb",
            activebackground="#ffdde8",
            activeforeground="#1b1b2f",
            relief="ridge",
            bd=2,
            font=("Arial", 12, "bold"),
            cursor="hand2",
            padx=6,
            pady=2,
            width=3,
        )
        self.settings_button.pack(side=tk.LEFT, padx=5)

        # Меню
        self.menu_button = tk.Button(
            self.panel,
            text="Меню",
            command=self.back_to_menu,
            fg="white",
            bg="#ff1493",
            activebackground="#ff85c2",
            activeforeground="white",
            relief="raised",
            bd=2,
            font=("Arial", 12, "bold"),
            cursor="hand2",
            padx=10,
            pady=3,
        )
        self.menu_button.pack(side=tk.LEFT, padx=5)

        # Hit
        self.hit_button = tk.Button(
            self.panel,
            text="Hit!",
            command=self.on_hit,
            fg="white",
            bg="#ff1493",
            activebackground="#ff85c2",
            activeforeground="white",
            relief="raised",
            bd=3,
            font=("Arial", 14, "bold"),
            cursor="hand2",
            padx=20,
            pady=5,
        )
        self.hit_button.pack(side=tk.RIGHT, padx=10)

        self.bind("<KeyPress>", self.on_key_press)

        # авто-кликер
        self.start_auto_clicker()

        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def back_to_menu(self):
        # при выходе в меню сохраняем прогресс
        self.save_score()
        self.save_upgrades()
        self.animation_running = False
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
        # выбор GIF по флагу use_alt_skin и наличию файла
        if self.use_alt_skin and os.path.exists(ALT_GIF):
            gif_path = ALT_GIF
            alt_mode = True
        else:
            gif_path = MAIN_GIF
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

        # используем текущий множитель, но его не меняем
        speed_factor = self.anim_speed_factor
        if alt_mode:
            speed_factor *= 1.5  # ALT чуть быстрее, но фиксированный коэффициент

        self.base_delay = max(0.02, base_delay / speed_factor)

    def restart_animation(self):
        # аккуратный перезапуск анимации при смене скина/скорости
        self.animation_running = False
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
        self.after(delay_ms, self.animate)

    # ===== сохранение / загрузка базовых файлов =====

    def load_score(self):
        if os.path.exists(SCORE_FILE):
            try:
                with open(SCORE_FILE, "r", encoding="utf-8") as f:
                    val = f.read().strip()
                    if val:
                        return int(val)
            except Exception:
                return 0
        return 0

    def save_score(self):
        try:
            with open(SCORE_FILE, "w", encoding="utf-8") as f:
                f.write(str(self.score))
        except Exception:
            pass

    def load_upgrades(self):
        # множитель, автоклик, текущий скин, скорость анимации, флаг "ALT куплен"
        default = (1.0, 0, False, 1.0, False)
        if os.path.exists(UPGRADE_FILE):
            try:
                with open(UPGRADE_FILE, "r", encoding="utf-8") as f:
                    line = f.read().strip()
                    if line:
                        parts = line.split(";")
                        mult = float(parts[0])
                        auto_ms = int(parts[1])
                        use_alt = parts[2] == "1"
                        anim_speed = float(parts[3])
                        alt_unlocked = parts[4] == "1" if len(parts) > 4 else False
                        return mult, auto_ms, use_alt, anim_speed, alt_unlocked
            except Exception:
                return default
        return default

    def save_upgrades(self):
        try:
            with open(UPGRADE_FILE, "w", encoding="utf-8") as f:
                use_alt_flag = "1" if self.use_alt_skin else "0"
                alt_unlocked_flag = "1" if self.alt_unlocked else "0"
                f.write(
                    f"{self.multiplier};{self.auto_interval_ms};"
                    f"{use_alt_flag};{self.anim_speed_factor};{alt_unlocked_flag}"
                )
        except Exception:
            pass

    # ===== ручная система сохранений =====

    def save_game_manual(self):
        # сохраняем всё важное состояние одной JSON-структурой [web:225][web:228]
        data = {
            "score": self.score,
            "multiplier": self.multiplier,
            "auto_interval_ms": self.auto_interval_ms,
            "use_alt_skin": self.use_alt_skin,
            "anim_speed_factor": self.anim_speed_factor,
            "alt_unlocked": self.alt_unlocked,
        }
        try:
            with open(SAVEGAME_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f)
        except Exception:
            pass

        # маленькое уведомление внизу панели
        info = tk.Label(
            self.panel,
            text="Игра сохранена",
            fg="#1b1b2f",
            bg="#ff69b4",
            font=("Arial", 10, "bold"),
        )
        info.pack(side=tk.LEFT, padx=5)
        # убрать уведомление через пару секунд
        self.after(2000, info.destroy)

    def load_game_manual(self):
        # можно вызвать на старте игры, если захочешь автозагрузку
        if os.path.exists(SAVEGAME_FILE):
            try:
                with open(SAVEGAME_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.score = int(data.get("score", self.score))
                self.multiplier = float(data.get("multiplier", self.multiplier))
                self.auto_interval_ms = int(data.get("auto_interval_ms", self.auto_interval_ms))
                self.use_alt_skin = bool(data.get("use_alt_skin", self.use_alt_skin))
                self.anim_speed_factor = float(data.get("anim_speed_factor", self.anim_speed_factor))
                self.alt_unlocked = bool(data.get("alt_unlocked", self.alt_unlocked))
            except Exception:
                pass

    # ===== текст счёта =====

    def score_text(self):
        return f"Score: {self.score}  (x{self.multiplier:.1f})"

    def update_score_label(self):
        self.score_label.config(text=self.score_text())

    def add_score(self, amount):
        gained = int(amount * self.multiplier)
        self.score += gained
        self.update_score_label()

    # ===== события =====

    def on_hit(self):
        self.add_score(1)

    def on_key_press(self, event):
        self.add_score(1)

    def on_close(self):
        # при выходе сохраняем прогресс и настройки
        self.save_score()
        self.save_upgrades()
        self.save_settings()
        self.animation_running = False
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

        btn_x2 = tk.Button(
            shop,
            text="Купить x2 множитель (100 Score)",
            fg="white",
            bg="#ff1493",
            activebackground="#ff85c2",
            activeforeground="white",
            relief="raised",
            bd=2,
            font=("Arial", 11, "bold"),
            cursor="hand2",
            command=lambda: self.buy_multiplier(shop, info, 2.0, 100),
        )
        btn_x2.pack(pady=5)

        btn_x4 = tk.Button(
            shop,
            text="Купить x4 множитель (250 Score)",
            fg="white",
            bg="#ff1493",
            activebackground="#ff85c2",
            activeforeground="white",
            relief="raised",
            bd=2,
            font=("Arial", 11, "bold"),
            cursor="hand2",
            command=lambda: self.buy_multiplier(shop, info, 4.0, 250),
        )
        btn_x4.pack(pady=5)

        btn_auto = tk.Button(
            shop,
            text="Автокликер / ускорение (150 Score)",
            fg="white",
            bg="#ff1493",
            activebackground="#ff85c2",
            activeforeground="white",
            relief="raised",
            bd=2,
            font=("Arial", 11, "bold"),
            cursor="hand2",
            command=lambda: self.buy_autoclick(shop, info, 150),
        )
        btn_auto.pack(pady=5)

        btn_skin = tk.Button(
            shop,
            text="Купить ALT скин (200 Score)",
            fg="white",
            bg="#ff1493",
            activebackground="#ff85c2",
            activeforeground="white",
            relief="raised",
            bd=2,
            font=("Arial", 11, "bold"),
            cursor="hand2",
            command=lambda: self.buy_skin(shop, info, 200),
        )
        btn_skin.pack(pady=5)

        btn_inventory = tk.Button(
            shop,
            text="Инвентарь скинов",
            fg="white",
            bg="#ff1493",
            activebackground="#ff85c2",
            activeforeground="white",
            relief="raised",
            bd=2,
            font=("Arial", 11, "bold"),
            cursor="hand2",
            command=lambda: self.open_skin_inventory(shop, info),
        )
        btn_inventory.pack(pady=5)

        btn_anim = tk.Button(
            shop,
            text="Ускорить анимацию (x+0.5) (120 Score)",
            fg="white",
            bg="#ff1493",
            activebackground="#ff85c2",
            activeforeground="white",
            relief="raised",
            bd=2,
            font=("Arial", 11, "bold"),
            cursor="hand2",
            command=lambda: self.buy_anim_speed(shop, info, 120),
        )
        btn_anim.pack(pady=5)

        close_btn = tk.Button(
            shop,
            text="Закрыть",
            command=shop.destroy,
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

    def shop_info_text(self):
        return (
            f"Score: {self.score}\n"
            f"Множитель: x{self.multiplier:.1f}\n"
            f"Автокликер: "
            f"{'ON (' + str(self.auto_interval_ms) + ' ms)' if self.auto_interval_ms else 'OFF'}\n"
            f"Скин сейчас: {'ALT' if self.use_alt_skin else 'MAIN'}\n"
            f"ALT разблокирован: {'YES' if self.alt_unlocked else 'NO'}\n"
            f"Скорость анимации: x{self.anim_speed_factor:.1f}"
        )

    def refresh_shop_info(self, label):
        label.config(text=self.shop_info_text())

    def buy_multiplier(self, shop_window, info_label, factor, cost):
        if self.score >= cost:
            self.score -= cost
            self.multiplier *= factor
            self.update_score_label()
            self.save_score()
            self.save_upgrades()
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
                self.auto_interval_ms = max(200, int(self.auto_interval_ms * 0.7))
            self.update_score_label()
            self.save_score()
            self.save_upgrades()
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
        # покупка ALT‑скина навсегда
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
            self.use_alt_skin = True  # сразу включаем ALT
            self.restart_animation()
            self.update_score_label()
            self.save_score()
            self.save_upgrades()
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

        # ALT доступен только если куплен
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
        # выбор скина без затрат очков (если ALT куплен)
        if use_alt and not self.alt_unlocked:
            inv_window.destroy()
            return

        self.use_alt_skin = use_alt
        self.restart_animation()
        self.update_score_label()
        self.save_upgrades()
        self.refresh_shop_info(info_label)
        inv_window.destroy()

    def buy_anim_speed(self, shop_window, info_label, cost):
        if self.score >= cost:
            self.score -= cost
            # плавное увеличение скорости вместо бесконечного умножения
            self.anim_speed_factor += 0.5
            self.restart_animation()
            self.update_score_label()
            self.save_score()
            self.save_upgrades()
            self.refresh_shop_info(info_label)
            msg = tk.Label(
                shop_window,
                text=f"Анимация ускорена! x{self.anim_speed_factor:.1f}.",
                fg="#1b1b2f",
                bg="#ffb6c1",
                font=("Arial", 11),
            )
            msg.pack(pady=3)
        else:
            self._not_enough_score(shop_window)

    def _not_enough_score(self, shop_window):
        msg = tk.Label(
            shop_window,
            text="Недостаточно Score.",
            fg="#1b1b2f",
            bg="#ffb6c1",
            font=("Arial", 11),
        )
        msg.pack(pady=3)

    # ===== окно настроек =====

    def open_settings(self):
        settings_win = tk.Toplevel(self)
        settings_win.title("Настройки")
        settings_win.geometry("260x220+820+180")
        settings_win.configure(bg="#ffb6c1")

        title = tk.Label(
            settings_win,
            text="Разрешение окна",
            fg="#1b1b2f",
            bg="#ffb6c1",
            font=("Arial", 14, "bold"),
        )
        title.pack(pady=10)

        # варианты разрешений
        resolutions = [
            ("640 x 640", 640, 640),
            ("800 x 600", 800, 600),
            ("1024 x 768", 1024, 768),
        ]

        for text, w, h in resolutions:
            btn = tk.Button(
                settings_win,
                text=text,
                fg="white",
                bg="#ff1493",
                activebackground="#ff85c2",
                activeforeground="white",
                relief="raised",
                bd=2,
                font=("Arial", 11, "bold"),
                cursor="hand2",
                command=lambda width=w, height=h: self.apply_resolution(settings_win, width, height),
            )
            btn.pack(pady=5)

        close_btn = tk.Button(
            settings_win,
            text="Закрыть",
            command=settings_win.destroy,
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

    def apply_resolution(self, settings_win, width, height):
        # применяем новое разрешение и сохраняем в settings.txt [web:106][web:102]
        self.window_width = width
        self.window_height = height
        self.set_geometry(width, height)
        self.save_settings()
        settings_win.destroy()


if __name__ == "__main__":
    app = ZeroTwoGame()
    app.mainloop()