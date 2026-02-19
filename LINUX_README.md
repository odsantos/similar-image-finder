# SI Finder - Installation Guide (Linux)

Welcome to SI Finder! This is a "Setup-once" portable application.

## How to Install

1. **Extract** this ZIP file.
2. **Double-click** the `SI-Finder` binary (or run `./SI-Finder` in a terminal).
3. **Setup Logic**: The first time you run it, the app will automatically:
   - Copy itself to your system (`~/.local/share/SI-Finder/`).
   - Create a shortcut in your **Applications Menu**.
4. **Clean Up**: Once you see the "Installation Successful" message, you can safely **delete this extraction folder**.

## How to Uninstall

If you wish to remove the application and its shortcut:

1. **Remove Shortcut**: Run `rm ~/.local/share/applications/si_finder.desktop` in your terminal.
2. **Remove App Data**: Run `rm -rf ~/.local/share/SI-Finder/` to delete the binary and settings.

---
*Portable & Private - No Root/Sudo required.*
