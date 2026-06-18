import tkinter as tk
from tkinter import filedialog

def open_file(**kwargs):
   root = tk.Tk()
   root.title("Select File Widget")
   if 'title' not in kwargs:
      kwargs['title'] = "Select File"
   if 'filetypes' not in kwargs:
      kwargs['filetypes'] = [("Text Files", "*.txt")]
   f_path = filedialog.askopenfilename(**kwargs)
   # print(f"File opened: {f_path}")
   root.destroy()
   return f_path

def open_directory(**kwargs):
   root = tk.Tk()
   root.title("Select Folder Widget")
   if 'title' not in kwargs:
      kwargs['title'] = "Select Directory"
   d_path = filedialog.askdirectory(**kwargs)
   root.destroy()
   return d_path
