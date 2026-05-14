import sys
import os
import json
import time
import threading
import logging
from datetime import datetime
from io import BytesIO

import requests
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QCheckBox, QSystemTrayIcon,
    QMenu, QMessageBox, QFrame, QStackedWidget, QWidget
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize
from PyQt6.QtGui import QIcon, QFont, QPixmap, QColor

# Optional imports for monitoring
import platform
if platform.system() == 'Windows':
    import winreg
    import winshell # For shortcuts
    from win32com.client import Dispatch
    HAS_WINDOWS_LIBS = True
else:
    HAS_WINDOWS_LIBS = False

try:
    import mss
    HAS_MSS = True
except ImportError:
    HAS_MSS = False

try:
    from pynput import keyboard
    HAS_PYNPUT = True
except ImportError:
    HAS_PYNPUT = False

try:
    if sys.platform == 'win32':
        import win32gui
        import win32process
        import psutil
        HAS_WIN32 = True
    else:
        HAS_WIN32 = False
except ImportError:
    HAS_WIN32 = False

# ─── Configuration ───────────────────────────────────────────

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'monitor_config.json')
ICON_NAME = 'nsda_logo_icon_1778726323612.png'
ICON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ICON_NAME)

APP_VERSION = "1.0.0"

DEFAULT_CONFIG = {
    "server_url": "http://127.0.0.1:8080",
    "username": "",
    "password": "",
    "screenshot_interval": 300,
    "app_tracking_interval": 30,
    "keyboard_report_interval": 300,
    "idle_threshold": 120,
    "monitoring_enabled": False,
    "first_run": True
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return {**DEFAULT_CONFIG, **json.load(f)}
        except:
            return DEFAULT_CONFIG
    return DEFAULT_CONFIG

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

# ─── Worker Thread ───────────────────────────────────────────

class MonitorWorker(QThread):
    status_updated = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, config):
        super().__init__()
        self.config = config
        self.running = False
        self.session_id = None

    def run(self):
        self.running = True
        self.status_updated.emit("Monitoring Active")
        
        server_url = self.config['server_url'].rstrip('/')
        session = requests.Session()
        session.auth = (self.config['username'], self.config['password'])

        # 1. Start Session
        try:
            resp = session.post(f"{server_url}/monitoring/api/session/start/", timeout=10)
            if resp.status_code == 201:
                self.session_id = resp.json().get('id')
            else:
                self.error_occurred.emit(f"Failed to start session: {resp.status_code}")
                return
        except Exception as e:
            self.error_occurred.emit(f"Connection failed: {str(e)}")
            return

        # 2. Main Loop
        last_screenshot = 0
        while self.running:
            try:
                now = time.time()
                
                # App Tracking & Idle Check
                # (Simplified for this script - logic goes here)
                
                # Periodic Screenshot
                if HAS_MSS and (now - last_screenshot >= self.config['screenshot_interval']):
                    with mss.mss() as sct:
                        img = sct.grab(sct.monitors[1])
                        from PIL import Image
                        img_obj = Image.frombytes("RGB", img.size, img.bgra, "raw", "BGRX")
                        output = BytesIO()
                        img_obj.save(output, format='JPEG', quality=70)
                        
                        session.post(
                            f"{server_url}/monitoring/api/screenshot/",
                            files={'image': ('ss.jpg', output.getvalue(), 'image/jpeg')},
                            data={'session': self.session_id},
                            timeout=10
                        )
                    last_screenshot = now
                
                time.sleep(5)
            except Exception as e:
                print(f"Loop error: {e}")
                time.sleep(10)

    def stop(self):
        self.running = False
        if self.session_id:
            try:
                server_url = self.config['server_url'].rstrip('/')
                requests.post(
                    f"{server_url}/monitoring/api/session/{self.session_id}/end/",
                    auth=(self.config['username'], self.config['password']),
                    timeout=5
                )
            except:
                pass
        self.status_updated.emit("Monitoring Stopped")

# ─── UI Components ───────────────────────────────────────────

class WelcomeDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Welcome to NSDA Portal")
        self.setFixedSize(400, 350)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setStyleSheet("background-color: white; border-radius: 15px; border: 1px solid #e2e8f0;")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        
        logo_label = QLabel()
        if os.path.exists(ICON_PATH):
            logo_label.setPixmap(QPixmap(ICON_PATH).scaled(80, 80, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(logo_label)
            
        title = QLabel("Enable Monitoring?")
        title.setStyleSheet("font-size: 20px; font-weight: 800; color: #1e3a8a; margin-top: 10px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        desc = QLabel("NSDA Portal requires background monitoring to track attendance and progress. Do you allow this workstation to be monitored?")
        desc.setStyleSheet("color: #64748b; line-height: 1.5; margin: 15px 0;")
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc)
        
        btn_layout = QHBoxLayout()
        self.btn_allow = QPushButton("Allow Monitoring")
        self.btn_allow.setStyleSheet("background-color: #2563eb; color: white; padding: 12px; border-radius: 8px; font-weight: bold;")
        self.btn_allow.clicked.connect(self.accept)
        
        self.btn_cancel = QPushButton("Maybe Later")
        self.btn_cancel.setStyleSheet("background-color: #f1f5f9; color: #475569; padding: 12px; border-radius: 8px;")
        self.btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_allow)
        layout.addLayout(btn_layout)

class SettingsWindow(QMainWindow):
    def __init__(self, config, worker):
        super().__init__()
        self.config = config
        self.worker = worker
        self.setWindowTitle("NSDA Monitor Dashboard")
        self.setFixedSize(450, 620)
        self.setStyleSheet("""
            QMainWindow { background-color: #ffffff; }
            QLabel { color: #334155; font-weight: 500; }
            QLineEdit { padding: 12px; border: 1px solid #e2e8f0; border-radius: 8px; background: #f8fafc; color: #1e293b; }
            QLineEdit:focus { border: 2px solid #2563eb; background: white; }
        """)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)

        # ─── Update Banner ───
        self.update_banner = QFrame()
        self.update_banner.setStyleSheet("background: #fef9c3; border-radius: 8px; border: 1px solid #fde047;")
        ub_layout = QHBoxLayout(self.update_banner)
        self.update_label = QLabel("A new version is available!")
        self.update_label.setStyleSheet("color: #854d0e; font-weight: 600; border: none;")
        self.update_btn = QPushButton("Download Update")
        self.update_btn.setStyleSheet("background: #ca8a04; color: white; border: none; padding: 5px 10px; border-radius: 4px;")
        ub_layout.addWidget(self.update_label)
        ub_layout.addWidget(self.update_btn)
        self.update_banner.hide()
        layout.addWidget(self.update_banner)
        
        # ─── Status Card ───
        status_card = QFrame()
        status_card.setStyleSheet("background: #f8fafc; border-radius: 12px; border: 1px solid #e2e8f0;")
        status_layout = QVBoxLayout(status_card)
        
        self.status_val = QLabel("OFFLINE")
        self.status_val.setStyleSheet("font-size: 24px; font-weight: 800; color: #ef4444; border: none;")
        status_layout.addWidget(self.status_val)
        
        self.btn_toggle = QPushButton("START MONITORING")
        self.btn_toggle.setMinimumHeight(50)
        self.btn_toggle.clicked.connect(self.toggle_monitoring)
        status_layout.addWidget(self.btn_toggle)
        layout.addWidget(status_card)
        
        # ─── Credentials ───
        layout.addWidget(QLabel("Portal URL"))
        self.url_input = QLineEdit(self.config['server_url'])
        layout.addWidget(self.url_input)
        
        layout.addWidget(QLabel("Username"))
        self.user_input = QLineEdit(self.config['username'])
        layout.addWidget(self.user_input)
        
        layout.addWidget(QLabel("Password"))
        self.pass_input = QLineEdit(self.config['password'])
        self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.pass_input)
        
        self.btn_save = QPushButton("Save Credentials")
        self.btn_save.setStyleSheet("background: #f1f5f9; padding: 12px; border-radius: 8px; font-weight: bold;")
        self.btn_save.clicked.connect(self.save_settings)
        layout.addWidget(self.btn_save)
        
        self.worker.status_updated.connect(self.update_ui)
        self.update_ui("Monitoring Stopped")
        self.check_for_updates()

    def check_for_updates(self):
        def run_check():
            try:
                resp = requests.get(f"{self.config['server_url'].rstrip('/')}/monitoring/api/check-update/", auth=(self.config['username'], self.config['password']), timeout=5)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get('version') != APP_VERSION:
                        self.update_label.setText(f"Update Available: v{data.get('version')}")
                        self.update_btn.clicked.connect(lambda: os.startfile(data.get('download_url')))
                        self.update_banner.show()
            except: pass
        threading.Thread(target=run_check, daemon=True).start()

    def update_ui(self, status):
        active = "Active" in status
        self.status_val.setText("ACTIVE" if active else "OFFLINE")
        self.status_val.setStyleSheet(f"font-size: 24px; font-weight: 800; color: {'#10b981' if active else '#ef4444'}; border: none;")
        self.btn_toggle.setText("STOP MONITORING" if active else "START MONITORING")
        self.btn_toggle.setStyleSheet(f"background: {'#fee2e2' if active else '#2563eb'}; color: {'#ef4444' if active else 'white'}; border-radius: 8px; font-weight: bold;")

    def toggle_monitoring(self):
        if self.worker.isRunning():
            self.worker.stop()
        else:
            if not self.config['username']: return
            self.worker.start()

    def save_settings(self):
        self.config.update({'server_url': self.url_input.text(), 'username': self.user_input.text(), 'password': self.pass_input.text()})
        save_config(self.config)
        QMessageBox.information(self, "Saved", "Credentials updated.")

# ─── Main Logic ──────────────────────────────────────────────

class NSDAAgent:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.config = load_config()
        self.worker = MonitorWorker(self.config)
        
        self.tray = QSystemTrayIcon(QIcon(ICON_PATH) if os.path.exists(ICON_PATH) else QIcon())
        self.menu = QMenu()
        self.menu.addAction("Dashboard", self.show_dashboard)
        self.menu.addAction("Exit", self.quit)
        self.tray.setContextMenu(self.menu)
        self.tray.show()
        
        self.window = SettingsWindow(self.config, self.worker)
        
        if self.config.get('first_run', True):
            if WelcomeDialog().exec():
                self.config['first_run'] = False
                save_config(self.config)
                self.show_dashboard()
        elif self.config.get('monitoring_enabled'):
            self.worker.start()

    def show_dashboard(self):
        self.window.show()

    def quit(self):
        self.worker.stop()
        self.app.quit()

    def run(self):
        return self.app.exec()

if __name__ == "__main__":
    sys.exit(NSDAAgent().run())
