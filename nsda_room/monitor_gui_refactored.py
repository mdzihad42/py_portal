class SettingsWindow(QMainWindow):
    def __init__(self, config, worker):
        super().__init__()
        self.config = config
        self.worker = worker
        self.setWindowTitle("NSDA Monitor Dashboard")
        self.setFixedSize(450, 620) # Increased height for update banner
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

        # ─── Update Banner (Hidden by default) ───
        self.update_banner = QFrame()
        self.update_banner.setObjectName("UpdateBanner")
        self.update_banner.setStyleSheet("background: #fef9c3; border-radius: 8px; border: 1px solid #fde047;")
        ub_layout = QHBoxLayout(self.update_banner)
        self.update_label = QLabel("A new version is available!")
        self.update_label.setStyleSheet("color: #854d0e; font-weight: 600; border: none; background: none;")
        self.update_btn = QPushButton("Download Update")
        self.update_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update_btn.setStyleSheet("background: #ca8a04; color: white; border: none; padding: 5px 10px; border-radius: 4px;")
        ub_layout.addWidget(self.update_label)
        ub_layout.addWidget(self.update_btn)
        self.update_banner.hide()
        layout.addWidget(self.update_banner)
        
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
        layout.addWidget(QLabel("Portal URL"))
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("http://your-portal.com")
        self.url_input.setText(self.config.get('server_url', ''))
        layout.addWidget(self.url_input)
        
        layout.addWidget(QLabel("Student ID / Username"))
        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("Enter your username")
        self.user_input.setText(self.config.get('username', ''))
        layout.addWidget(self.user_input)
        
        layout.addWidget(QLabel("Portal Password"))
        self.pass_input = QLineEdit()
        self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pass_input.setPlaceholderText("Enter your password")
        self.pass_input.setText(self.config.get('password', ''))
        layout.addWidget(self.pass_input)
        
        separator = QFrame()
        separator.setObjectName("Separator")
        layout.addWidget(separator)
        
        self.btn_save = QPushButton("Save & Update Credentials")
        self.btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save.setStyleSheet("""
            QPushButton { background-color: #f1f5f9; color: #475569; padding: 12px; border-radius: 8px; font-weight: bold; border: 1px solid #e2e8f0; }
            QPushButton:hover { background-color: #e2e8f0; }
        """)
        self.btn_save.clicked.connect(self.save_settings)
        layout.addWidget(self.btn_save)
        
        # UI Updates
        self.update_status_ui(self.worker.isRunning())
        self.worker.started.connect(lambda: self.update_status_ui(True))
        self.worker.finished.connect(lambda: self.update_status_ui(False))
        
        # Check for updates on launch
        self.check_for_updates()

    def check_for_updates(self):
        """Check server for a newer version."""
        def run_check():
            try:
                server_url = self.config.get('server_url', '').rstrip('/')
                if not server_url: return
                
                response = requests.get(
                    f"{server_url}/monitoring/api/check-update/",
                    auth=(self.config.get('username'), self.config.get('password')),
                    timeout=5
                )
                if response.status_code == 200:
                    data = response.json()
                    new_version = data.get('version')
                    if new_version and new_version != APP_VERSION:
                        self.update_label.setText(f"Update Available: v{new_version}")
                        self.update_btn.clicked.connect(lambda: os.startfile(data.get('download_url')))
                        self.update_banner.show()
            except Exception as e:
                print(f"Update check failed: {e}")

        threading.Thread(target=run_check, daemon=True).start()

    def update_status_ui(self, active):
        if active:
            self.status_val.setText("MONITORING ACTIVE")
            self.status_val.setStyleSheet("font-size: 28px; font-weight: 800; color: #22c55e; border: none;")
            self.btn_toggle.setText("STOP MONITORING")
            self.btn_toggle.setStyleSheet("""
                QPushButton { background-color: #fee2e2; color: #ef4444; border-radius: 10px; font-weight: 800; border: 2px solid #fecaca; }
                QPushButton:hover { background-color: #fecaca; }
            """)
        else:
            self.status_val.setText("OFFLINE")
            self.status_val.setStyleSheet("font-size: 28px; font-weight: 800; color: #ef4444; border: none;")
            self.btn_toggle.setText("START MONITORING")
            self.btn_toggle.setStyleSheet("""
                QPushButton { background-color: #2563eb; color: white; border-radius: 10px; font-weight: 800; border: none; }
                QPushButton:hover { background-color: #1d4ed8; }
            """)

    def toggle_monitoring(self):
        if self.worker.isRunning():
            self.worker.stop()
            self.config['monitoring_enabled'] = False
        else:
            # Validate credentials before starting
            if not self.config.get('username') or not self.config.get('password'):
                QMessageBox.warning(self, "Setup Required", "Please save your credentials first.")
                return
            self.worker.start()
            self.config['monitoring_enabled'] = True
        
        # Save state
        with open(CONFIG_FILE, 'w') as f:
            json.dump(self.config, f, indent=2)

    def save_settings(self):
        self.config['server_url'] = self.url_input.text()
        self.config['username'] = self.user_input.text()
        self.config['password'] = self.pass_input.text()
        
        with open(CONFIG_FILE, 'w') as f:
            json.dump(self.config, f, indent=2)
            
        QMessageBox.information(self, "Success", "Credentials saved successfully!")
        self.check_for_updates() # Check again with new credentials
