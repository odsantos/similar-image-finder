# SI Finder - Similar Image Finder

A lightweight, cross-platform desktop application designed to find visually similar images within a directory using Perceptual Hashing (pHash).

![Version](https://img.shields.io/badge/version-1.0.0-teal)
![License](https://img.shields.io/badge/license-MIT-blue)
![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20Windows%20%7C%20macOS-lightgrey)

## 🚀 Features

- **Visual Search:** Find images that "look" like your target, even if they have different filenames or resolutions.
- **Thumbnail Grid:** View matches in a responsive, modern gallery layout.
- **Multi-language Support:** Fully localized in English and Portuguese.
- **Adjustable Sensitivity:** Use the threshold slider to find exact duplicates or loose variations.
- **Fast Indexing:** Uses an SQLite database to remember image hashes, making subsequent searches near-instant.
- **Independent & Portable:** No installation required. Available as AppImage (Linux), ZIP (macOS), and EXE (Windows).

## 🛠️ Installation

Simply download the latest version from the [Releases](https://github.com/odsantos/similar-image-finder/releases) page.

- **Windows:** Download the `.zip`, extract, and run `SI-Finder.exe`.
- **Linux:** Download the `.AppImage`, make it executable (`chmod +x`), and run.
- **macOS:** Download the `.zip`, extract, and move to your Applications folder.

## 📖 How to Use

1. **Index:** Click "Index Directory" and select the folder containing your images (e.g., your website's assets).
2. **Adjust:** Set the "Sensitivity" slider. Lower numbers mean the images must be almost identical.
3. **Search:** Click "Search Similar Image" and select the image you want to find variations of.
4. **Browse:** Results with thumbnails and "Distance" scores will appear in the grid.

## 🏗️ Development

If you want to run the source code locally:

```bash
# Clone the repository
git clone [https://github.com/odsantos/similar-image-finder.git](https://github.com/odsantos/similar-image-finder.git)
cd similar-image-finder

# Install dependencies
pip install customtkinter pillow imagehash
```

## 📄 License

Distributed under the MIT License. See [LICENSE](./LICENSE) file for the full text.

Developed by [osantos](https://github.com/odsantos)