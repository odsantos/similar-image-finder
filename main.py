import customtkinter as ctk
from PIL import Image
import imagehash
import sqlite3
import os
import sys
from tkinter import filedialog, messagebox
from i18n import translations

# --- PyInstaller Path Helper ---
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# Configuration
VERSION = "v1.0.3"
DB_NAME = "images_metadata.db" 

ctk.set_appearance_mode("Dark")

try:
    ctk.set_default_color_theme("teal")
except Exception:
    ctk.set_default_color_theme("blue")

class ImageFinderApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.lang = "en"
        self.db_path = DB_NAME
        
        self.setup_ui()
        self.update_ui_text()

    def setup_ui(self):
        self.geometry("1100x700")
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- Sidebar ---
        self.sidebar_frame = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        
        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="SI FINDER", font=ctk.CTkFont(size=22, weight="bold"))
        self.logo_label.pack(padx=20, pady=30)

        self.index_button = ctk.CTkButton(self.sidebar_frame, command=self.run_indexing)
        self.index_button.pack(padx=20, pady=10)

        self.search_button = ctk.CTkButton(self.sidebar_frame, command=self.run_search)
        self.search_button.pack(padx=20, pady=10)

        self.label_threshold = ctk.CTkLabel(self.sidebar_frame, text="")
        self.label_threshold.pack(padx=20, pady=(20, 0))
        
        self.threshold_slider = ctk.CTkSlider(self.sidebar_frame, from_=0, to=20, number_of_steps=20)
        self.threshold_slider.pack(padx=20, pady=10)
        self.threshold_slider.set(8)

        self.version_label = ctk.CTkLabel(self.sidebar_frame, text=VERSION, font=ctk.CTkFont(size=10))
        self.version_label.pack(side="bottom", padx=20, pady=(0, 10))

        self.lang_menu = ctk.CTkOptionMenu(self.sidebar_frame, values=["en", "pt"], command=self.change_language)
        self.lang_menu.pack(side="bottom", padx=20, pady=10)
        
        self.lang_label = ctk.CTkLabel(self.sidebar_frame, text="")
        self.lang_label.pack(side="bottom", padx=20, pady=0)

        self.about_button = ctk.CTkButton(self.sidebar_frame, command=self.show_about, fg_color="transparent", border_width=1)
        self.about_button.pack(side="bottom", padx=20, pady=10)

        # --- Main Content Area ---
        self.scrollable_frame = ctk.CTkScrollableFrame(self)
        self.scrollable_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        self.scrollable_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

    def update_ui_text(self):
        t = translations[self.lang]
        self.title(t["title"])
        self.index_button.configure(text=t["index_button"])
        self.search_button.configure(text=t["search_button"])
        self.label_threshold.configure(text=t["threshold_label"])
        self.scrollable_frame.configure(label_text=t["results_label"])
        self.lang_label.configure(text=t["lang_label"])
        self.about_button.configure(text=t["about_button"])

    def change_language(self, new_lang):
        self.lang = new_lang
        self.update_ui_text()

    def show_about(self):
        t = translations[self.lang]
        messagebox.showinfo(t["about_title"], t["about_text"].format(version=VERSION))

    def get_db_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("CREATE TABLE IF NOT EXISTS images (path TEXT UNIQUE, hash TEXT, last_modified REAL)")
        return conn

    def run_indexing(self):
        folder = filedialog.askdirectory()
        if not folder: 
            return
        
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        valid_exts = ('.png', '.jpg', '.jpeg', '.webp')
        files = [os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith(valid_exts)]

        for path in files:
            try:
                mtime = os.path.getmtime(path)
                cursor.execute("SELECT last_modified FROM images WHERE path=?", (path,))
                row = cursor.fetchone()
                
                if not row or row[0] != mtime:
                    with Image.open(path) as img:
                        h = str(imagehash.phash(img))
                    cursor.execute("INSERT OR REPLACE INTO images VALUES (?, ?, ?)", (path, h, mtime))
            except Exception: 
                continue
        
        conn.commit()
        conn.close()
        messagebox.showinfo("Done", translations[self.lang]["indexing_done"])

    def run_search(self):
        target_path = filedialog.askopenfilename()
        if not target_path: 
            return

        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        with Image.open(target_path) as img:
            target_hash = imagehash.phash(img)

        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT path, hash FROM images")
        
        matches = []
        threshold = self.threshold_slider.get()

        for path, h_str in cursor.fetchall():
            if not os.path.exists(path): 
                continue
            dist = target_hash - imagehash.hex_to_hash(h_str)
            if dist <= threshold:
                matches.append((dist, path))
        
        matches.sort(key=lambda x: x[0])
        self.display_matches(matches)
        conn.close()

    def display_matches(self, matches):
        for i, (dist, path) in enumerate(matches):
            card = ctk.CTkFrame(self.scrollable_frame)
            card.grid(row=i // 4, column=i % 4, padx=10, pady=10, sticky="nsew")

            try:
                img = Image.open(path)
                ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(120, 120))
                img_label = ctk.CTkLabel(card, image=ctk_img, text="")
                img_label.pack(pady=5)
            except:
                ctk.CTkLabel(card, text=translations[self.lang]["error_loading"]).pack()

            ctk.CTkLabel(card, text=f"Dist: {int(dist)}", font=("Arial", 11, "bold")).pack()
            filename = os.path.basename(path)
            ctk.CTkLabel(card, text=filename, font=("Arial", 10), wraplength=120).pack(pady=(0,5))

if __name__ == "__main__":
    app = ImageFinderApp()
    app.mainloop()