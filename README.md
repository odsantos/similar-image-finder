# SI Finder - Similar Image Finder

A lightweight, cross-platform desktop application designed to find visually similar images within a directory using Perceptual Hashing (pHash).

![Version](https://img.shields.io/badge/version-1.2.3-teal)
![License](https://img.shields.io/badge/license-MIT-blue)
![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20Windows%20%7C%20macOS-lightgrey)

## 🚀 Features

- **Visual Search:** Find images that "look" like your target, even if they have different filenames or resolutions.
- **Thumbnail Grid:** View matches in a responsive, modern gallery layout.
- **Web Integration:** Open related webpages directly from results if filenames follow the `l_IDp_ID` pattern.
- **Multi-language Support:** Fully localized in **English, Spanish, and Portuguese**.
- **Adjustable Sensitivity:** Use the threshold slider to find exact duplicates or loose variations.
- **Fast Indexing:** Uses an SQLite database to remember image hashes, making subsequent searches near-instant.
- **Independent & Portable:** No installation required.

## 📥 Get the App

### 💎 Professional Builds (Recommended)

For the best experience, download the pre-compiled official bundles. These require no technical setup—just extract and run.

- **[Download for Windows, macOS, & Linux on Gumroad](https://osvaldosantos.gumroad.com/)**

> **Note on Assets:** When uncompressing the ZIP asset, you will find a direct folder for macOS and an `.exe` for Windows. Files are located in the root of the archive, not inside a `dist` folder.

*Purchasing a build helps support the continued development and maintenance of this project!*

### 🛠️ Build from Source (Advanced)

If you prefer to run the application using your own Python environment:

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/odsantos/similar-image-finder.git](https://github.com/odsantos/similar-image-finder.git)
   cd similar-image-finder
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application:**
   ```bash
   python main.py
   ```

## 📖 How to Use

1. **Index:** Click "Index Folder" and select the directory containing your images.
2. **Search:** Click "Search Image" and select the reference image to find similar items.
3. **Adjust (Optional):** If you want more or fewer results, move the "Sensitivity" slider. 
   - **Lower numbers (0-5):** Best for finding exact duplicates.
   - **Higher numbers (10+):** Best for finding looser variations.
4. **Browse:** Results appear in the grid. Click the **Globe** icon for web links or the **Folder** icon to locate the file on your computer.

## 📄 License
 
Distributed under the MIT License. See [LICENSE](./LICENSE) file for the full text.

---

### AI Collaboration Credit
This project was developed through a collaborative process between **Osvaldo Santos** ([@odsantos](https://github.com/odsantos)) and **Gemini (Google AI)**. While the logic and architecture were AI-assisted, the final oversight, deployment, and ownership belong to the human author.
