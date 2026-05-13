"""
NSDA Portal Monitoring Agent
============================
Standalone Python script for student machines.
Captures screenshots, tracks active applications, and monitors keyboard activity.
Uploads data to the NSDA Portal server via REST API.

Usage:
    1. Configure monitor_config.json with your server URL and credentials
    2. Run: python monitor_agent.py
    3. The agent will start monitoring and uploading data automatically

Requirements:
    pip install requests mss Pillow pynput pygetwindow
"""

import os
import sys
import json
import time
import threading
import tempfile
import logging
from datetime import datetime, timedelta
from io import BytesIO

import requests

# Optional imports — gracefully handle missing
try:
    import mss
    HAS_MSS = True
except ImportError:
    HAS_MSS = False
    print("[WARNING] mss not installed. Screenshots disabled. Install: pip install mss")

try:
    from pynput import keyboard
    HAS_PYNPUT = True
except ImportError:
    HAS_PYNPUT = False
    print("[WARNING] pynput not installed. Keyboard tracking disabled. Install: pip install pynput")

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
    print("[WARNING] pywin32/psutil not installed. App tracking limited. Install: pip install pywin32 psutil")


# ─── Configuration ───────────────────────────────────────────

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'monitor_config.json')

DEFAULT_CONFIG = {
    "server_url": "http://127.0.0.1:8000",
    "username": "",
    "password": "",
    "screenshot_interval": 600,  # 10 minutes
    "app_tracking_interval": 30,  # 30 seconds
    "keyboard_report_interval": 300,  # 5 minutes
    "idle_threshold": 120,  # 2 minutes
}

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
)
logger = logging.getLogger('nsda_monitor')


def load_config():
    """Load configuration from file or create default."""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
        return {**DEFAULT_CONFIG, **config}

    # Create default config file
    with open(CONFIG_FILE, 'w') as f:
        json.dump(DEFAULT_CONFIG, f, indent=2)
    logger.info(f"Created default config at {CONFIG_FILE}. Please configure it.")
    return DEFAULT_CONFIG


class MonitorAgent:
    """Main monitoring agent."""

    def __init__(self, config):
        self.config = config
        self.server_url = config['server_url'].rstrip('/')
        self.session = requests.Session()
        self.session_id = None
        self.running = False

        # Keyboard tracking state
        self.keystroke_count = 0
        self.deletion_count = 0
        self.edit_count = 0
        self.typing_start = None
        self.typing_duration = 0
        self.last_key_time = None
        self.kb_lock = threading.Lock()

        # App tracking state
        self.current_app = None
        self.current_window = None
        self.app_start_time = None
        self.last_input_time = time.time()

    def authenticate(self):
        """Login to the server and get auth token."""
        logger.info("Authenticating with server...")
        try:
            # 1. First GET to receive the CSRF cookie
            self.session.get(f"{self.server_url}/accounts/login/")
            csrf = self.session.cookies.get('csrftoken', '')
            
            # 2. Update headers with CSRF
            self.session.headers.update({
                'X-CSRFToken': csrf,
                'Referer': f"{self.server_url}/accounts/login/",
            })

            # 3. POST login
            resp = self.session.post(
                f"{self.server_url}/accounts/login/",
                data={
                    'username': self.config['username'],
                    'password': self.config['password'],
                    'csrfmiddlewaretoken': csrf,
                },
                allow_redirects=False,
            )

            if resp.status_code in (200, 302):
                # Refresh CSRF token after login (Django rotates it)
                new_csrf = self.session.cookies.get('csrftoken', '')
                if new_csrf:
                    self.session.headers.update({'X-CSRFToken': new_csrf})
                
                logger.info("Authentication successful!")
                return True
            else:
                logger.error(f"Authentication failed: {resp.status_code}")
                return False
        except requests.ConnectionError:
            logger.error(f"Cannot connect to server: {self.server_url}")
            return False

    def start_session(self):
        """Start a monitoring session on the server."""
        try:
            resp = self.session.post(
                f"{self.server_url}/monitoring/api/session/start/",
            )
            if resp.status_code == 201:
                data = resp.json()
                self.session_id = data['id']
                logger.info(f"Monitoring session started (ID: {self.session_id})")
                return True
            else:
                logger.error(f"Failed to start session: {resp.status_code}")
                return False
        except Exception as e:
            logger.error(f"Session start error: {e}")
            return False

    def end_session(self):
        """End the current monitoring session."""
        if self.session_id:
            try:
                self.session.post(
                    f"{self.server_url}/monitoring/api/session/{self.session_id}/end/",
                )
                logger.info("Monitoring session ended.")
            except Exception as e:
                logger.error(f"Session end error: {e}")

    # ─── Screenshot Capture ──────────────────────────────────

    def capture_screenshot(self):
        """Capture and upload a screenshot."""
        if not HAS_MSS:
            return

        try:
            with mss.mss() as sct:
                screenshot = sct.grab(sct.monitors[1])

                # Convert to JPEG
                from PIL import Image
                img = Image.frombytes('RGB', screenshot.size, screenshot.bgra, 'raw', 'BGRX')
                buffer = BytesIO()
                img.save(buffer, format='JPEG', quality=60)
                buffer.seek(0)

                # Upload
                files = {'image': ('screenshot.jpg', buffer, 'image/jpeg')}
                data = {}
                if self.session_id:
                    data['session'] = self.session_id

                resp = self.session.post(
                    f"{self.server_url}/monitoring/api/screenshot/",
                    files=files,
                    data=data,
                )
                if resp.status_code == 201:
                    logger.info(f"Screenshot taken and uploaded successfully. (Interval: {self.config['screenshot_interval']}s)")
                else:
                    logger.warning(f"Screenshot upload failed: {resp.status_code} - {resp.text}")

        except Exception as e:
            logger.error(f"Screenshot error: {e}")

    def screenshot_loop(self):
        """Periodically capture screenshots."""
        while self.running:
            self.capture_screenshot()
            time.sleep(self.config['screenshot_interval'])

    # ─── App Tracking ────────────────────────────────────────

    def get_active_window(self):
        """Get the currently active window info."""
        if HAS_WIN32 and sys.platform == 'win32':
            try:
                hwnd = win32gui.GetForegroundWindow()
                title = win32gui.GetWindowText(hwnd)
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                try:
                    proc = psutil.Process(pid)
                    app_name = proc.name()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    app_name = "Unknown"
                return app_name, title
            except Exception:
                return "Unknown", ""
        return "Unknown", ""

    def track_app_usage(self):
        """Track current application and upload when app changes."""
        app_name, window_title = self.get_active_window()

        # Check idle
        idle_time = time.time() - self.last_input_time
        is_idle = idle_time > self.config['idle_threshold']

        if app_name != self.current_app or window_title != self.current_window:
            # App changed — upload previous usage
            if self.current_app and self.app_start_time:
                duration = int(time.time() - self.app_start_time)
                self.upload_app_usage(
                    self.current_app,
                    self.current_window,
                    self.app_start_time,
                    duration,
                    is_idle,
                )

            self.current_app = app_name
            self.current_window = window_title
            self.app_start_time = time.time()

    def upload_app_usage(self, app_name, window_title, start_time, duration, is_idle):
        """Upload app usage data."""
        try:
            data = {
                'app_name': app_name[:255],
                'window_title': window_title[:500],
                'start_time': datetime.fromtimestamp(start_time).isoformat(),
                'duration_seconds': duration,
                'is_idle': is_idle,
            }
            if self.session_id:
                data['session'] = self.session_id

            self.session.post(
                f"{self.server_url}/monitoring/api/app-usage/",
                json=data,
            )
        except Exception as e:
            logger.error(f"App usage upload error: {e}")

    def app_tracking_loop(self):
        """Periodically track app usage."""
        while self.running:
            self.track_app_usage()
            time.sleep(self.config['app_tracking_interval'])

    # ─── Keyboard Tracking ───────────────────────────────────

    def on_key_press(self, key):
        """Handle keyboard press events."""
        self.last_input_time = time.time()

        with self.kb_lock:
            self.keystroke_count += 1

            if self.typing_start is None:
                self.typing_start = time.time()
            self.last_key_time = time.time()

            try:
                if key == keyboard.Key.backspace or key == keyboard.Key.delete:
                    self.deletion_count += 1
                elif key in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
                    pass  # Modifier key
                else:
                    self.edit_count += 1
            except AttributeError:
                self.edit_count += 1

    def report_keyboard_activity(self):
        """Upload keyboard activity report."""
        with self.kb_lock:
            if self.keystroke_count == 0:
                return

            typing_dur = 0
            if self.typing_start and self.last_key_time:
                typing_dur = int(self.last_key_time - self.typing_start)

            data = {
                'total_keystrokes': self.keystroke_count,
                'deletion_count': self.deletion_count,
                'edit_count': self.edit_count,
                'typing_duration_seconds': typing_dur,
                'interval_minutes': self.config['keyboard_report_interval'] // 60,
            }
            if self.session_id:
                data['session'] = self.session_id

            # Reset counters
            self.keystroke_count = 0
            self.deletion_count = 0
            self.edit_count = 0
            self.typing_start = None
            self.typing_duration = 0

        try:
            self.session.post(
                f"{self.server_url}/monitoring/api/keyboard/",
                json=data,
            )
            logger.info("Keyboard activity reported.")
        except Exception as e:
            logger.error(f"Keyboard report error: {e}")

    def keyboard_report_loop(self):
        """Periodically report keyboard activity."""
        while self.running:
            time.sleep(self.config['keyboard_report_interval'])
            self.report_keyboard_activity()

    # ─── Main Loop ───────────────────────────────────────────

    def start(self):
        """Start all monitoring threads."""
        if not self.authenticate():
            logger.error("Cannot authenticate. Please check config.")
            return

        if not self.start_session():
            logger.error("Cannot start monitoring session.")
            return

        self.running = True
        threads = []

        # Screenshot thread
        t = threading.Thread(target=self.screenshot_loop, daemon=True)
        t.start()
        threads.append(t)
        logger.info(f"Screenshot capture started (every {self.config['screenshot_interval']}s)")

        # App tracking thread
        t = threading.Thread(target=self.app_tracking_loop, daemon=True)
        t.start()
        threads.append(t)
        logger.info(f"App tracking started (every {self.config['app_tracking_interval']}s)")

        # Keyboard tracking
        if HAS_PYNPUT:
            listener = keyboard.Listener(on_press=self.on_key_press)
            listener.start()
            logger.info("Keyboard tracking started.")

            t = threading.Thread(target=self.keyboard_report_loop, daemon=True)
            t.start()
            threads.append(t)

        logger.info("=" * 50)
        logger.info("NSDA Monitoring Agent is running.")
        logger.info("Press Ctrl+C to stop.")
        logger.info("=" * 50)

        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Stopping monitoring agent...")
            self.running = False
            self.end_session()
            logger.info("Agent stopped.")


if __name__ == '__main__':
    config = load_config()

    if not config['username'] or not config['password']:
        print("\n" + "=" * 50)
        print("NSDA Monitoring Agent - Setup")
        print("=" * 50)
        config['server_url'] = input(f"Server URL [{config['server_url']}]: ").strip() or config['server_url']
        config['username'] = input("Username: ").strip()
        config['password'] = input("Password: ").strip()

        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        print(f"Config saved to {CONFIG_FILE}\n")

    agent = MonitorAgent(config)
    agent.start()
