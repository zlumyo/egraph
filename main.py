__author__ = 'Владимир'

import tkinter as tk
from GUI.mainwindow import MainWindow


if __name__ == '__main__':
    root = tk.Tk()
    mainwindow = MainWindow(master=root)
    mainwindow.mainloop()