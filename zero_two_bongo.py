import tkinter as tk
from PIL import Image, ImageTk
from itertools import count
import os

GIF_PATH = "zero_two.gif"   # гифка Zero Two рядом со скриптом
SCORE_FILE = "score.txt"    # файл для сохранения очков
UPGRADE_FILE = "upgrades.txt"  # файл для сохранения улучшений

class ZeroTwoBongo(tk.Tk):
    def __init__(self):
        super().__init__()

        # окно
        self.title("Zero Two Bongo")
        self.geometry("640x640+100+100")
        self.minsize(640, 640)
        self.maxsize(640, 640)
        self.configure(bg="#1b1b2f")

        # загружаем сохранённый счёт и улучшения
        self.score = self.load_score()
        self.multiplier = self.load_multiplier()  # множитель очков

        # === GIF Zero Two ===
        try:
            pil_image = Image.open(GIF_PATH)
        except Exception as e:
            raise RuntimeError(f"Не удалось открыть GIF {GIF_PATH}: {e}")

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

        self.base_delay = pil_image.info.get("duration", 100) / 1000.0
        self.current_delay = self.base_delay
        self.current_frame_index = 0

        self.image_label = tk.Label(self, bg="#1b1b2f")
        self.image_label.pack(expand=True, fill=tk.BOTH)

        # === Розовая панель ===
        self.panel = tk.Frame(self, bg="#ff69b4", height=80)
        self.panel.pack(fill=tk.X, side=tk.BOTTOM)

        # счёт (стоит на месте)
        self.score_label = tk.Label(
            self.panel,
            text=self.score_text(),
            fg="white",
            bg="#ff69b4",
            font=("Arial", 14, "bold"),
        )
        self.score_label.pack(side=tk.LEFT, padx=10)

        # кнопка "Hit!"
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

        # анимация GIF
        self.animate()

        # сохраняем всё при закрытии
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    # ====== сохранение / загрузка ======

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

    def load_multiplier(self):
        # множитель улучшений (по умолчанию 1.0)
        if os.path.exists(UPGRADE_FILE):
            try:
                with open(UPGRADE_FILE, "r", encoding="utf-8") as f:
                    val = f.read().strip()
                    if val:
                        return float(val)
            except Exception:
                return 1.0
        return 1.0

    def save_multiplier(self):
        try:
            with open(UPGRADE_FILE, "w", encoding="utf-8") as f:
                f.write(str(self.multiplier))
        except Exception:
            pass

    def score_text(self):
        return f"Score: {self.score}  (x{self.multiplier:.1f})"

    def update_score_label(self):
        self.score_label.config(text=self.score_text())

    def add_score(self, amount):
        # реальное количество очков с учётом множителя
        gained = int(amount * self.multiplier)
        self.score += gained
        self.update_score_label()

    # ====== события ======

    def on_hit(self):
        self.add_score(1)

    def on_key_press(self, event):
        self.add_score(1)

    def on_close(self):
        # сохраняем счёт и множитель
        self.save_score()
        self.save_multiplier()
        self.destroy()

    # ====== анимация GIF ======

    def animate(self):
        self.image_label.config(image=self.frames[self.current_frame_index])
        self.current_frame_index = (self.current_frame_index + 1) % len(self.frames)
        delay_ms = int(self.current_delay * 1000)
        self.after(delay_ms, self.animate)

    # ====== магазин ======

    def open_shop(self):
        shop = tk.Toplevel(self)
        shop.title("Shop")
        shop.geometry("320x320+760+120")
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
                f"Текущий множитель: x{self.multiplier:.1f}\n"
                f"Текущий Score: {self.score}"
            ),
            fg="#1b1b2f",
            bg="#ffb6c1",
            font=("Arial", 12),
            justify="left",
        )
        info.pack(pady=10)

        # улучшение: x2 множитель за 100 Score
        upgrade_btn = tk.Button(
            shop,
            text="Купить x2 множитель (100 Score)",
            fg="white",
            bg="#ff1493",
            activebackground="#ff85c2",
            activeforeground="white",
            relief="raised",
            bd=2,
            font=("Arial", 12, "bold"),
            cursor="hand2",
            command=lambda: self.buy_multiplier_upgrade(shop, info),
        )
        upgrade_btn.pack(pady=15)

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
            font=("Arial", 12, "bold"),
            cursor="hand2",
        )
        close_btn.pack(pady=10)

    def buy_multiplier_upgrade(self, shop_window, info_label):
        cost = 100
        if self.score >= cost:
            # тратим очки и увеличиваем множитель
            self.score -= cost
            self.multiplier *= 2.0
            self.update_score_label()
            self.save_score()
            self.save_multiplier()

            info_label.config(
                text=(
                    f"Текущий множитель: x{self.multiplier:.1f}\n"
                    f"Текущий Score: {self.score}"
                )
            )

            msg = tk.Label(
                shop_window,
                text="Улучшение куплено! Теперь клики дают больше очков.",
                fg="#1b1b2f",
                bg="#ffb6c1",
                font=("Arial", 11),
            )
            msg.pack(pady=5)
        else:
            msg = tk.Label(
                shop_window,
                text="Недостаточно Score для покупки.",
                fg="#1b1b2f",
                bg="#ffb6c1",
                font=("Arial", 11),
            )
            msg.pack(pady=5)


if __name__ == "__main__":
    app = ZeroTwoBongo()
    app.mainloop()