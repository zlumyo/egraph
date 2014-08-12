__author__ = 'Владимир'

import tkinter as tk
import tkinter.ttk as ttk
import tkinter.filedialog as filedialog
import os
import os.path as FS
import shlex
import subprocess as ipc
import tkinter.messagebox as msgbox


class MainWindow(tk.Frame):
    def __init__(self, master=None):
        tk.Frame.__init__(self, master)

        self.result = None
        self.path_to_dot = "C:\\Program Files (x86)\\Graphviz2.38\\bin\\dot.exe"

        self.pack()
        self.grid_configure(padx=(10, 10), pady=(10, 10))
        self.create_widgets()
        MainWindow.center(master)

    def create_widgets(self):

        self.btn_open = tk.Button(self, text="Открыть файл",
                                  command=self.choose_file)
        self.btn_open.pack(side="top")

        self.lbl_info = tk.Label(self, text="Выберите файл")
        self.lbl_info.pack(side="top")

        self.cmbx_formats = ttk.Combobox(self, state="readonly")
        self.cmbx_formats["values"] = ["png", "svg", "jpg"]
        self.cmbx_formats.current(0)
        self.cmbx_formats.pack(side="top")

        self.btn_create_image = tk.Button(self, text="Создать изображение",
                                          command=self.create_image)
        self.btn_create_image.pack(side="bottom")

    def choose_file(self):
        options = {
            'defaultextension': '.dot',
            'filetypes': [
                ('all files', '.*'),
                ('файлы dot', '.dot')
            ],
            'initialdir': os.getcwd(),
            'initialfile': 'script.dot',
            'parent': self.master,
            'title': 'Выберите dot файл'
        }

        self.result = filedialog.askopenfilename(**options)
        self.lbl_info["text"] = "Файл выбран"

    def create_image(self):
        cmd = shlex.quote(self.path_to_dot) + ' -T' + self.cmbx_formats.get()
        if self.result is None:
            return

        dotfile = open(self.result)
        script = dotfile.read()
        dotfile.close()

        dot = ipc.Popen(shlex.split(cmd), stdin=ipc.PIPE, stdout=ipc.PIPE, stderr=ipc.PIPE)

        dot.stdin.write(script.encode())
        dot.stdin.close()

        image = dot.stdout.read()
        dot.stdout.close()
        dot.stderr.close()

        dot.terminate()

        filename = FS.splitext(self.result)[0] + "." + self.cmbx_formats.get()
        imgpath = FS.join(FS.join(FS.dirname(self.result), os.pardir), FS.basename(filename))
        imgfile = open(imgpath, "wb")
        imgfile.write(image)
        imgfile.close()

        msgbox.showinfo("Генерация изображения", "Генерация и сохранение заверешены!")
        tmp = FS.abspath(imgpath)
        ipc.call(["start", tmp], shell=True)

    @staticmethod
    def center(win):
        win.update_idletasks()
        width = win.winfo_width()
        height = win.winfo_height()
        x = win.winfo_screenwidth() // 2 - width // 2
        y = win.winfo_screenheight() // 2 - height // 2
        win.geometry('{}x{}+{}+{}'.format(width, height, x, y))
        if win.attributes('-alpha') == 0:
            win.attributes('-alpha', 1.0)
        win.deiconify()