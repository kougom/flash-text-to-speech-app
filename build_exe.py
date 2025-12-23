import os
import subprocess
from PIL import Image

def convert_icon(png_path, ico_path):
    print(f"Converting {png_path} to {ico_path}...")
    img = Image.open(png_path)
    img.save(ico_path, format='ICO', sizes=[(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)])
    print("Icon conversion complete.")

def build_exe():
    png_icon = "icon.png"
    ico_icon = "icon.ico"
    
    if os.path.exists(png_icon):
        convert_icon(png_icon, ico_icon)
    else:
        print(f"Warning: {png_icon} not found, skipping icon conversion.")

    # PyInstaller command
    # --onefile: Create a single executable
    # --noconsole: Don't show terminal window
    # --icon: Use the specified icon
    # --add-data: Include .env and icon.png (needed for system tray)
    # Note: On Windows, use ';' as separator for --add-data
    
    cmd = [
        "python", "-m", "PyInstaller",
        "--noconsole",
        "--onefile",
        f"--icon={ico_icon}",
        "--add-data", ".env;.",
        "--add-data", "icon.png;.",
        "--collect-all", "google.generativeai",
        "--name", "FlashSTT",
        "main.py"
    ]
    
    print(f"Running command: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)
    print("\nBuild complete! Check the 'dist' folder for FlashSTT.exe")

if __name__ == "__main__":
    build_exe()
