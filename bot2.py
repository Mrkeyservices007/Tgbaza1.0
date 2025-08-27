#!/usr/bin/env python3
# telegram_gui_monitor_img_safe.py

import asyncio, os, json
from telethon import TelegramClient
from telethon.tl.types import Channel, Chat
from zoneinfo import ZoneInfo
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk

api_id = 
api_hash = ''
LOCAL_TZ = ZoneInfo("Asia/Samarkand")

base_dir = os.path.dirname(os.path.abspath(__file__))
log_dir = os.path.join(base_dir, 'logs')
os.makedirs(log_dir, exist_ok=True)

client = TelegramClient('session_name', api_id, api_hash)

def load_all_users():
    users = []
    paths = [
        os.path.join(log_dir, "groups"),
        os.path.join(log_dir, "private", "users")
    ]
    for path in paths:
        if os.path.exists(path):
            for root, dirs, files in os.walk(path):
                for d in dirs:
                    info_file = os.path.join(root, d, "info.json")
                    if os.path.exists(info_file):
                        with open(info_file, "r", encoding="utf-8") as f:
                            users.append(json.load(f))
    return users

def search_user(identifier):
    results = []
    all_users = load_all_users()
    for u in all_users:
        if str(identifier) in [str(u.get("id")), u.get("username") or "", u.get("phone") or ""]:
            results.append(u)
    return results

class TelegramMonitorGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Telegram Monitor")
        self.geometry("1000x600")
        self.configure(bg="black")

        self.selected_img_label = tk.Label(self, bg="black")
        self.selected_img_label.pack(pady=5)

        self.label = tk.Label(self, text="ID / Username / Phone:", font=("Arial", 12), bg="black", fg="lime")
        self.label.pack(pady=5)

        self.search_var = tk.StringVar()
        self.entry = tk.Entry(self, textvariable=self.search_var, font=("Arial", 12), width=40, bg="#222", fg="lime", insertbackground="lime")
        self.entry.pack(pady=5)

        self.search_btn = tk.Button(self, text="Search", command=self.on_search, bg="#111", fg="lime")
        self.search_btn.pack(pady=5)

        self.frame = tk.Frame(self, bg="black")
        self.frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.tree_scroll = tk.Scrollbar(self.frame)
        self.tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        columns = ("ID", "Username", "First Name", "Last Name", "Phone", "Status", "Bio")
        self.tree = ttk.Treeview(self.frame, columns=columns, show="headings", yscrollcommand=self.tree_scroll.set, selectmode="browse")
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree_scroll.config(command=self.tree.yview)

        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=120, anchor="center")

        style = ttk.Style(self)
        style.theme_use("default")
        style.configure("Treeview",
                        background="black",
                        foreground="lime",
                        rowheight=60,
                        fieldbackground="black")
        style.map("Treeview",
                  background=[('selected', '#111')],
                  foreground=[('selected', 'lime')])

        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.images = {}  # rasmlar reference

        self.all_users = load_all_users()
        self.display_users(self.all_users)

    def load_profile_image(self, user):
        user_folder = os.path.join(log_dir, "groups", str(user.get("username") or user.get("id")))
        if not os.path.exists(user_folder):
            user_folder = os.path.join(log_dir, "private", "users", str(user.get("username") or user.get("id")))
        profile_path = os.path.join(user_folder, "profile.jpg")
        if os.path.exists(profile_path):
            try:
                img = Image.open(profile_path).resize((100, 100))
                tk_img = ImageTk.PhotoImage(img)
                return tk_img
            except:
                return None
        return None

    def display_users(self, users):
        for i in self.tree.get_children():
            self.tree.delete(i)
        for idx, u in enumerate(users):
            status_clean = u.get("status") or "Unknown"
            self.tree.insert("", "end",
                             iid=f"{u.get('id')}_{idx}",
                             values=(u.get("id"),
                                     u.get("username") or "",
                                     u.get("first_name") or "",
                                     u.get("last_name") or "",
                                     u.get("phone") or "",
                                     status_clean,
                                     str(u.get("bio") or "")))

    def on_search(self):
        identifier = self.search_var.get().strip()
        if not identifier:
            messagebox.showwarning("Warning", "Iltimos, qidirish uchun ID, username yoki telefon raqam kiriting!")
            return
        results = search_user(identifier)
        if results:
            self.display_users(results)
        else:
            messagebox.showinfo("Not Found", f"'{identifier}' bo'yicha foydalanuvchi topilmadi!")

    def on_select(self, event):
        selected = self.tree.selection()
        if selected:
            idx = selected[0]
            user_id = idx.split("_")[0]
            # topish
            user = next((u for u in self.all_users if str(u.get("id"))==user_id), None)
            if user:
                profile_img = self.load_profile_image(user)
                if profile_img:
                    self.selected_img_label.configure(image=profile_img)
                    self.selected_img_label.image = profile_img

async def start_client():
    await client.start()
    print("🤖 Telegram monitor ishga tushdi...")

if __name__ == "__main__":
    asyncio.run(start_client())
    app = TelegramMonitorGUI()
    app.mainloop()
