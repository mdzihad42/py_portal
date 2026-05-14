import os
import subprocess
import sys

def build():
    print("Starting Build Process for NSDA Monitor...")
    
    # Dependencies check
    try:
        import PyInstaller
    except ImportError:
        print("PyInstaller not found. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller winshell pywin32"])

    # Path setup
    script_path = "monitor_gui.py"
    icon_path = "nsda_logo_icon_1778726323612.png"
    
    if not os.path.exists(script_path):
        print(f"Error: {script_path} not found.")
        return

    # Build Command
    # --onefile: Create a single executable
    # --windowed: No console window
    # --icon: Set the application icon
    # --add-data: Include the icon in the build
    
    command = [
        "pyinstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",
        f"--icon={icon_path}" if os.path.exists(icon_path) else "",
        f"--add-data={icon_path};." if os.path.exists(icon_path) else "",
        "--name=NSDA_Monitor",
        script_path
    ]
    
    # Filter empty strings
    command = [c for c in command if c]
    
    print(f"Running command: {' '.join(command)}")
    
    try:
        subprocess.check_call(command)
        print("\n" + "="*50)
        print("SUCCESS: Build complete!")
        print(f"Your executable is located in the 'dist' folder: {os.path.abspath('dist/NSDA_Monitor.exe')}")
        print("="*50)
    except subprocess.CalledProcessError as e:
        print(f"Build failed with error: {e}")

if __name__ == "__main__":
    build()
