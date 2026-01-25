import customtkinter as ctk
from PIL import Image, ImageTk
import imagehash
import sqlite3
import os
import sys
import threading
import re
import webbrowser
import subprocess
from tkinter import filedialog, messagebox
from i18n import translations

VERSION = "v1.2.1"
DB_NAME = "images_metadata.db"
DEFAULT_URL = "https://your-website.com/search?id="
REPO_URL = "https://github.com/odsantos/similar-image-finder"
PRIMARY_BLUE = "#1f538d" 
HOVER_BLUE = "#14375e"

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def open_file_explorer(path):
    path = os.path.normpath(path)
    try:
        if sys.platform == "win32":
            subprocess.Popen(['explorer', '/select,', path])
        elif sys.platform == "darwin":
            subprocess.Popen(['open', '-R', path])
        else: 
            try:
                subprocess.run([
                    "dbus-send", "--session", "--dest=org.freedesktop.FileManager1", 
                    "--type=method_call", "/org/freedesktop/FileManager1", 
                    "org.freedesktop.FileManager1.ShowItems", 
                    f"array:string:file://{path}", "string:"
                ], timeout=1, stderr=subprocess.DEVNULL)
            except:
                subprocess.Popen(['dolphin', '--select', path])
    except Exception:
        try:
            subprocess.Popen(['xdg-open', os.path.dirname(path)])
        except: pass

class ImageFinderApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.lang = "en"
        self.db_path = DB_NAME
        self.current_font_size = 12
        self.thumbnails = [] 
        self.status_state = None 

        try:
            icon_p = resource_path("assets/images/icon-1024x1024.png")
            if os.path.exists(icon_p):
                self.icon_image = Image.open(icon_p)
                self.tk_icon = ImageTk.PhotoImage(self.icon_image.resize((32, 32)))
                self.iconphoto(True, self.tk_icon)
                # Fix for Linux title bars/taskbars
                self.wm_iconphoto(True, self.tk_icon)
        except: pass
            
        self.setup_ui()
        self.update_ui_text()

    def show_custom_info(self, title, message):
        info_window = ctk.CTkToplevel(self)
        info_window.title(title)
        info_window.geometry("450x300")
        info_window.after(100, lambda: info_window.focus_force())
        
        info_window.grid_columnconfigure(0, weight=1)
        info_window.grid_rowconfigure((0, 2), weight=1) 

        msg_label = ctk.CTkLabel(
            info_window, 
            text=message, 
            justify="center", 
            wraplength=400,
            font=("Arial", self.current_font_size)
        )
        msg_label.grid(row=1, column=0, padx=20, pady=10)
        
        ok_button = ctk.CTkButton(
            info_window, 
            text="OK", 
            width=100, 
            command=info_window.destroy,
            fg_color=PRIMARY_BLUE,
            hover_color=HOVER_BLUE
        )
        ok_button.grid(row=3, column=0, pady=(0, 25))

    def show_about(self):
        t = translations[self.lang]
        about_window = ctk.CTkToplevel(self)
        about_window.title(t["about_title"])
        about_window.geometry("450x320")
        about_window.after(100, lambda: about_window.focus_force())

        about_window.grid_columnconfigure(0, weight=1)
        about_window.grid_rowconfigure((0, 3), weight=1) 
        
        msg = ctk.CTkLabel(
            about_window, 
            text=t["about_text"].format(version=VERSION), 
            justify="center", 
            wraplength=400,
            font=("Arial", self.current_font_size)
        )
        msg.grid(row=1, column=0, padx=20, pady=(10, 5))
        
        link_color = ("#1f538d", "#5dade2") 
        link_label = ctk.CTkLabel(
            about_window, 
            text=t["repo_label"], 
            text_color=link_color, 
            cursor="hand2", 
            font=("Arial", self.current_font_size, "underline")
        )
        link_label.grid(row=2, column=0, pady=5)
        link_label.bind("<Button-1>", lambda e: webbrowser.open(REPO_URL))

        ok_btn = ctk.CTkButton(
            about_window, 
            text="OK", 
            width=100, 
            command=about_window.destroy, 
            fg_color=PRIMARY_BLUE, 
            hover_color=HOVER_BLUE
        )
        ok_btn.grid(row=4, column=0, pady=(0, 25))

    def on_about_hover(self, event):
        self.about_button.configure(text_color="white", fg_color=HOVER_BLUE)

    def on_about_leave(self, event):
        self.about_button.configure(fg_color="transparent")
        self.about_button.configure(text_color="black" if ctk.get_appearance_mode() == "Light" else "white")

    def show_thresh_info(self):
        t = translations[self.lang]
        self.show_custom_info(t["sens_help_title"], t["sens_help_msg"])

    def show_url_info(self):
        t = translations[self.lang]
        self.show_custom_info(t["url_help_title"], t["url_help_msg"])

    def handle_web_click(self, path):
        current_url = self.url_entry.get().strip()
        if not current_url or "your-website.com" in current_url:
            self.show_url_info()
            return

        filename = os.path.basename(path)
        match = re.search(r'l_(\d+)p(\d+)', filename)
        if match:
            lesson_id, page_id = match.group(1), match.group(2)
            sep = "&" if "?" in current_url else "?"
            webbrowser.open(f"{current_url}{sep}lesson_id={lesson_id}&page_id={page_id}")

    def change_font_size(self, size):
        self.current_font_size = int(size)
        self.update_ui_text()

    def update_slider_label(self, val):
        self.threshold_value_label.configure(text=str(int(val)))

    def toggle_theme(self):
        ctk.set_appearance_mode("Dark" if self.theme_switch.get() else "Light")
        self.about_button.configure(text_color="black" if not self.theme_switch.get() else "white")

    def change_language(self, new_lang):
        self.lang = new_lang
        self.update_ui_text()

    def update_font_globally(self, master):
        for widget in master.winfo_children():
            try:
                if hasattr(widget, "configure") and not isinstance(widget, (ctk.CTkScrollableFrame, ctk.CTkFrame)):
                    widget.configure(font=ctk.CTkFont(size=self.current_font_size))
            except: pass
            if hasattr(widget, "winfo_children") and widget.winfo_children():
                self.update_font_globally(widget)

    def update_ui_text(self):
        t = translations[self.lang]
        self.title(t["title"])
        self.index_button.configure(text=t["index_button"])
        self.search_button.configure(text=t["search_button"])
        self.label_threshold.configure(text=t["threshold_label"])
        self.url_label.configure(text=t["base_url"])
        self.theme_switch.configure(text=t["dark_mode"])
        self.about_button.configure(text=t["about_button"])
        
        if self.status_state == "complete":
            self.status_label.configure(text=t["status_complete"])
        elif self.status_state == "searching":
            self.status_label.configure(text=t["status_searching"])
        elif isinstance(self.status_state, int):
            self.status_label.configure(text=t["found_matches"].format(count=self.status_state))
            
        self.update_font_globally(self)

    def setup_ui(self):
        self.geometry("1200x800")
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar_frame = ctk.CTkFrame(self, width=250, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        
        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="SI FINDER", font=ctk.CTkFont(size=22, weight="bold"))
        self.logo_label.pack(padx=20, pady=(30, 10))

        self.index_button = ctk.CTkButton(self.sidebar_frame, command=self.start_indexing_thread, fg_color=PRIMARY_BLUE, hover_color=HOVER_BLUE)
        self.index_button.pack(padx=20, pady=5)

        self.search_button = ctk.CTkButton(self.sidebar_frame, command=self.start_search_thread, fg_color=PRIMARY_BLUE, hover_color=HOVER_BLUE)
        self.search_button.pack(padx=20, pady=5)

        self.progress_bar = ctk.CTkProgressBar(self.sidebar_frame, progress_color=PRIMARY_BLUE)
        self.progress_bar.pack(padx=20, pady=10)
        self.progress_bar.set(0)
        self.status_label = ctk.CTkLabel(self.sidebar_frame, text="", font=ctk.CTkFont(size=11))
        self.status_label.pack(padx=20, pady=0)

        ctk.CTkLabel(self.sidebar_frame, text="", height=45).pack()

        thresh_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        thresh_frame.pack(padx=20, fill="x")
        self.label_threshold = ctk.CTkLabel(thresh_frame, text="")
        self.label_threshold.pack(side="left")
        ctk.CTkButton(thresh_frame, text="?", width=20, height=20, corner_radius=10, command=self.show_thresh_info, fg_color=PRIMARY_BLUE, hover_color=HOVER_BLUE).pack(side="right")

        self.threshold_slider = ctk.CTkSlider(self.sidebar_frame, from_=0, to=20, number_of_steps=20, command=self.update_slider_label, button_color=PRIMARY_BLUE, button_hover_color=HOVER_BLUE, progress_color=PRIMARY_BLUE)
        self.threshold_slider.pack(padx=20, pady=(10,0))
        self.threshold_slider.set(8)
        self.threshold_value_label = ctk.CTkLabel(self.sidebar_frame, text="8", font=ctk.CTkFont(size=11, weight="bold"))
        self.threshold_value_label.pack(padx=20, pady=(0, 0))

        ctk.CTkLabel(self.sidebar_frame, text="", height=45).pack()

        url_header = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        url_header.pack(padx=20, fill="x")
        self.url_label = ctk.CTkLabel(url_header, text="", font=ctk.CTkFont(size=11))
        self.url_label.pack(side="left")
        ctk.CTkButton(url_header, text="?", width=20, height=20, corner_radius=10, command=self.show_url_info, fg_color=PRIMARY_BLUE, hover_color=HOVER_BLUE).pack(side="right")
        
        self.url_entry = ctk.CTkEntry(self.sidebar_frame)
        self.url_entry.pack(padx=20, pady=5, fill="x")
        self.url_entry.insert(0, DEFAULT_URL)

        ctk.CTkLabel(self.sidebar_frame, text="", height=45).pack()

        self.theme_switch = ctk.CTkSwitch(self.sidebar_frame, text="", command=self.toggle_theme, progress_color=PRIMARY_BLUE)
        self.theme_switch.pack(padx=20, pady=10)
        self.theme_switch.select()

        self.font_size_menu = ctk.CTkOptionMenu(self.sidebar_frame, values=["12", "14", "16", "18", "20"], command=self.change_font_size, fg_color=PRIMARY_BLUE, button_color=PRIMARY_BLUE, button_hover_color=HOVER_BLUE)
        self.font_size_menu.pack(padx=20, pady=10)

        self.lang_menu = ctk.CTkOptionMenu(self.sidebar_frame, values=["en", "pt"], command=self.change_language, fg_color=PRIMARY_BLUE, button_color=PRIMARY_BLUE, button_hover_color=HOVER_BLUE)
        self.lang_menu.pack(side="bottom", padx=20, pady=20)
        
        self.about_button = ctk.CTkButton(self.sidebar_frame, command=self.show_about, fg_color="transparent", border_width=1, hover_color=HOVER_BLUE, text_color=("black", "white"))
        self.about_button.pack(side="bottom", padx=20, pady=(0, 10))
        self.about_button.bind("<Enter>", self.on_about_hover)
        self.about_button.bind("<Leave>", self.on_about_leave)

        self.scrollable_frame = ctk.CTkScrollableFrame(self)
        self.scrollable_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        self.scrollable_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

    def get_db_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("CREATE TABLE IF NOT EXISTS images (path TEXT UNIQUE, hash TEXT, last_modified REAL)")
        return conn

    def start_indexing_thread(self):
        folder = filedialog.askdirectory()
        if not folder: return
        self.index_button.configure(state="disabled")
        threading.Thread(target=self.run_indexing, args=(folder,), daemon=True).start()

    def run_indexing(self, folder):
        conn = self.get_db_connection()
        cursor = conn.cursor()
        valid_exts = ('.png', '.jpg', '.jpeg', '.webp')
        files = [os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith(valid_exts)]
        total = len(files)
        for i, path in enumerate(files):
            try:
                mtime = os.path.getmtime(path)
                cursor.execute("SELECT last_modified FROM images WHERE path=?", (path,))
                row = cursor.fetchone()
                if not row or row[0] != mtime:
                    with Image.open(path) as img:
                        h = str(imagehash.phash(img))
                    cursor.execute("INSERT OR REPLACE INTO images VALUES (?, ?, ?)", (path, h, mtime))
                if i % 10 == 0:
                    self.progress_bar.set(i / total)
                    self.after(0, lambda val=f"{i}/{total}": self.status_label.configure(text=val))
            except: continue
        conn.commit()
        conn.close()
        self.status_state = "complete"
        self.after(0, self.update_ui_text)
        self.after(0, lambda: self.index_button.configure(state="normal"))
        self.show_custom_info("Done", translations[self.lang]["indexing_done"])

    def start_search_thread(self):
        target_path = filedialog.askopenfilename()
        if not target_path: return
        threading.Thread(target=self.run_search, args=(target_path,), daemon=True).start()

    def run_search(self, target_path):
        self.status_state = "searching"
        self.after(0, self.update_ui_text)
        self.after(0, lambda: [w.destroy() for w in self.scrollable_frame.winfo_children()])
        with Image.open(target_path) as img:
            target_hash = imagehash.phash(img)
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT path, hash FROM images")
        matches, threshold, all_data = [], self.threshold_slider.get(), cursor.fetchall()
        for i, (path, h_str) in enumerate(all_data):
            if not os.path.exists(path): continue
            dist = target_hash - imagehash.hex_to_hash(h_str)
            if dist <= threshold:
                matches.append((dist, path))
            if i % 100 == 0: self.progress_bar.set(i / len(all_data))
        matches.sort(key=lambda x: x[0])
        conn.close()
        self.status_state = len(matches)
        self.after(0, self.update_ui_text)
        self.after(0, lambda: self.display_matches(matches))

    def display_matches(self, matches):
        self.thumbnails = [] 
        t = translations[self.lang]
        
        # Load helper icons using resource_path
        try:
            globe_p = resource_path("assets/images/globe.png")
            folder_p = resource_path("assets/images/folder.png")
            globe_img = Image.open(globe_p).resize((20, 20))
            folder_img = Image.open(folder_p).resize((20, 20))
            ctk_globe = ctk.CTkImage(light_image=globe_img, dark_image=globe_img, size=(20, 20))
            ctk_folder = ctk.CTkImage(light_image=folder_img, dark_image=folder_img, size=(20, 20))
        except:
            # Fallback if icons are missing
            ctk_globe = None
            ctk_folder = None

        for i, (dist, path) in enumerate(matches):
            card = ctk.CTkFrame(self.scrollable_frame)
            card.grid(row=i // 4, column=i % 4, padx=10, pady=10, sticky="nsew")
            try:
                raw_img = Image.open(path)
                raw_img.thumbnail((240, 240))
                ctk_img = ctk.CTkImage(light_image=raw_img, dark_image=raw_img, size=(120, 120))
                self.thumbnails.append(ctk_img) 
                ctk.CTkLabel(card, image=ctk_img, text="").pack(pady=5)
            except: 
                # Use translated error and current dynamic font size
                ctk.CTkLabel(card, text=t["error_loading"], font=("Arial", self.current_font_size)).pack(pady=40)

            filename = os.path.basename(path)
            ctk.CTkLabel(card, text=filename, font=("Arial", self.current_font_size, "bold"), wraplength=120).pack(pady=0)
            ctk.CTkLabel(card, text=f"Dist: {int(dist)}", font=("Arial", self.current_font_size - 2), text_color=("gray30", "gray70")).pack(pady=(0, 5))
            
            btn_frame = ctk.CTkFrame(card, fg_color="transparent")
            btn_frame.pack(pady=5)
            
            # Globe button (Web link)
            ctk.CTkButton(btn_frame, image=ctk_globe, text="" if ctk_globe else "Web", 
                         width=30, height=30, fg_color="transparent", 
                         hover_color=("gray80", "gray20"), 
                         command=lambda p=path: self.handle_web_click(p)).pack(side="left", padx=5)
            
            # Folder button (Local explorer)
            ctk.CTkButton(btn_frame, image=ctk_folder, text="" if ctk_folder else "File", 
                         width=30, height=30, fg_color="transparent", 
                         hover_color=("gray80", "gray20"), 
                         command=lambda p=path: open_file_explorer(p)).pack(side="left", padx=5)

if __name__ == "__main__":
    app = ImageFinderApp()
    app.mainloop()