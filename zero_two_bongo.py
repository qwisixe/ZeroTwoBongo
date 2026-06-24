import tkinter as tk
import time

GIF_PATH = "zero_two.gif"  # имя gif-файла рядом со скриптом

class ZeroTwoBongo:
    def __init__(self):
        # окно
        self.root = tk.Tk()
        self.root.title("Zero Two Bongo")
        self.root.configure(bg="black")
        self.root.overrideredirect(True)  # без рамки

        # позиция/размер окна
        self.root.geometry("300x300+100+100")

        # загружаем все кадры gif
        self.frames = []
        try:
            # пробуем прочитать до 100 кадров
            for i in range(100):
                frame = tk.PhotoImage(file=GIF_PATH, format=f"gif -index {i}")
                self.frames.append(frame)
        except tk.TclError:
            # gif закончился — выходим из цикла
            pass

        if not self.frames:
            raise RuntimeError(f"Не удалось загрузить кадры из {GIF_PATH}. Проверь имя файла и его расположение.")

        # состояние анимации
        self.current_frame_index = 0
        self.last_frame_change_time = time.time()
        self.base_speed = 0.12       # базовая скорость (сек на кадр)
        self.current_speed = self.base_speed

        # виджет с картинкой
        self.label = tk.Label(self.root, bg="black")
        self.label.pack(expand=True)

        # счётчик
        self.score = 0
        self.score_label = tk.Label(self.root, text=f"Score: {self.score}", fg="white", bg="black")
        self.score_label.pack()

        # реакция на клавиши
        self.root.bind("<KeyPress>", self.on_key_press)

        # запуск анимации
        self.update_animation()
        self.root.mainloop()

    def on_key_press(self, event):
        # при нажатии любой клавиши
        self.score += 1
        self.score_label.config(text=f"Score: {self.score}")
        # ускоряем анимацию
        self.current_speed = max(0.04, self.current_speed * 0.7)

    def update_animation(self):
        now = time.time()
        # смена кадра
        if now - self.last_frame_change_time >= self.current_speed:
            self.last_frame_change_time = now
            self.current_frame_index = (self.current_frame_index + 1) % len(self.frames)
            self.label.config(image=self.frames[self.current_frame_index])

            # плавно возвращаемся к базовой скорости
            if self.current_speed < self.base_speed:
                self.current_speed += 0.01

        # повторяем каждые 10 мс
        self.root.after(10, self.update_animation)


if __name__ == "__main__":
    ZeroTwoBongo()