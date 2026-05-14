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
# Note: Use the actual generated image name from the environment
ICON_NAME = 'nsda_logo_icon_1778726323612.png'
ICON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ICON_NAME)

DEFAULT_CONFIG = {
    "server_url": "http://127.0.0.1:8080",
    "username": "",
    "password": "",
    "screenshot_interval": 600,
    "app_tracking_interval": 30,
    "keyboard_report_interval": 300,
    "idle_threshold": 120,
    "monitoring_enabled": False,
    "first_run": True
}

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('nsda_gui')

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
            # Ensure all default keys exist
            for key, value in DEFAULT_CONFIG.items():
                if key not in config:
                    config[key] = value
            return config
        except Exception:
            return DEFAULT_CONFIG
    return DEFAULT_CONFIG

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

# ─── Windows Utility Functions ───────────────────────────────

def add_to_startup():
    """Add the application to Windows startup via Registry."""
    if not HAS_WINDOWS_LIBS: return
    
    app_path = os.path.abspath(sys.argv[0])
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, "NSDAMonitor", 0, winreg.REG_SZ, app_path)
        winreg.CloseKey(key)
        logger.info("Added to Windows startup.")
        return True
    except Exception as e:
        logger.error(f"Failed to add to startup: {e}")
        return False

def create_desktop_shortcut():
    """Create a shortcut on the user's desktop."""
    if not HAS_WINDOWS_LIBS: return
    
    try:
        desktop = winshell.desktop()
        path = os.path.join(desktop, "NSDA Monitor.lnk")
        target = os.path.abspath(sys.argv[0])
        icon = os.path.abspath(ICON_PATH) if os.path.exists(ICON_PATH) else target
        
        shell = Dispatch('WScript.Shell')
        shortcut = shell.CreateShortCut(path)
        shortcut.Targetpath = target
        shortcut.WorkingDirectory = os.path.dirname(target)
        shortcut.IconLocation = icon
        shortcut.save()
        logger.info("Desktop shortcut created.")
        return True
    except Exception as e:
        logger.error(f"Failed to create shortcut: {e}")
        return False

# ─── Worker Thread for Monitoring ──────────────────────────

class MonitoringWorker(QThread):
    status_updated = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.running = False
        self.session = requests.Session()
        self.session_id = None
        self.kb_listener = None
        
        # Internal state for keyboard
        self.keystroke_count = 0
        self.deletion_count = 0
        self.edit_count = 0
        self.last_input_time = time.time()
        self.typing_start = None
        self.last_key_time = None
        
        # Internal state for apps
        self.current_app = None
        self.current_window = None
        self.app_start_time = None

    def authenticate(self):
        url = self.config['server_url'].rstrip('/')
        try:
            # 1. Get CSRF
            self.session.get(f"{url}/accounts/login/", timeout=10)
            csrf = self.session.cookies.get('csrftoken', '')
            self.session.headers.update({
                'X-CSRFToken': csrf,
                'Referer': f"{url}/accounts/login/",
            })
            
            # 2. Login
            resp = self.session.post(
                f"{url}/accounts/login/",
                data={
                    'username': self.config['username'],
                    'password': self.config['password'],
                    'csrfmiddlewaretoken': csrf,
                },
                allow_redirects=False,
                timeout=10
            )
            
            if resp.status_code in (200, 302):
                new_csrf = self.session.cookies.get('csrftoken', '')
                if new_csrf:
                    self.session.headers.update({'X-CSRFToken': new_csrf})
                return True
        except Exception as e:
            logger.error(f"Auth error: {e}")
        return False

    def start_session(self):
        url = self.config['server_url'].rstrip('/')
        try:
            resp = self.session.post(f"{url}/monitoring/api/session/start/", timeout=10)
            if resp.status_code == 201:
                self.session_id = resp.json()['id']
                return True
        except Exception as e:
            logger.error(f"Session error: {e}")
        return False

    def run(self):
        if not self.authenticate():
            self.error_occurred.emit("Authentication failed. Check credentials/server.")
            return

        if not self.start_session():
            self.error_occurred.emit("Failed to start monitoring session.")
            return

        self.running = True
        self.status_updated.emit("Monitoring Active")
        
        # Start keyboard listener
        if HAS_PYNPUT:
            self.kb_listener = keyboard.Listener(on_press=self.on_key_press)
            self.kb_listener.start()

        last_screenshot = 0
        last_app_track = 0
        last_kb_report = 0

        while self.running:
            now = time.time()
            
            # 1. Screenshot
            if now - last_screenshot >= self.config['screenshot_interval']:
                self.capture_screenshot()
                last_screenshot = now
            
            # 2. App Tracking
            if now - last_app_track >= self.config['app_tracking_interval']:
                self.track_app_usage()
                last_app_track = now
                
            # 3. Keyboard Report
            if now - last_kb_report >= self.config['keyboard_report_interval']:
                self.report_keyboard_activity()
                last_kb_report = now
                
            time.sleep(1)

    def stop(self):
        self.running = False
        if self.kb_listener:
            self.kb_listener.stop()
        
        if self.session_id:
            url = self.config['server_url'].rstrip('/')
            try:
                self.session.post(f"{url}/monitoring/api/session/{self.session_id}/end/", timeout=5)
            except:
                pass
        self.status_updated.emit("Monitoring Stopped")

    def on_key_press(self, key):
        self.last_input_time = time.time()
        self.keystroke_count += 1
        
        if self.typing_start is None:
            self.typing_start = time.time()
        self.last_key_time = time.time()
        
        try:
            if key == keyboard.Key.backspace or key == keyboard.Key.delete:
                self.deletion_count += 1
            else:
                self.edit_count += 1
        except:
            self.edit_count += 1

    def capture_screenshot(self):
        if not HAS_MSS: return
        try:
            with mss.mss() as sct:
                screenshot = sct.grab(sct.monitors[1])
                from PIL import Image
                img = Image.frombytes('RGB', screenshot.size, screenshot.bgra, 'raw', 'BGRX')
                buffer = BytesIO()
                img.save(buffer, format='JPEG', quality=60)
                buffer.seek(0)
                
                files = {'image': ('screenshot.jpg', buffer, 'image/jpeg')}
                data = {'session': self.session_id} if self.session_id else {}
                url = self.config['server_url'].rstrip('/')
                self.session.post(f"{url}/monitoring/api/screenshot/", files=files, data=data, timeout=15)
        except Exception as e:
            logger.error(f"Screenshot error: {e}")

    def track_app_usage(self):
        if not HAS_WIN32: return
        try:
            hwnd = win32gui.GetForegroundWindow()
            title = win32gui.GetWindowText(hwnd)
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            proc = psutil.Process(pid)
            app_name = proc.name()
            
            idle = (time.time() - self.last_input_time) > self.config['idle_threshold']
            
            if app_name != self.current_app or title != self.current_window:
                if self.current_app and self.app_start_time:
                    duration = int(time.time() - self.app_start_time)
                    self.upload_app_usage(self.current_app, self.current_window, self.app_start_time, duration, idle)
                
                self.current_app = app_name
                self.current_window = title
                self.app_start_time = time.time()
        except:
            pass

    def upload_app_usage(self, app, title, start, dur, idle):
        url = self.config['server_url'].rstrip('/')
        data = {
            'app_name': app[:255],
            'window_title': title[:500],
            'start_time': datetime.fromtimestamp(start).isoformat(),
            'duration_seconds': dur,
            'is_idle': idle
        }
        if self.session_id:
            data['session'] = self.session_id
        try:
            self.session.post(f"{url}/monitoring/api/app-usage/", json=data, timeout=10)
        except:
            pass

    def report_keyboard_activity(self):
        if self.keystroke_count == 0: return
        url = self.config['server_url'].rstrip('/')
        dur = int(self.last_key_time - self.typing_start) if self.typing_start else 0
        data = {
            'total_keystrokes': self.keystroke_count,
            'deletion_count': self.deletion_count,
            'edit_count': self.edit_count,
            'typing_duration_seconds': dur,
            'interval_minutes': self.config['keyboard_report_interval'] // 60
        }
        if self.session_id:
            data['session'] = self.session_id
        try:
            self.session.post(f"{url}/monitoring/api/keyboard/", json=data, timeout=10)
            # Reset
            self.keystroke_count = 0
            self.deletion_count = 0
            self.edit_count = 0
            self.typing_start = None
        except:
            pass

# ─── UI Components ──────────────────────────────────────────

class PermissionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("NSDA Portal - Permission Request")
        self.setFixedSize(400, 280)
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Dialog)
        self.setStyleSheet("""
            QDialog { background-color: #ffffff; border: 1px solid #e0e0e0; border-radius: 8px; }
            QLabel#Title { color: #1e293b; font-size: 18px; font-weight: bold; }
            QLabel#Desc { color: #64748b; font-size: 13px; }
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)
        
        # Logo placeholder or generated icon
        logo_label = QLabel()
        if os.path.exists(ICON_PATH):
            pixmap = QPixmap(ICON_PATH).scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            logo_label.setPixmap(pixmap)
        else:
            logo_label.setText("NSDA")
            logo_label.setStyleSheet("font-weight: bold; color: #2563eb; font-size: 24px;")
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(logo_label)
            
        title = QLabel("Enable Monitoring?")
        title.setObjectName("Title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        desc = QLabel("NSDA Portal requires background monitoring to track attendance and progress. Do you allow this workstation to be monitored?")
        desc.setObjectName("Desc")
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        self.btn_allow = QPushButton("Allow Monitoring")
        self.btn_allow.setStyleSheet("""
            QPushButton { background-color: #2563eb; color: white; padding: 10px; border-radius: 5px; font-weight: bold; border: none; }
            QPushButton:hover { background-color: #1d4ed8; }
        """)
        self.btn_allow.clicked.connect(self.accept)
        
        self.btn_cancel = QPushButton("Maybe Later")
        self.btn_cancel.setStyleSheet("""
            QPushButton { background-color: #f1f5f9; color: #475569; padding: 10px; border-radius: 5px; border: 1px solid #e2e8f0; }
            QPushButton:hover { background-color: #e2e8f0; }
        """)
        self.btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_allow)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)

class SettingsWindow(QMainWindow):
    def __init__(self, config, worker):
        super().__init__()
        self.config = config
        self.worker = worker
        self.setWindowTitle("NSDA Monitor Dashboard")
        self.setFixedSize(450, 580)
        self.setStyleSheet("""
            QMainWindow { background-color: #ffffff; }
            QLabel { color: #334155; font-weight: 500; }
            QLineEdit { padding: 12px; border: 1px solid #e2e8f0; border-radius: 8px; background: #f8fafc; color: #1e293b; }
            QLineEdit:focus { border: 2px solid #2563eb; background: white; }
            QFrame#Separator { background-color: #f1f5f9; min-height: 2px; max-height: 2px; }
        """)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)
        
        # ─── Status Section ───
        status_card = QFrame()
        status_card.setStyleSheet("background: #f8fafc; border-radius: 12px; border: 1px solid #e2e8f0;")
        status_layout = QVBoxLayout(status_card)
        status_layout.setContentsMargins(20, 20, 20, 20)
        
        self.status_title = QLabel("Monitoring Status")
        self.status_title.setStyleSheet("font-size: 14px; font-weight: 600; color: #64748b; border: none;")
        status_layout.addWidget(self.status_title)
        
        self.status_val = QLabel("OFFLINE")
        self.status_val.setStyleSheet("font-size: 28px; font-weight: 800; color: #ef4444; border: none;")
        status_layout.addWidget(self.status_val)
        
        self.btn_toggle = QPushButton("START MONITORING")
        self.btn_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle.setMinimumHeight(55)
        self.btn_toggle.clicked.connect(self.toggle_monitoring)
        status_layout.addWidget(self.btn_toggle)
        
        layout.addWidget(status_card)
        
        # ─── Credentials Section ───
        layout.addSpacing(10)
        creds_label = QLabel("Portal Credentials")
        creds_label.setStyleSheet("font-weight: 700; color: #1e293b; font-size: 15px;")
        layout.addWidget(creds_label)
        
        layout.addWidget(QLabel("Server URL"))
        self.url_input = QLineEdit(self.config['server_url'])
        layout.addWidget(self.url_input)
        
        h_layout = QHBoxLayout()
        v1 = QVBoxLayout()
        v1.addWidget(QLabel("Username"))
        self.user_input = QLineEdit(self.config['username'])
        v1.addWidget(self.user_input)
        h_layout.addLayout(v1)
        
        v2 = QVBoxLayout()
        v2.addWidget(QLabel("Password"))
        self.pass_input = QLineEdit(self.config['password'])
        self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        v2.addWidget(self.pass_input)
        h_layout.addLayout(v2)
        layout.addLayout(h_layout)
        
        layout.addStretch()
        
        self.btn_save = QPushButton("Save & Update Credentials")
        self.btn_save.setStyleSheet("""
            QPushButton { background-color: #f1f5f9; color: #1e293b; padding: 12px; border-radius: 8px; font-weight: 600; border: 1px solid #e2e8f0; }
            QPushButton:hover { background-color: #e2e8f0; }
        """)
        self.btn_save.clicked.connect(self.save_creds)
        layout.addWidget(self.btn_save)
        
        # Connect signals
        self.worker.status_updated.connect(self.update_ui_state)
        self.worker.error_occurred.connect(self.show_error)
        
        # Initial State
        self.update_ui_state("Monitoring Stopped")

    def update_ui_state(self, status):
        if "Active" in status:
            self.status_val.setText("ACTIVE")
            self.status_val.setStyleSheet("font-size: 28px; font-weight: 800; color: #10b981; border: none;")
            self.btn_toggle.setText("STOP MONITORING")
            self.btn_toggle.setStyleSheet("""
                QPushButton { background-color: #ef4444; color: white; border-radius: 8px; font-weight: bold; border: none; font-size: 14px; }
                QPushButton:hover { background-color: #dc2626; }
            """)
        else:
            self.status_val.setText("OFFLINE")
            self.status_val.setStyleSheet("font-size: 28px; font-weight: 800; color: #64748b; border: none;")
            self.btn_toggle.setText("START MONITORING")
            self.btn_toggle.setStyleSheet("""
                QPushButton { background-color: #10b981; color: white; border-radius: 8px; font-weight: bold; border: none; font-size: 14px; }
                QPushButton:hover { background-color: #059669; }
            """)

    def show_error(self, text):
        QMessageBox.critical(self, "Connection Error", text)
        self.update_ui_state("Error")

    def toggle_monitoring(self):
        if not self.config['username'] or not self.config['password']:
            QMessageBox.warning(self, "Action Required", "Please enter your portal credentials first.")
            return

        if not self.worker.isRunning():
            self.config['monitoring_enabled'] = True
            save_config(self.config)
            self.worker.config = self.config
            self.worker.start()
        else:
            self.config['monitoring_enabled'] = False
            save_config(self.config)
            self.worker.stop()

    def save_creds(self):
        self.config['server_url'] = self.url_input.text()
        self.config['username'] = self.user_input.text()
        self.config['password'] = self.pass_input.text()
        save_config(self.config)
        
        if self.worker.isRunning():
            # Restart with new creds
            self.worker.stop()
            self.worker.wait()
            self.worker.config = self.config
            self.worker.start()
            
        QMessageBox.information(self, "Success", "Credentials saved successfully.")

# ─── Main Application ───────────────────────────────────────

class NSDAApp(QApplication):
    def __init__(self, argv):
        super().__init__(argv)
        self.setApplicationName("NSDA Monitor")
        self.config = load_config()
        
        # Setup worker
        self.worker = MonitoringWorker(self.config)
        
        # Setup Tray
        self.tray_icon = QSystemTrayIcon(self)
        if os.path.exists(ICON_PATH):
            self.tray_icon.setIcon(QIcon(ICON_PATH))
        else:
            pixmap = QPixmap(32, 32)
            pixmap.fill(QColor("#3b82f6"))
            self.tray_icon.setIcon(QIcon(pixmap))
            
        self.tray_menu = QMenu()
        self.action_settings = self.tray_menu.addAction("Open Settings")
        self.action_settings.triggered.connect(self.show_settings)
        self.tray_menu.addSeparator()
        self.action_quit = self.tray_menu.addAction("Exit Agent")
        self.action_quit.triggered.connect(self.quit_app)
        
        self.tray_icon.setContextMenu(self.tray_menu)
        self.tray_icon.show()
        
        self.settings_win = SettingsWindow(self.config, self.worker)
        
        # Logic Flow
        if self.config.get('first_run', True):
            QTimer.singleShot(1000, self.handle_first_run)
        elif self.config.get('monitoring_enabled', False):
            self.worker.start()

    def handle_first_run(self):
        dialog = PermissionDialog()
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.config['monitoring_enabled'] = True
            self.config['first_run'] = False
            save_config(self.config)
            
            # Auto-run & Shortcut Setup
            add_to_startup()
            create_desktop_shortcut()
            
            if not self.config['username'] or not self.config['password']:
                self.show_settings()
                QMessageBox.information(None, "Setup Required", "Please enter your Portal credentials to begin monitoring.")
            else:
                self.worker.config = self.config
                self.worker.start()
        else:
            self.config['monitoring_enabled'] = False
            self.config['first_run'] = False
            save_config(self.config)
            self.tray_icon.showMessage(
                "Monitoring Disabled", 
                "The agent is idle. You can enable it anytime from the System Tray settings.", 
                QSystemTrayIcon.MessageIcon.Information
            )

    def show_settings(self):
        self.settings_win.show()
        self.settings_win.raise_()
        self.settings_win.activateWindow()

    def quit_app(self):
        self.worker.stop()
        self.worker.wait(2000)
        self.quit()

if __name__ == '__main__':
    app = NSDAApp(sys.argv)
    sys.exit(app.exec())
