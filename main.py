# SI Finder - Similar Image Finder
# Copyright (c) 2026 Osvaldo Santos
# Licensed under the MIT License
# AI Collaboration Credit: Gemini (Google AI)

import customtkinter as ctk
from PIL import Image, ImageTk
import imagehash
import sqlite3
import os
import sys
import threading
import re
import webbrowser
import logging
import subprocess
import hashlib
from tkinter import filedialog
from i18n import translations

VERSION = "v1.3.3"
DEFAULT_URL = "https://your-website.com/search?id="
REPO_URL = "https://github.com/odsantos/similar-image-finder"
PRIMARY_BLUE = "#1f538d"
HOVER_BLUE = "#14375e"
STD_HEIGHT = 32


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


def reveal_file_in_explorer(file_path):
    file_path = os.path.abspath(os.path.normpath(file_path))
    if not os.path.exists(file_path):
        return

    try:
        if sys.platform == "win32":
            subprocess.run(["explorer", "/select,", file_path])
        elif sys.platform == "darwin":
            subprocess.run(["open", "-R", file_path])
        else:  # Linux
            # Method 1: Try DBus (universal for modern desktops)
            try:
                subprocess.run(
                    [
                        "dbus-send",
                        "--session",
                        "--print-reply",
                        "--dest=org.freedesktop.FileManager1",
                        "/org/freedesktop/FileManager1",
                        "org.freedesktop.FileManager1.ShowItems",
                        f"array:string:file://{file_path}",
                        "string:",
                    ],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass

            # Method 2: Check for specific file managers
            managers = [
                ("nautilus", "--select"),
                ("dolphin", "--select"),
                ("nemo", "--no-desktop"),
                ("caja", "--select"),
                ("thunar", "--select"),
                ("pcmanfm", "--select"),
            ]

            for cmd, arg in managers:
                if (
                    subprocess.call(
                        ["which", cmd],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    == 0
                ):
                    subprocess.Popen([cmd, arg, file_path])
                    return

            # Method 3: Fallback to opening parent directory
            subprocess.Popen(["xdg-open", os.path.dirname(file_path)])

    except Exception as e:
        print(f"Error revealing file in explorer: {e}")


def open_directory_in_explorer(dir_path):
    dir_path = os.path.abspath(os.path.normpath(dir_path))
    if not os.path.exists(dir_path) or not os.path.isdir(dir_path):
        return

    try:
        if sys.platform == "win32":
            subprocess.run(["explorer", dir_path])
        elif sys.platform == "darwin":
            subprocess.run(["open", dir_path])
        else:  # Linux
            subprocess.Popen(["xdg-open", dir_path])
    except Exception as e:
        print(f"Error opening directory in explorer: {e}")


class ImageFinderApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # FIX: Set WM_CLASS for Linux dock/taskbar association
        if sys.platform == "linux":
            try:
                # Use a lower-level call to ensure the class is set early and correctly
                self.tk.call('wm', 'class', self._w, 'si_finder')
                self.wm_name("si_finder")
                self.wm_instance("si_finder")
                # Trigger self-installation if not in a persistent home
                self.install_linux_to_system()
            except Exception as e:
                print(f"Error setting Linux WM properties: {e}")

        ctk.set_appearance_mode("System")  # Detect system theme on startup
        self.lang = "en"
        self.db_path = None
        self.current_font_size = 12
        self.thumbnails = []
        self.status_state = None
        self.active_popup = None
        self.active_popup_type = None
        self.last_search_image = None
        self.previous_status_text = ""

        # Keys for dynamic translation of help dialogs
        self.current_info_title_key = ""
        self.current_info_msg_key = ""

        self.set_window_icon(self)
        self.setup_ui()
        self.update_ui_text()

    def set_window_icon(self, window):
        """Sets the window icon for both Windows and Linux/macOS."""
        try:
            if sys.platform == "win32":
                icon_path = resource_path("assets/images/icon.ico")
                if os.path.exists(icon_path):
                    # Set immediately
                    window.iconbitmap(icon_path)
                    # For Toplevels, Windows often needs a retry after it's deiconified/mapped
                    if isinstance(window, ctk.CTkToplevel):
                        window.after(200, lambda: window.iconbitmap(icon_path))
                        window.after(500, lambda: window.iconbitmap(icon_path))
            else:
                icon_path = resource_path("assets/images/icon-1024x1024.png")
                if os.path.exists(icon_path):
                    img = Image.open(icon_path)
                    
                    # Prevent Garbage Collection
                    if not hasattr(self, '_icon_storage'):
                        self._icon_storage = []
                    
                    # Create multiple sizes (standard for GNOME/Wayland)
                    photo_icons = []
                    for size in (16, 32, 64, 128, 256):
                        resized = img.resize((size, size), Image.Resampling.LANCZOS)
                        ph = ImageTk.PhotoImage(resized)
                        photo_icons.append(ph)
                        self._icon_storage.append(ph)
                    
                    # 'True' applies this icon to all future popup dialogs automatically
                    window.iconphoto(True, *photo_icons)
        except Exception as e:
            print(f"Error loading icon: {e}")

    def install_linux_to_system(self):
        """Automatically moves the app to a persistent location on first run."""
        if sys.platform != "linux":
            return

        persistent_dir = self.get_app_dir() # ~/.local/share/SI-Finder
        shortcut_path = os.path.expanduser("~/.local/share/applications/si_finder.desktop")
        
        # Determine current executable path
        current_exe = os.path.abspath(sys.argv[0])
        persistent_exe = os.path.join(persistent_dir, "SI-Finder")
        persistent_icon = os.path.join(persistent_dir, "icon.png")

        # If we are already running from the persistent home, just ensure shortcut exists
        if current_exe == persistent_exe:
            if not os.path.exists(shortcut_path):
                self._create_desktop_file(persistent_exe, persistent_icon, shortcut_path)
            return

        # Perform migration
        try:
            import shutil
            os.makedirs(persistent_dir, exist_ok=True)
            
            # 1. Copy binary
            if not os.path.exists(persistent_exe) or os.path.getmtime(current_exe) > os.path.getmtime(persistent_exe):
                shutil.copy2(current_exe, persistent_exe)
                os.chmod(persistent_exe, 0o755)

            # 2. Copy icon (look for bundled resource or local dot-prefixed companion)
            bundled_icon = resource_path("assets/images/icon-1024x1024.png")
            local_hidden_icon = os.path.join(os.path.dirname(current_exe), ".SI-Finder-Icon.png")
            
            if os.path.exists(bundled_icon):
                shutil.copy2(bundled_icon, persistent_icon)
            elif os.path.exists(local_hidden_icon):
                shutil.copy2(local_hidden_icon, persistent_icon)

            # 3. Create Desktop Shortcut
            self._create_desktop_file(persistent_exe, persistent_icon, shortcut_path)
            
            # 4. Notify User
            self.after(1000, lambda: self._show_install_notification())
            
        except Exception as e:
            print(f"Linux self-installation failed: {e}")

    def _create_desktop_file(self, exe_path, icon_path, shortcut_path):
        """Helper to write the .desktop file."""
        desktop_content = f"""[Desktop Entry]
Name=SI Finder
Exec="{exe_path}"
Icon={icon_path}
Type=Application
Categories=Graphics;Utility;
Terminal=false
StartupWMClass=si_finder
Comment=Similar Image Finder
"""
        with open(shortcut_path, "w") as f:
            f.write(desktop_content)
        os.chmod(shortcut_path, 0o755)
        print(f"System shortcut created at: {shortcut_path}")

    def _show_install_notification(self):
        """Shows a one-time message after successful migration."""
        from tkinter import messagebox
        messagebox.showinfo(
            "SI Finder Installed",
            "SI Finder is now in your Applications menu! 🚀\n\n"
            "The application has been moved to a persistent location.\n"
            "You can now safely delete this extraction folder."
        )

    def get_app_dir(self):
        """
        Returns a writable directory for storing application data (databases).
        - Windows: %APPDATA%/SI-Finder
        - macOS: ~/Library/Application Support/SI-Finder
        - Linux: ~/.local/share/SI-Finder (or $XDG_DATA_HOME)
        """
        if sys.platform == "win32":
            base_dir = os.path.join(os.environ["APPDATA"], "SI-Finder")
        elif sys.platform == "darwin":
            base_dir = os.path.expanduser("~/Library/Application Support/SI-Finder")
        else:
            # Linux / Unix
            xdg_data_home = os.environ.get(
                "XDG_DATA_HOME", os.path.expanduser("~/.local/share")
            )
            base_dir = os.path.join(xdg_data_home, "SI-Finder")

        if not os.path.exists(base_dir):
            try:
                os.makedirs(base_dir, exist_ok=True)
            except OSError as e:
                print(f"Error creating data directory {base_dir}: {e}")
                # Fallback to tmp if user dir is not writable (unlikely but safe)
                base_dir = os.path.join(
                    os.environ.get("TMPDIR", "/tmp"), "SI-Finder_Data"
                )
                os.makedirs(base_dir, exist_ok=True)

        return base_dir

    def get_db_connection(self, specific_db=None):
        target_db = specific_db if specific_db else self.db_path
        if not target_db:
            return None
        path_to_db = os.path.join(self.get_app_dir(), target_db)
        conn = sqlite3.connect(path_to_db)
        conn.execute(
            "CREATE TABLE IF NOT EXISTS images (path TEXT UNIQUE, hash TEXT, last_modified REAL)"
        )
        conn.execute("CREATE TABLE IF NOT EXISTS info (key TEXT UNIQUE, value TEXT)")
        return conn

    def _handle_mousewheel_event(self, event, scrollable_frame):
        """Redirects mouse wheel events to a specific scrollable frame's canvas."""
        # event.num is for Linux (4=up, 5=down); event.delta is for Windows/macOS
        if event.num == 4:
            scrollable_frame._parent_canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            scrollable_frame._parent_canvas.yview_scroll(1, "units")
        elif event.delta:
            # Standardize delta (Windows/macOS)
            scroll_amount = int(-1 * (event.delta / 120))
            scrollable_frame._parent_canvas.yview_scroll(scroll_amount, "units")

    def bind_tree(self, widget, callback):
        """Recursively binds mousewheel events to a widget and all its children."""
        events = ["<MouseWheel>", "<Button-4>", "<Button-5>"]
        for event in events:
            widget.bind(event, callback)

        # Apply to all child widgets (labels, images, frames, etc.)
        for child in widget.winfo_children():
            self.bind_tree(child, callback)

    def _manage_popup(self, title, popup_type):
        """Creates a modal popup window that blocks main window interaction."""
        if self.active_popup is not None and self.active_popup.winfo_exists():
            self.active_popup.destroy()

        popup = ctk.CTkToplevel(self)
        popup.withdraw()  # Hide the window immediately upon creation
        popup.title(title)
        popup.transient(self)

        popup.after(100, lambda: popup.focus_force())
        self.active_popup = popup
        self.active_popup_type = popup_type
        
        # Ensure icon is set for the new top-level popup
        self.set_window_icon(popup)
        
        return popup

    def center_toplevel(self, toplevel, width, height):
        main_win_x = self.winfo_x()
        main_win_y = self.winfo_y()
        main_win_width = self.winfo_width()
        main_win_height = self.winfo_height()

        x_pos = main_win_x + (main_win_width - width) // 2
        y_pos = main_win_y + (main_win_height - height) // 2

        toplevel.geometry(f"{width}x{height}+{x_pos}+{y_pos}")

    def show_custom_info(self, title_key, message_key):
        """Creates a translated information popup."""
        t = translations[self.lang]
        self.current_info_title_key = title_key
        self.current_info_msg_key = message_key

        info_window = self._manage_popup(t.get(title_key, title_key), "info")
        self.center_toplevel(info_window, 450, 300)
        info_window.grid_columnconfigure(0, weight=1)
        info_window.grid_rowconfigure((0, 2), weight=1)

        self.info_msg_label = ctk.CTkLabel(
            info_window,
            text=t.get(message_key, message_key),
            justify="center",
            wraplength=400,
        )
        self.info_msg_label.grid(row=1, column=0, padx=20, pady=10)

        ok_button = ctk.CTkButton(
            info_window,
            text="OK",
            width=100,
            height=STD_HEIGHT,
            command=info_window.destroy,
            fg_color=PRIMARY_BLUE,
            hover_color=HOVER_BLUE,
        )
        ok_button.grid(row=3, column=0, pady=(0, 25))

        self.update_font_globally(info_window)
        info_window.after(10, lambda: [info_window.deiconify(), info_window.grab_set()])

    def show_load_index_window(self, title_key_override=None):
        t = translations[self.lang]
        self._manage_popup(t.get(title_key_override or "manage_indexes_title", "Manage Indexes"), "load")
        self.center_toplevel(self.active_popup, 500, 400)
        self.refresh_load_index_content()
        self.active_popup.after(
            10, lambda: [self.active_popup.deiconify(), self.active_popup.grab_set()]
        )

    def refresh_load_index_content(self):
        if not self.active_popup or self.active_popup_type != "load":
            return
        for widget in self.active_popup.winfo_children():
            widget.destroy()
        t = translations[self.lang]
        scroll = ctk.CTkScrollableFrame(self.active_popup)
        scroll.pack(fill="both", expand=True, padx=10, pady=10)

        # Bind mouse wheel events directly to the scroll frame itself for empty areas
        scroll.bind("<MouseWheel>", lambda e: self._handle_mousewheel_event(e, scroll)) # Windows/macOS
        scroll.bind("<Button-4>", lambda e: self._handle_mousewheel_event(e, scroll))   # Linux scroll up
        scroll.bind("<Button-5>", lambda e: self._handle_mousewheel_event(e, scroll))   # Linux scroll down
        app_dir = self.get_app_dir()
        db_files = sorted([f for f in os.listdir(app_dir) if f.endswith(".db")])
        if not db_files:
            ctk.CTkLabel(
                scroll,
                text=t.get("no_indexes_found", "No indexes"),
                font=("Arial", self.current_font_size),
            ).pack(pady=20)
            return
        for db_file in db_files:
            source_path = "Unknown path"
            try:
                temp_conn = self.get_db_connection(db_file)
                res = temp_conn.execute(
                    "SELECT value FROM info WHERE key='source_path'"
                ).fetchone()
                if res:
                    source_path = res[0]
                temp_conn.close()
            except:
                pass
            item_frame = ctk.CTkFrame(scroll)
            item_frame.pack(fill="x", pady=5, padx=5)

            # Text frame for index name and path
            text_frame = ctk.CTkFrame(item_frame, fg_color="transparent")
            text_frame.pack(fill="x", expand=True, padx=10, pady=5)
            ctk.CTkLabel(
                text_frame, text=db_file, font=("Arial", self.current_font_size, "bold")
            ).pack(anchor="w")
            ctk.CTkLabel(
                text_frame,
                text=source_path,
                font=("Arial", self.current_font_size),
                text_color="gray",
                wraplength=400,
            ).pack(anchor="w")

            # Button frame
            button_frame = ctk.CTkFrame(item_frame, fg_color="transparent")
            button_frame.pack(fill="x", expand=True, padx=10, pady=(5, 10))
            button_frame.grid_columnconfigure((0, 1), weight=1)

            ctk.CTkButton(
                button_frame,
                text=t.get("select", "Select"),
                height=STD_HEIGHT - 4,
                fg_color=PRIMARY_BLUE,
                command=lambda f=db_file: self.set_active_db(f, self.active_popup),
            ).grid(row=0, column=0, sticky="ew", padx=(0, 5))

            ctk.CTkButton(
                button_frame,
                text=t.get("delete_button", "Delete"),
                height=STD_HEIGHT - 4,
                fg_color="red",
                hover_color="#c00",
                command=lambda f=db_file: self.show_confirmation_dialog(
                    "delete_index_confirm_title",
                    "delete_index_confirm_message",
                    lambda: self.delete_index(f),
                ),
            ).grid(row=0, column=1, sticky="ew", padx=(5, 0))

            # THE FIX: Bind mouse wheel to this card and all its children
            # We pass 'scroll' so the handler knows which canvas to move
            self.bind_tree(item_frame, lambda e: self._handle_mousewheel_event(e, scroll))


        self.update_font_globally(self.active_popup)

    def show_confirmation_dialog(self, title_key, message_key, callback):
        t = translations[self.lang]
        dialog = self._manage_popup(t.get(title_key, title_key), "confirm")
        self.center_toplevel(dialog, 450, 200)
        dialog.grid_columnconfigure(0, weight=1)
        dialog.grid_rowconfigure((0, 2), weight=1)

        msg_label = ctk.CTkLabel(
            dialog,
            text=t.get(message_key, message_key),
            justify="center",
            wraplength=400,
        )
        msg_label.grid(row=1, column=0, padx=20, pady=10)

        button_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        button_frame.grid(row=3, column=0, pady=(0, 25))

        def on_confirm():
            callback()
            dialog.destroy()

        confirm_button = ctk.CTkButton(
            button_frame,
            text=t.get("confirm_button", "Confirm"),
            width=100,
            height=STD_HEIGHT,
            command=on_confirm,
            fg_color="red",
            hover_color="#c00",
        )
        confirm_button.pack(side="left", padx=10)

        cancel_button = ctk.CTkButton(
            button_frame,
            text=t.get("cancel_button", "Cancel"),
            width=100,
            height=STD_HEIGHT,
            command=dialog.destroy,
            fg_color=PRIMARY_BLUE,
            hover_color=HOVER_BLUE,
        )
        cancel_button.pack(side="right", padx=10)
        self.update_font_globally(dialog)
        dialog.after(10, lambda: [dialog.deiconify(), dialog.grab_set()])

    def delete_index(self, db_file):
        if self.db_path == db_file:
            self.db_path = None
            self.clear_search_results()
            self.update_ui_text()

        try:
            os.remove(os.path.join(self.get_app_dir(), db_file))
        except Exception as e:
            print(f"Error deleting index file: {e}")

        self.refresh_load_index_content()

    def _open_search_folder(self, event=None):
        if self.db_path:
            conn = self.get_db_connection()
            if conn:
                try:
                    res = conn.execute(
                        "SELECT value FROM info WHERE key='source_path'"
                    ).fetchone()
                    if res and os.path.exists(res[0]):
                        open_directory_in_explorer(res[0])
                except Exception as e:
                    print(f"Error opening search folder: {e}")
                finally:
                    conn.close()

    def set_active_db(self, db_file, window):
        print(f"DEBUG: set_active_db called with db_file={db_file}, window={window}")
        self.db_path = db_file
        self.clear_search_results()
        self.status_state = "index_loaded"
        self.update_ui_text()
        print(f"DEBUG: Destroying window {window}")
        window.destroy()
        print(f"DEBUG: Window destroyed. Checking pending search...")

        if hasattr(self, '_pending_search_after_index_selection') and self._pending_search_after_index_selection:
            print(f"DEBUG: Pending search found. Re-triggering start_search_thread.")
            self._pending_search_after_index_selection = False # Reset flag to avoid infinite loops
            self.after(0, self.start_search_thread) # Call start_search_thread on next idle cycle
        else:
            print(f"DEBUG: No pending search.")
        print(f"DEBUG: set_active_db finished.")

    def show_about(self):
        t = translations[self.lang]
        about_window = self._manage_popup(t["about_button"], "about")
        self.center_toplevel(about_window, 450, 320)
        about_window.grid_columnconfigure(0, weight=1)
        about_window.grid_rowconfigure((0, 3), weight=1)
        self.about_msg_label = ctk.CTkLabel(
            about_window, text="", justify="center", wraplength=400
        )
        self.about_msg_label.grid(row=1, column=0, padx=20, pady=(10, 5))
        self.about_link_label = ctk.CTkLabel(
            about_window,
            text=t["repo_label"],
            text_color=("#1f538d", "#5dade2"),
            cursor="hand2",
            font=("Arial", self.current_font_size, "underline"),
        )
        self.about_link_label.grid(row=2, column=0, pady=5)
        self.about_link_label.bind("<Button-1>", lambda e: webbrowser.open(REPO_URL))
        ok_btn = ctk.CTkButton(
            about_window,
            text="OK",
            width=100,
            height=STD_HEIGHT,
            command=about_window.destroy,
            fg_color=PRIMARY_BLUE,
            hover_color=HOVER_BLUE,
        )
        ok_btn.grid(row=4, column=0, pady=(0, 25))
        about_window.after(
            50, lambda: [about_window.deiconify(), about_window.grab_set()]
        )
        self.update_about_text()
        self.update_font_globally(about_window)

    def update_about_text(self):
        if self.active_popup and self.active_popup_type == "about":
            t = translations[self.lang]
            self.about_msg_label.configure(text=t["about_text"].format(version=VERSION))
            self.about_link_label.configure(text=t["repo_label"])

    def handle_web_click(self, path):
        current_url = self.url_entry.get().strip()
        if not current_url or "your-website.com" in current_url:
            self.show_custom_info("url_help_title", "url_help_msg")
            return
        filename = os.path.basename(path)
        match = re.search(r"l_(\d+)p(\d+)", filename)
        if match:
            lesson_id, page_id = match.group(1), match.group(2)
            sep = "&" if "?" in current_url else "?"
            webbrowser.open(
                f"{current_url}{sep}lesson_id={lesson_id}&page_id={page_id}"
            )

    def change_font_size(self, size):
        self.current_font_size = int(size)
        
        # Destroy existing option menus
        if hasattr(self, 'font_size_menu') and self.font_size_menu.winfo_exists():
            self.font_size_menu.destroy()
        if hasattr(self, 'lang_menu') and self.lang_menu.winfo_exists():
            self.lang_menu.destroy()

        self.update_ui_text() # This updates texts of other widgets
        self.update_font_globally(self) # This updates fonts of other widgets

        # Re-create option menus with the new font size
        self._create_option_menus(self.current_font_size)

    def update_slider_label(self, val):
        self.threshold_value_label.configure(text=str(int(val)))

    def toggle_theme(self):
        new_mode = "Dark" if self.theme_switch.get() else "Light"
        ctk.set_appearance_mode(new_mode)

        # After changing the theme, reset the buttons to their default non-hovered state
        if new_mode == "Light":
            self.load_index_button.configure(text_color="black", fg_color="transparent")
            self.about_button.configure(text_color="black", fg_color="transparent")
        else:  # Dark mode
            self.load_index_button.configure(text_color="white", fg_color="transparent")
            self.about_button.configure(text_color="white", fg_color="transparent")

    def change_language(self, new_lang):
        self.lang = new_lang
        self.update_ui_text()
        self.update_font_globally(self)
        if self.active_popup and self.active_popup.winfo_exists():
            self.update_font_globally(self.active_popup)

    def update_font_globally(self, master):
        for widget in master.winfo_children():
            try:
                if hasattr(widget, "configure") and not isinstance(
                    widget, (ctk.CTkScrollableFrame, ctk.CTkFrame)
                ):
                    widget.configure(font=ctk.CTkFont(size=self.current_font_size))
            except:
                pass
            if hasattr(widget, "winfo_children") and widget.winfo_children():
                self.update_font_globally(widget)

    def _create_option_menus(self, font_size):
        # Language Option Menu (Packed last, so visually at the very bottom)
        self.lang_menu = ctk.CTkOptionMenu(
            self.sidebar_frame,
            values=["en", "es", "pt"],
            height=STD_HEIGHT - 4, # Adjusted height
            command=self.change_language,
            fg_color=PRIMARY_BLUE,
            button_color=PRIMARY_BLUE,
            button_hover_color=HOVER_BLUE,
            font=ctk.CTkFont(size=font_size)
        )
        self.lang_menu.pack(side="bottom", padx=20, pady=(5, 5))
        self.lang_menu.set(self.lang) # Set initial selected value

        # Font Size Option Menu
        self.font_size_menu = ctk.CTkOptionMenu(
            self.sidebar_frame,
            values=["12", "14", "16", "18", "20"],
            height=STD_HEIGHT - 4, # Adjusted height
            command=self.change_font_size,
            fg_color=PRIMARY_BLUE,
            button_color=PRIMARY_BLUE,
            button_hover_color=HOVER_BLUE,
            font=ctk.CTkFont(size=font_size)
        )
        self.font_size_menu.pack(side="bottom", padx=20, pady=(5, 5))
        self.font_size_menu.set(str(font_size)) # Set initial selected value

        # Dark Mode Toggle (Packed before option menus, so visually above them)
        self.theme_switch = ctk.CTkSwitch(
            self.sidebar_frame,
            text="",
            command=self.toggle_theme,
            progress_color=PRIMARY_BLUE,
        )
        self.theme_switch.pack(side="bottom", padx=20, pady=(5, 5))
        
        # Sync switch with current system/theme mode
        if ctk.get_appearance_mode() == "Dark":
            self.theme_switch.select()
        else:
            self.theme_switch.deselect()

    def on_repeat_hover(self, event):
        if self.last_search_image:
            self.previous_status_text = self.status_label.cget("text")
            fname = os.path.basename(self.last_search_image)
            self.status_label.configure(
                text=f"Reuse: {fname}", text_color=("#1f538d", "#5dade2")
            )

    def on_repeat_leave(self, event):
        if hasattr(self, "previous_status_text"):
            self.status_label.configure(
                text=self.previous_status_text, text_color=("black", "white")
            )

    def update_ui_text(self):
        t = translations[self.lang]
        self.title(t["title"])
        self.index_button.configure(text=t["index_button"])
        self.search_button.configure(text=t["search_button"])
        self.load_index_button.configure(
            text=t.get("manage_indexes_button", "Manage Indexes")
        )
        self.label_threshold.configure(text=t["threshold_label"])
        self.url_label.configure(text=t["base_url"])
        self.theme_switch.configure(text=t["dark_mode"])
        self.about_button.configure(text=t["about_button"])

        if self.status_state == "complete":
            status_text = t["status_complete"]
        elif self.status_state == "searching":
            status_text = t["status_searching"]
        elif isinstance(self.status_state, int):
            status_text = t["found_matches"].format(count=self.status_state)
        elif self.status_state == "index_loaded":
            status_text = t.get("status_index_loaded", "Index Loaded")
        else:
            status_text = ""

        if self.status_state == "searching":
            self.status_label.configure(
                text=status_text,
                text_color=("black", "white"),
                fg_color=("#ffcb76", "#997a00")  # Amber/Gold (between yellow and orange)
            )
        else:
            self.status_label.configure(
                text=status_text,
                text_color=("black", "white"),
                fg_color="transparent"
            )
        self.previous_status_text = status_text

        source_path = None
        if self.db_path:
            try:
                conn = self.get_db_connection()
                res = conn.execute(
                    "SELECT value FROM info WHERE key='source_path'"
                ).fetchone()
                if res:
                    source_path = res[0]
                conn.close()
            except:
                pass

        if source_path:
            self.folder_info_label.configure(
                text=t.get("current_search_folder", "Search Folder:"),
                text_color=("black", "white"),  # Ensure consistency with other labels
            )
            self.folder_path_display.configure(
                text=source_path,
                fg_color=("gray90", "gray20"),
                text_color=("#1f538d", "#5dade2"),  # Light blue for dark mode
            )
        else:
            self.folder_info_label.configure(
                text="", text_color=("gray", "gray")
            )  # Ensure consistency
            self.folder_path_display.configure(
                text="",
                fg_color="transparent",
                text_color=("black", "white"),  # Default text color
            )

        if self.last_search_image:
            self.repeat_search_button.pack(side="right", padx=(5, 0))
        else:
            self.repeat_search_button.pack_forget()

        if self.active_popup and self.active_popup.winfo_exists():
            if self.active_popup_type == "about":
                self.active_popup.title(t["about_title"])
                self.update_about_text()
            elif self.active_popup_type == "load":
                self.active_popup.title(t.get("manage_indexes_title", "Manage Indexes"))
                self.refresh_load_index_content()
            elif self.active_popup_type == "info":
                self.active_popup.title(t.get(self.current_info_title_key, "Info"))
                if hasattr(self, "info_msg_label"):
                    self.info_msg_label.configure(
                        text=t.get(self.current_info_msg_key, "")
                    )

    def setup_ui(self):
        self.geometry("1200x800")
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.sidebar_frame = ctk.CTkFrame(self, width=250, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")

        self.logo_label = ctk.CTkLabel(
            self.sidebar_frame,
            text="SI FINDER",
            font=ctk.CTkFont(size=22, weight="bold"),
        )
        self.logo_label.pack(padx=20, pady=(30, 10))

        self.index_button = ctk.CTkButton(
            self.sidebar_frame,
            height=STD_HEIGHT,
            command=self.start_indexing_thread,
            fg_color=PRIMARY_BLUE,
            hover_color=HOVER_BLUE,
        )
        self.index_button.pack(padx=20, pady=5)

        search_container = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        search_container.pack(padx=20, pady=5)
        self.search_button = ctk.CTkButton(
            search_container,
            width=140,
            height=STD_HEIGHT,
            command=self.start_search_thread,
            fg_color=PRIMARY_BLUE,
            hover_color=HOVER_BLUE,
        )
        self.search_button.pack(side="left")
        self.repeat_search_button = ctk.CTkButton(
            search_container,
            text="↺",
            width=35,
            height=STD_HEIGHT,
            command=self.repeat_last_search,
            fg_color="transparent",
            border_width=1,
            text_color=("black", "white"),
        )
        self.repeat_search_button.bind("<Enter>", self.on_repeat_hover)
        self.repeat_search_button.bind("<Leave>", self.on_repeat_leave)

        def on_enter(button):
            # On hover, the style is the same for both themes
            button.configure(text_color="white", fg_color=HOVER_BLUE)

        def on_leave(button):
            # On leave, revert to theme-specific default
            if ctk.get_appearance_mode() == "Light":
                button.configure(text_color="black", fg_color="transparent")
            else:  # Dark mode
                button.configure(text_color="white", fg_color="transparent")

        self.load_index_button = ctk.CTkButton(
            self.sidebar_frame,
            height=STD_HEIGHT,
            command=self.show_load_index_window,
            fg_color="transparent",
            border_width=1,
            hover_color=HOVER_BLUE,
            text_color=("black", "white"),
        )
        self.load_index_button.bind(
            "<Enter>", lambda event, b=self.load_index_button: on_enter(b)
        )
        self.load_index_button.bind(
            "<Leave>", lambda event, b=self.load_index_button: on_leave(b)
        )
        self.load_index_button.pack(padx=20, pady=10)

        self.progress_bar = ctk.CTkProgressBar(
            self.sidebar_frame, progress_color=PRIMARY_BLUE
        )
        self.progress_bar.pack(padx=20, pady=10)
        self.progress_bar.set(0)
        self.status_label = ctk.CTkLabel(
            self.sidebar_frame, text="", font=ctk.CTkFont(size=11), wraplength=210, width=210
        )
        self.status_label.pack(padx=20, pady=0)
        self.folder_info_label = ctk.CTkLabel(
            self.sidebar_frame, text="", font=ctk.CTkFont(size=10), text_color="gray"
        )
        self.folder_info_label.pack(padx=20, pady=(10, 0), anchor="w")
        self.folder_path_display = ctk.CTkLabel(
            self.sidebar_frame,
            text="",
            font=ctk.CTkFont(size=10, weight="bold"),
            wraplength=210,
            justify="left",
            corner_radius=6,
            padx=10,
            pady=5,
            cursor="hand2",  # Indicate clickable
        )
        self.folder_path_display.pack(padx=20, pady=(2, 5), anchor="w", fill="x")
        self.folder_path_display.bind("<Button-1>", self._open_search_folder)

        ctk.CTkLabel(self.sidebar_frame, text="", height=20).pack()
        thresh_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        thresh_frame.pack(padx=20, fill="x")
        self.label_threshold = ctk.CTkLabel(thresh_frame, text="")
        self.label_threshold.pack(side="left")
        ctk.CTkButton(
            thresh_frame,
            text="?",
            width=20,
            height=20,
            corner_radius=10,
            command=lambda: self.show_custom_info("sens_help_title", "sens_help_msg"),
            fg_color=PRIMARY_BLUE,
            hover_color=HOVER_BLUE,
        ).pack(side="right")

        self.threshold_slider = ctk.CTkSlider(
            self.sidebar_frame,
            from_=0,
            to=20,
            number_of_steps=20,
            command=self.update_slider_label,
            button_color=PRIMARY_BLUE,
            button_hover_color=HOVER_BLUE,
            progress_color=PRIMARY_BLUE,
        )
        self.threshold_slider.pack(padx=20, pady=(5, 0))
        self.threshold_slider.set(8)
        self.threshold_value_label = ctk.CTkLabel(
            self.sidebar_frame, text="8", font=ctk.CTkFont(size=11, weight="bold")
        )
        self.threshold_value_label.pack(padx=20, pady=(0, 0))

        url_header = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        url_header.pack(padx=20, pady=(15, 0), fill="x")
        self.url_label = ctk.CTkLabel(url_header, text="", font=ctk.CTkFont(size=11))
        self.url_label.pack(side="left")
        ctk.CTkButton(
            url_header,
            text="?",
            width=20,
            height=20,
            corner_radius=10,
            command=lambda: self.show_custom_info("url_help_title", "url_help_msg"),
            fg_color=PRIMARY_BLUE,
            hover_color=HOVER_BLUE,
        ).pack(side="right")

        self.url_entry = ctk.CTkEntry(self.sidebar_frame, height=STD_HEIGHT)
        self.url_entry.pack(padx=20, pady=5, fill="x")
        self.url_entry.insert(0, DEFAULT_URL)

        # Spacer to push elements up
        spacer = ctk.CTkLabel(self.sidebar_frame, text="")
        spacer.pack(expand=True, fill="both")

        self.about_button = ctk.CTkButton(
            self.sidebar_frame,
            height=STD_HEIGHT,
            command=self.show_about,
            fg_color="transparent",
            border_width=1,
            hover_color=HOVER_BLUE,
            text_color=("black", "white"),
        )
        self.about_button.bind(
            "<Enter>", lambda event, b=self.about_button: on_enter(b)
        )
        self.about_button.bind(
            "<Leave>", lambda event, b=self.about_button: on_leave(b)
        )
        self.about_button.pack(side="bottom", padx=20, pady=(20, 20))





        # Call helper method to create option menus
        self._create_option_menus(self.current_font_size)

        self.scrollable_frame = ctk.CTkScrollableFrame(self)
        self.scrollable_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        self.scrollable_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        # Bind keyboard events for scrolling
        self.scrollable_frame.bind("<Prior>", self._on_scroll_page_up)
        self.scrollable_frame.bind("<Next>", self._on_scroll_page_down)
        self.scrollable_frame.bind("<Home>", self._on_scroll_home)
        self.scrollable_frame.bind("<End>", self._on_scroll_end)
        # Bind mouse wheel for consistency/explicit control if default isn't working
        self.scrollable_frame.bind("<MouseWheel>", self._on_mouse_wheel) # Windows/macOS
        self.scrollable_frame.bind("<Button-4>", self._on_mouse_wheel) # Linux scroll up
        self.scrollable_frame.bind("<Button-5>", self._on_mouse_wheel) # Linux scroll down

        # Explicitly manage focus for scrolling
        self.scrollable_frame.bind("<Enter>", lambda event: self.scrollable_frame.focus_set())
        self.scrollable_frame.bind("<Leave>", lambda event: self.focus_set())

    def _on_scroll_page_up(self, event):
        self.scrollable_frame._parent_canvas.yview_scroll(-1, "pages")

    def _on_scroll_page_down(self, event):
        self.scrollable_frame._parent_canvas.yview_scroll(1, "pages")

    def _on_scroll_home(self, event):
        self.scrollable_frame._parent_canvas.yview_moveto(0)

    def _on_scroll_end(self, event):
        self.scrollable_frame._parent_canvas.yview_moveto(1)

    def _on_mouse_wheel(self, event):
        # Determine scroll direction and amount based on OS/event type
        if sys.platform == "darwin": # macOS
            self.scrollable_frame._parent_canvas.yview_scroll(-int(event.delta/abs(event.delta)), "units")
        elif sys.platform == "win32": # Windows
            self.scrollable_frame._parent_canvas.yview_scroll(-int(event.delta/120), "units")
        else: # Linux
            if event.num == 4: # Scroll up
                self.scrollable_frame._parent_canvas.yview_scroll(-1, "units")
            elif event.num == 5: # Scroll down
                self.scrollable_frame._parent_canvas.yview_scroll(1, "units")

    def repeat_last_search(self):
        if self.last_search_image and os.path.exists(self.last_search_image):
            if not self.db_path:
                self.show_load_index_window()
                return
            threading.Thread(
                target=self.run_search, args=(self.last_search_image,), daemon=True
            ).start()
        else:
            self.last_search_image = None
            self.update_ui_text()

    def start_indexing_thread(self):
        folder = filedialog.askdirectory()
        if not folder:
            return
        self.clear_search_results()
        path_hash = hashlib.md5(folder.encode()).hexdigest()[:6]
        self.db_path = f"{os.path.basename(os.path.normpath(folder))}_{path_hash}.db"
        self.index_button.configure(state="disabled")
        self.search_button.configure(state="disabled")
        self.repeat_search_button.configure(state="disabled")
        self.load_index_button.configure(state="disabled")
        threading.Thread(target=self.run_indexing, args=(folder,), daemon=True).start()

    def run_indexing(self, folder):
        conn = None
        try:
            path_to_db = os.path.join(self.get_app_dir(), self.db_path)
            conn = sqlite3.connect(path_to_db, timeout=10)
            cursor = conn.cursor()
            cursor.execute(
                "CREATE TABLE IF NOT EXISTS images (path TEXT UNIQUE, hash TEXT, last_modified REAL)"
            )
            cursor.execute(
                "CREATE TABLE IF NOT EXISTS info (key TEXT UNIQUE, value TEXT)"
            )
            cursor.execute(
                "INSERT OR REPLACE INTO info VALUES (?, ?)", ("source_path", folder)
            )
            valid_exts = (".png", ".jpg", ".jpeg", ".webp")
            files = [
                os.path.join(folder, f)
                for f in os.listdir(folder)
                if f.lower().endswith(valid_exts)
            ]
            total = len(files)
            for i, path in enumerate(files):
                try:
                    mtime = os.path.getmtime(path)
                    cursor.execute(
                        "SELECT last_modified FROM images WHERE path=?", (path,)
                    )
                    row = cursor.fetchone()
                    if not row or row[0] != mtime:
                        with Image.open(path) as img:
                            h = str(imagehash.phash(img))
                        cursor.execute(
                            "INSERT OR REPLACE INTO images VALUES (?, ?, ?)",
                            (path, h, mtime),
                        )
                    if i % 10 == 0:
                        self.after(0, lambda v=i / total: self.progress_bar.set(v))
                        self.after(
                            0,
                            lambda v=f"{i}/{total}": self.status_label.configure(
                                text=v
                            ),
                        )
                except:
                    continue
            conn.commit()
        except sqlite3.OperationalError as e:
            print(f"Database error: {e}")
        finally:
            if conn:
                conn.close()
        self.status_state = "complete"
        self.after(0, self.update_ui_text)
        self.after(0, lambda: self.index_button.configure(state="normal"))
        self.after(0, lambda: self.search_button.configure(state="normal"))
        self.after(0, lambda: self.repeat_search_button.configure(state="normal"))
        self.after(0, lambda: self.load_index_button.configure(state="normal"))
        self.after(
            200, lambda: self.show_custom_info("status_complete", "indexing_done")
        )

    def start_search_thread(self):
        if not self.db_path:
            # If no search folder is available, display an informative message
            self.show_custom_info("search_folder_missing_title", "search_folder_missing_msg")
            return
        
        # If a search folder is available, proceed to open the file explorer for image selection
        # The _pending_search_after_index_selection flag (and its usage in set_active_db) is
        # kept to allow for re-triggering this method if an index was just selected, but
        # it doesn't control the initial flow here.
        if hasattr(self, '_pending_search_after_index_selection'): # Only reset if it exists
            self._pending_search_after_index_selection = False 
        target_path = filedialog.askopenfilename()
        if not target_path:
            return
        self.last_search_image = target_path
        self.update_ui_text()
        threading.Thread(
            target=self.run_search, args=(target_path,), daemon=True
        ).start()

    def run_search(self, target_path):
        try:
            with Image.open(target_path) as img:
                target_hash = imagehash.phash(img)
        except Exception as e:
            self.after(
                0,
                lambda: self.show_custom_info(
                    "error_loading",
                    f"Invalid image file: {os.path.basename(target_path)}",
                ),
            )
            self.status_state = None
            self.after(0, self.update_ui_text)
            return

        self.status_state = "searching"
        self.after(0, self.update_ui_text)
        self.after(
            0, lambda: [w.destroy() for w in self.scrollable_frame.winfo_children()]
        )
        conn = self.get_db_connection()
        if not conn:
            return
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='images'"
        )
        if not cursor.fetchone():
            conn.close()
            self.status_state = 0
            self.after(0, self.update_ui_text)
            return
        cursor.execute("SELECT path, hash FROM images")
        matches, threshold, all_data = (
            [],
            self.threshold_slider.get(),
            cursor.fetchall(),
        )
        for i, (path, h_str) in enumerate(all_data):
            if not os.path.exists(path):
                continue
            dist = target_hash - imagehash.hex_to_hash(h_str)
            if dist <= threshold:
                matches.append((dist, path))
            if i % 100 == 0:
                self.after(0, lambda v=i / len(all_data): self.progress_bar.set(v))
        matches.sort(key=lambda x: x[0])
        conn.close()
        self.status_state = len(matches)
        self.after(0, self.update_ui_text)
        self.after(0, lambda: self.display_matches(matches))

    def clear_search_results(self):
        self.status_state = None
        self.thumbnails = []
        widgets = self.scrollable_frame.winfo_children()
        for i, widget in enumerate(reversed(widgets)):
            self.after(i * 30, widget.destroy)

        # Schedule the UI update after the last widget has been told to destroy
        self.after(len(widgets) * 30, self.update_ui_text)


    def display_matches(self, matches):
        self.thumbnails = []
        try:
            globe_p, folder_p = resource_path("assets/images/globe.png"), resource_path(
                "assets/images/folder.png"
            )
            self.ctk_globe, self.ctk_folder = self._load_icons(globe_p, folder_p)
        except:
            self.ctk_globe = self.ctk_folder = None

        for i, (dist, path) in enumerate(matches):
            # Pass necessary data to the worker thread
            threading.Thread(
                target=self._process_and_create_card_thread,
                args=(i, dist, path),
                daemon=True
            ).start()

    def _load_icons(self, globe_p, folder_p):
        globe_img = Image.open(globe_p).resize((20, 20))
        folder_img = Image.open(folder_p).resize((20, 20))
        ctk_globe = ctk.CTkImage(
            light_image=globe_img, dark_image=globe_img, size=(20, 20)
        )
        ctk_folder = ctk.CTkImage(
            light_image=folder_img, dark_image=folder_img, size=(20, 20)
        )
        return ctk_globe, ctk_folder

    def _process_and_create_card_thread(self, i, dist, path):
        """Worker thread to process image and schedule card creation on main thread."""
        try:
            raw_img = Image.open(path)
            raw_img.thumbnail((120, 120))  # Scale to fit within 120x120
            ctk_img = ctk.CTkImage(
                light_image=raw_img,
                dark_image=raw_img,
                size=raw_img.size,  # Use actual size after thumbnail
            )
            # Schedule the actual UI creation on the main thread
            self.after(0, lambda: self.winfo_exists() and self._create_match_card_ui(i, dist, path, ctk_img))
        except Exception as e:
            logging.exception(f"Error processing image in thread: {path}")
            # Schedule an error card creation or message on the main thread
            self.after(0, lambda: self.winfo_exists() and self._create_match_card_error(i, dist, path))


    def _create_match_card_error(self, i, dist, path):
        """Creates an error match card UI element on the main thread."""
        card = ctk.CTkFrame(self.scrollable_frame)
        card.grid(row=i // 4, column=i % 4, padx=10, pady=10, sticky="nsew")
        ctk.CTkLabel(card, text="Error loading image").pack(pady=40)
        ctk.CTkLabel(
            card,
            text=os.path.basename(path),
            font=("Arial", self.current_font_size, "bold"),
            wraplength=120,
        ).pack(pady=0)
        ctk.CTkLabel(
            card,
            text=f"Dist: {int(dist)}",
            font=("Arial", self.current_font_size - 2),
            text_color=("gray30", "gray70"),
        ).pack(pady=(0, 5))
        # No buttons for error cards, or add if desired

        # Bind scroll events for all widgets in this card to the main scrollable frame
        self.bind_tree(card, lambda e: self._handle_mousewheel_event(e, self.scrollable_frame))

    def _create_match_card_ui(self, i, dist, path, ctk_img):
        card = ctk.CTkFrame(self.scrollable_frame)
        card.grid(row=i // 4, column=i % 4, padx=10, pady=10, sticky="nsew")
        self.thumbnails.append(ctk_img) # Keep reference
        ctk.CTkLabel(card, image=ctk_img, text="").pack(pady=5)
        ctk.CTkLabel(
            card,
            text=os.path.basename(path),
            font=("Arial", self.current_font_size, "bold"),
            wraplength=120,
        ).pack(pady=0)
        ctk.CTkLabel(
            card,
            text=f"Dist: {int(dist)}",
            font=("Arial", self.current_font_size - 2),
            text_color=("gray30", "gray70"),
        ).pack(pady=(0, 5))
        btn_frame = ctk.CTkFrame(card, fg_color="transparent")
        btn_frame.pack(pady=5)
        ctk.CTkButton(
            btn_frame,
            image=self.ctk_globe,
            text="" if self.ctk_globe else "Web",
            width=30,
            height=30,
            fg_color="transparent",
            hover_color=("gray80", "gray20"),
            command=lambda p=path: self.handle_web_click(p),
        ).pack(side="left", padx=5)
        ctk.CTkButton(
            btn_frame,
            image=self.ctk_folder,
            text="" if self.ctk_folder else "File",
            width=30,
            height=30,
            fg_color="transparent",
            hover_color=("gray80", "gray20"),
            command=lambda p=path: reveal_file_in_explorer(p),
        ).pack(side="left", padx=5)

        # Bind scroll events for all widgets in this card to the main scrollable frame
        self.bind_tree(card, lambda e: self._handle_mousewheel_event(e, self.scrollable_frame))


if __name__ == "__main__":
    app = ImageFinderApp()
    app.mainloop()
