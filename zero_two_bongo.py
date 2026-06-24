import tkinter as tk
from PIL import Image, ImageTk
from itertools import count
import os

# === файлы ===
MAIN_GIF = "zero_two.gif"       # основной GIF Zero Two
ALT_GIF = "zero_two_alt.gif"    # альтернативный GIF для прокачки
SCORE_FILE = "score.txt"
UPGRADE_FILE = "upgrades.txt"   # сюда сохраняем множитель и апгрейды


# ======== класс игры ========

class ZeroTwoGame(tk.Tk):
    def __init__(self):
        super().__init__()

        # окно
        self.title("Zero Two Bongo")
        self.geometry("640x640+100+100")
        self.minsize(640, 640)
        self.maxsize(640, 640)
        self.configure(bg="#ffb6c1")  # розовый фон стартового экрана [web:123][web:127]

        # состояние апгрейдов
        self.score = self.load_score()
        self.multiplier, self.auto_interval_ms, self.use_alt_skin, self.anim_speed_factor = self.load_upgrades()

        # флаг: сейчас стартовый экран или игра
        self.current_frame = None

        # создаём стартовый экран
        self.create_start_screen()

    # ======== стартовый экран ========

    def create_start_screen(self):
        if self.current_frame:
            self.current_frame.destroy()

        frame = tk.Frame(self, bg="#ffb6c1")
        frame.pack(fill=tk.BOTH, expand=True)
        self.current_frame = frame

        title = tk.Label(
            frame,
            text="Zero Two Bongo",
            fg="#1b1b2f",
            bg="#ffb6c1",
            font=("Arial", 26, "bold"),
        )
        title.pack(pady=60)

        play_button = tk.Button(
            frame,
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
        play_button.pack(pady=20)

        dev_button = tk.Button(
            frame,
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
        dev_button.pack(pady=20)

    def show_devs(self):
        if self.current_frame:
            self.current_frame.destroy()

        frame = tk.Frame(self, bg="#ffb6c1")
        frame.pack(fill=tk.BOTH, expand=True)
        self.current_frame = frame

        label = tk.Label(
            frame,
            text="Главный разработчик - qwisixe",
            fg="red",
            bg="#ffb6c1",
            font=("Arial", 22, "bold"),
        )
        label.pack(expand=True)

        back_button = tk.Button(
            frame,
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

    # ======== запуск самой игры ========

    def start_game(self):
        if self.current_frame:
            self.current_frame.destroy()

        game_frame = tk.Frame(self, bg="#1b1b2f")
        game_frame.pack(fill=tk.BOTH, expand=True)
        self.current_frame = game_frame

        # верхняя часть — GIF Zero Two
        self.image_label = tk.Label(game_frame, bg="#1b1b2f")
        self.image_label.pack(expand=True, fill=tk.BOTH)

        # розовая панель снизу
        self.panel = tk.Frame(game_frame, bg="#ff69b4", height=80)
        self.panel.pack(fill=tk.X, side=tk.BOTTOM)

        # загрузка GIF по текущему скину
        self.load_gif_frames()

        # счёт + множитель
        self.score_label = tk.Label(
            self.panel,
            text=self.score_text(),
            fg="white",
            bg="#ff69b4",
            font=("Arial", 14, "bold"),
        )
        self.score_label.pack(side=tk.LEFT, padx=10)

        # кнопка Hit
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

        # кнопка-магазин
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
        self.shop_button.pack(side=tk.LEFT, padx=10)

        # бинды клавиш
        self.bind("<KeyPress>", self.on_key_press)

        # авто-кликер и анимация
        self.auto_click_running = False
        self.current_frame_index = 0
        self.animate()
        self.start_auto_clicker()

        # при закрытии — сохраняем
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    # ======== GIF ========

    def load_gif_frames(self):
        gif_path = ALT_GIF if self.use_alt_skin and os.path.exists(ALT_GIF) else MAIN_GIF
        try:
            pil_image = Image.open(gif_path)
        except Exception as e:
            raise RuntimeError(f"Не удалось открыть GIF {gif_path}: {e}")

        self.frames = []
        try:
            for i in count(0):
                pil_image.seek(i)
                frame = pil_image.copy().resize((400, 400))
                self.frames.append(ImageTk.PhotoImage(frame))
        except EOFError:
            pass

        if not self.frames:
            raise RuntimeError("GIF не содержит кадров или не поддерживается.")

        base_delay = pil_image.info.get("duration", 100) / 1000.0
        # учитываем ускорение анимации от прокачки
        self.base_delay = max(0.03, base_delay / self.anim_speed_factor)

    def animate(self):
        if not hasattr(self, "frames"):
            return
        self.image_label.config(image=self.frames[self.current_frame_index])
        self.current_frame_index = (self.current_frame_index + 1) % len(self.frames)
        delay_ms = int(self.base_delay * 1000)
        self.after(delay_ms, self.animate)

    # ======== счёт / сохранение ========

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
        # по умолчанию: множитель 1x, автокликер выключен (0 = нет),
        # основной скин, скорость анимации 1x
        default = (1.0, 0, False, 1.0)
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
                        return mult, auto_ms, use_alt, anim_speed
            except Exception:
                return default
        return default

    def save_upgrades(self):
        try:
            with open(UPGRADE_FILE, "w", encoding="utf-8") as f:
                use_alt_flag = "1" if self.use_alt_skin else "0"
                f.write(f"{self.multiplier};{self.auto_interval_ms};{use_alt_flag};{self.anim_speed_factor}")
        except Exception:
            pass

    def score_text(self):
        return f"Score: {self.score}  (x{self.multiplier:.1f})"

    def update_score_label(self):
        self.score_label.config(text=self.score_text())

    def add_score(self, amount):
        gained = int(amount * self.multiplier)
        self.score += gained
        self.update_score_label()

    # ======== события ========

    def on_hit(self):
        self.add_score(1)

    def on_key_press(self, event):
        self.add_score(1)

    def on_close(self):
        self.save_score()
        self.save_upgrades()
        self.destroy()

    # ======== авто-кликер ========

    def start_auto_clicker(self):
        if self.auto_interval_ms and self.auto_interval_ms > 0:
            self.auto_click_running = True
            self.after(self.auto_interval_ms, self.auto_click_tick)

    def auto_click_tick(self):
        if not self.auto_click_running:
            return
        # авто-кликер реально добавляет очки
        self.add_score(1)
        self.after(self.auto_interval_ms, self.auto_click_tick)

    # ======== магазин ========

    def open_shop(self):
        shop = tk.Toplevel(self)
        shop.title("Shop")
        shop.geometry("340x360+760+120")
        shop.configure(bg="#ffb6c1")

        title = tk.Label(
            shop,
            text="Zero Two Shop",
            fg="#1b1b2f",
            bg="#ffb6c1",
            font=("Arial", 16, "bold"),
        )
        title.pack(pady=10)

        info = tk.Label(
            shop,
            text=(
                f"Score: {self.score}\n"
                f"Множитель: x{self.multiplier:.1f}\n"
                f"Автокликер: "
                f"{'ON (' + str(self.auto_interval_ms) + ' ms)' if self.auto_interval_ms else 'OFF'}\n"
                f"Скин: {'ALT' if self.use_alt_skin else 'MAIN'}\n"
                f"Скорость анимации: x{self.anim_speed_factor:.1f}"
            ),
            fg="#1b1b2f",
            bg="#ffb6c1",
            font=("Arial", 11),
            justify="left",
        )
        info.pack(pady=10)

        # x2 множитель
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

        # x4 множитель
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

        # автокликер (включение или ускорение)
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

        # смена GIF-скина
        btn_skin = tk.Button(
            shop,
            text="Сменить скин (Zero Two ALT) (200 Score)",
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

        # ускорение анимации
        btn_anim = tk.Button(
            shop,
            text="Ускорить анимацию (x1.5) (120 Score)",
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

    def refresh_shop_info(self, label):
        label.config(
            text=(
                f"Score: {self.score}\n"
                f"Множитель: x{self.multiplier:.1f}\n"
                f"Автокликер: "
                f"{'ON (' + str(self.auto_interval_ms) + ' ms)' if self.auto_interval_ms else 'OFF'}\n"
                f"Скин: {'ALT' if self.use_alt_skin else 'MAIN'}\n"
                f"Скорость анимации: x{self.anim_speed_factor:.1f}"
            )
        )

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
            msg = tk.Label(
                shop_window,
                text="Недостаточно Score.",
                fg="#1b1b2f",
                bg="#ffb6c1",
                font=("Arial", 11),
            )
            msg.pack(pady=3)

    def buy_autoclick(self, shop_window, info_label, cost):
        if self.score >= cost:
            self.score -= cost
            # если автокликера нет, включаем с интервалом 1000 мс
            if not self.auto_interval_ms:
                self.auto_interval_ms = 1000
                self.start_auto_clicker()
            else:
                # ускоряем автокликер (уменьшаем интервал)
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
            msg = tk.Label(
                shop_window,
                text="Недостаточно Score.",
                fg="#1b1b2f",
                bg="#ffb6c1",
                font=("Arial", 11),
            )
            msg.pack(pady=3)

    def buy_skin(self, shop_window, info_label, cost):
        if self.score >= cost:
            self.score -= cost
            self.use_alt_skin = True
            # перезагружаем кадры GIF
            self.load_gif_frames()
            self.update_score_label()
            self.save_score()
            self.save_upgrades()
            self.refresh_shop_info(info_label)
            msg = tk.Label(
                shop_window,
                text="Скин сменён! Теперь используется ALT GIF.",
                fg="#1b1b2f",
                bg="#ffb6c1",
                font=("Arial", 11),
            )
            msg.pack(pady=3)
        else:
            msg = tk.Label(
                shop_window,
                text="Недостаточно Score.",
                fg="#1b1b2f",
                bg="#ffb6c1",
                font=("Arial", 11),
            )
            msg.pack(pady=3)

    def buy_anim_speed(self, shop_window, info_label, cost):
        if self.score >= cost:
            self.score -= cost
            self.anim_speed_factor *= 1.5
            # перезагружаем GIF с новой скоростью
            self.load_gif_frames()
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
            msg = tk.Label(
                shop_window,
                text="Недостаточно Score.",
                fg="#1b1b2f",
                bg="#ffb6c1",
                font=("Arial", 11),
            )
            msg.pack(pady=3)


if __name__ == "__main__":
    app = ZeroTwoGame()
    app.mainloop()