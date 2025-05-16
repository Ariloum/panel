import os
import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom
import time
import threading
from datetime import datetime
import schedule
from PyQt5.QtCore import QProcess, QTimer
from PyQt5.QtWidgets import QApplication

from utils.constants import APP_FOLDER, COLORS

class AppManager:
    """Class to manage console applications"""
    def __init__(self):
        self.apps = {}
        self.processes = {}
        self.schedules = {}
        self._last_schedule_time = None
        self.load_apps()
    
    def load_apps(self):
        """Load all apps from the apps folder"""
        if not os.path.exists(APP_FOLDER):
            os.makedirs(APP_FOLDER)
        
        # Keep track of existing apps and their running state
        existing_apps = set(self.apps.keys())
        new_apps = {}
        
        for app_dir in os.listdir(APP_FOLDER):
            app_path = os.path.join(APP_FOLDER, app_dir)
            if os.path.isdir(app_path):
                settings_path = os.path.join(app_path, "settings.xml")
                app_settings = self.load_settings(settings_path)
                
                # Clean up any duplicate URL parameters
                self.clean_duplicate_url_parameters(app_dir, settings_path, app_settings)
                
                new_apps[app_dir] = {
                    "name": app_dir,
                    "path": app_path,
                    "settings_path": settings_path,
                    "settings": app_settings
                }
        
        # Update apps dictionary while preserving running processes
        self.apps = new_apps
        
    def clean_duplicate_url_parameters(self, app_name, settings_path, settings):
        """Clean up duplicate URL parameters in settings file"""
        try:
            # Check if we need to clean up
            needs_cleanup = False
            main_url = settings.get("url", "")
            
            # Look for URL in custom parameters
            for key in list(settings.keys()):
                if key.lower() == "url" and key != "url":
                    print(f"DEBUG: Found duplicate URL parameter with key '{key}' for app {app_name}")
                    # If main URL is empty but we have a URL in custom parameters, use that
                    if not main_url and settings[key]:
                        settings["url"] = settings[key]
                        print(f"DEBUG: Moving URL value '{settings[key]}' from custom parameter to main URL")
                    # Remove the duplicate parameter
                    del settings[key]
                    needs_cleanup = True
            
            if needs_cleanup:
                print(f"DEBUG: Cleaning up duplicate URL parameters for app {app_name}")
                # Save the cleaned settings
                self.save_settings(app_name, settings)
                print(f"DEBUG: Cleanup complete for app {app_name}")
                
        except Exception as e:
            print(f"Error cleaning up duplicate URL parameters: {e}")
    
    def load_settings(self, settings_path):
        """Load settings from XML file"""
        settings = {
            "path": "",
            "command": "",
            "url": "",
            "autorun": False,
            "schedule_enabled": False,
            "schedule_type": "Interval",
            "interval_value": 60,
            "interval_unit": "Minutes",
            "schedule_time": "12:00",
            "display_name": "",
            "short_name": "",
            "group": ""
        }
        
        try:
            if os.path.exists(settings_path):
                tree = ET.parse(settings_path)
                root = tree.getroot()
                
                for elem in root:
                    if elem.tag == "parameters":
                        for param in elem:
                            # Skip URL parameter in custom parameters section if we already have a URL in main settings
                            param_name = param.get("name")
                            if param_name.lower() == "url" and "url" in settings and settings["url"]:
                                print(f"DEBUG: Skipping duplicate URL parameter in custom parameters")
                                continue
                            settings[param.get("name")] = param.get("value")
                    else:
                        settings[elem.tag] = elem.text
                        if elem.tag == "url":
                            print(f"DEBUG: Loaded URL from XML: {elem.text}")
                        
                # Convert boolean strings to actual booleans
                for key in ["autorun", "schedule_enabled"]:
                    if key in settings and settings[key] is not None:
                        settings[key] = str(settings[key]).lower() == "true"
                    else:
                        # Ensure default value if missing or None
                        settings[key] = False
                        
                # Convert numeric strings to integers
                if "interval_value" in settings and settings["interval_value"] is not None:
                    try:
                        settings["interval_value"] = int(settings["interval_value"])
                    except (ValueError, TypeError):
                        settings["interval_value"] = 60  # Default if conversion fails
                else:
                    settings["interval_value"] = 60  # Default if missing
                    
                # Ensure string values are not None
                for key in ["path", "command", "url", "group", "short_name", "interval_unit", "schedule_type", "schedule_time", "display_name"]:
                    if key not in settings or settings[key] is None:
                        settings[key] = ""
                    else:
                        # Ensure it's a string
                        settings[key] = str(settings[key])
                
                print(f"DEBUG: Final URL in settings: {settings.get('url', '')}")
        except Exception as e:
            print(f"Error loading settings from {settings_path}: {e}")
        
        return settings
    
    def save_settings(self, app_name, settings):
        """Save settings to XML file"""
        try:
            app_info = self.apps.get(app_name)
            if not app_info:
                return False
                
            settings_path = app_info["settings_path"]
            
            root = ET.Element("settings")
            
            for key, value in settings.items():
                elem = ET.SubElement(root, key)
                elem.text = str(value)
            
            # Save to file with pretty formatting
            rough_string = ET.tostring(root, 'utf-8')
            reparsed = minidom.parseString(rough_string)
            pretty_xml = reparsed.toprettyxml(indent="  ")
            
            with open(settings_path, "w") as f:
                f.write(pretty_xml)
                
            # Update in-memory settings
            self.apps[app_name]["settings"] = settings
            
            return True
        except Exception as e:
            print(f"Error saving settings: {e}")
            return False
    
    def start_app(self, app_name):
        """Start an application"""
        if app_name in self.apps and app_name not in self.processes:
            app_info = self.apps[app_name]
            settings = app_info["settings"]
            
            # Create process
            process = QProcess()
            
            # Set working directory if specified
            if settings["path"]:
                process.setWorkingDirectory(settings["path"])
                print(f"Setting working directory for {app_name}: {settings['path']}")
            
            # Start the process
            if settings["command"]:
                command = settings["command"]
                print(f"Starting process for {app_name} with command: {command}")
                
                # Check if this is a batch file
                is_batch_file = command.lower().endswith(".bat") or command.lower().endswith(".cmd")
                
                # Check if this is a Python script
                is_python_script = "python" in command.lower() or command.lower().endswith(".py")
                
                if is_batch_file:
                    # For batch files, we need to use cmd.exe as an intermediary to capture output properly
                    process.start("cmd.exe", ["/c", command])
                elif is_python_script:
                    # For Python scripts, we need to parse the command and arguments
                    # This ensures proper output capture
                    parts = command.split()
                    program = parts[0]
                    args = parts[1:]
                    
                    # If the command starts with python.exe or python, use it directly
                    if program.lower().endswith("python.exe") or program.lower() == "python":
                        # Add -u flag to ensure unbuffered output if not already present
                        if "-u" not in args and "-u" not in command:
                            args = ["-u"] + args
                        process.start(program, args)
                    # If it's just a .py file, prepend python -u
                    elif program.lower().endswith(".py"):
                        process.start("python", ["-u", program] + args)
                    else:
                        # For other Python-related commands, try to parse intelligently
                        # Add -u flag to ensure unbuffered output
                        process.start(program, ["-u"] + args)
                else:
                    # For other commands with arguments, split and process
                    parts = command.split()
                    if len(parts) > 1:
                        program = parts[0]
                        args = parts[1:]
                        process.start(program, args)
                    else:
                        # Simple command with no arguments
                        process.start(command)
                    
                self.processes[app_name] = process
                
                # Set process to use unbuffered output
                process.setProcessChannelMode(QProcess.MergedChannels)
                
                # Set environment variable to ensure Python doesn't buffer output
                environment = process.processEnvironment()
                environment.insert("PYTHONUNBUFFERED", "1")
                process.setProcessEnvironment(environment)
                
                return True
            else:
                print(f"No command specified for {app_name}")
        elif app_name in self.processes:
            print(f"App {app_name} is already running")
        else:
            print(f"App {app_name} not found in app list")
        
        return False
    
    def stop_app(self, app_name):
        """Stop an application"""
        if app_name in self.processes:
            print(f"Stopping app: {app_name}")
            process = self.processes[app_name]
            
            # Try to terminate gracefully first
            process.terminate()
            
            # Set up a timer to check if the process has finished after a short delay
            # This avoids blocking the UI thread
            QTimer.singleShot(500, lambda: self.check_process_terminated(app_name, process))
            
            # Remove from processes dict immediately to prevent duplicate stops
            del self.processes[app_name]
            print(f"Removed {app_name} from processes dictionary")
            return True
        else:
            print(f"App {app_name} is not running, cannot stop")
        
        return False
        
    def check_process_terminated(self, app_name, process):
        """Check if a process has terminated, and kill it if not"""
        if process.state() != QProcess.NotRunning:
            print(f"Process for {app_name} still running after terminate request, killing it")
            # Process is still running, kill it
            process.kill()
            
            # Wait a bit to ensure it's killed
            QTimer.singleShot(500, lambda: self._ensure_process_killed(app_name, process))
        else:
            print(f"Process for {app_name} successfully terminated")
    
    def _ensure_process_killed(self, app_name, process):
        """Final check to ensure process is killed"""
        if process.state() != QProcess.NotRunning:
            print(f"WARNING: Process for {app_name} could not be killed!")
        else:
            print(f"Process for {app_name} confirmed killed")
    
    def is_app_running(self, app_name):
        """Check if an app is running"""
        return app_name in self.processes
    
    def setup_schedules(self):
        """Set up all app schedules"""
        # Clear existing schedules
        schedule.clear()
        self.schedules = {}  # Clear the schedules dictionary
        
        for app_name, app_info in self.apps.items():
            settings = app_info["settings"]
            
            if settings.get("schedule_enabled", False):
                schedule_type = settings.get("schedule_type", "Interval")
                
                if schedule_type == "Interval":
                    interval_value = settings.get("interval_value", 60)
                    interval_unit = settings.get("interval_unit", "Minutes")
                    
                    # Create job based on unit
                    if interval_unit == "Seconds":
                        # For seconds, we need to be careful with small values
                        if interval_value < 1:
                            interval_value = 1  # Minimum 1 second
                        self.schedules[app_name] = schedule.every(interval_value).seconds.do(
                            self.scheduled_app_run, app_name=app_name)
                        print(f"Scheduled {app_name} to run every {interval_value} seconds")
                    elif interval_unit == "Minutes":
                        self.schedules[app_name] = schedule.every(interval_value).minutes.do(
                            self.scheduled_app_run, app_name=app_name)
                        print(f"Scheduled {app_name} to run every {interval_value} minutes")
                    elif interval_unit == "Hours":
                        self.schedules[app_name] = schedule.every(interval_value).hours.do(
                            self.scheduled_app_run, app_name=app_name)
                        print(f"Scheduled {app_name} to run every {interval_value} hours")
                    
                elif schedule_type == "Daily":
                    time_str = settings.get("schedule_time", "12:00")
                    self.schedules[app_name] = schedule.every().day.at(time_str).do(
                        self.scheduled_app_run, app_name=app_name)
                    print(f"Scheduled {app_name} to run daily at {time_str}")
                    
                elif schedule_type == "Weekly":
                    time_str = settings.get("schedule_time", "12:00")
                    self.schedules[app_name] = schedule.every().week.at(time_str).do(
                        self.scheduled_app_run, app_name=app_name)
                    print(f"Scheduled {app_name} to run weekly at {time_str}")
                    
                elif schedule_type == "Monthly":
                    time_str = settings.get("schedule_time", "12:00")
                    # Schedule library doesn't have direct monthly support, so we'll check date in the job
                    self.schedules[app_name] = schedule.every().day.at(time_str).do(
                        self.check_monthly_schedule, app_name=app_name)
                    print(f"Scheduled {app_name} to run monthly at {time_str}")
    
    def check_monthly_schedule(self, app_name):
        """Check if today is the day to run monthly schedule"""
        # Run on the 1st day of each month
        if datetime.now().day == 1:
            self.scheduled_app_run(app_name)
    
    def scheduled_app_run(self, app_name):
        """Run an app based on schedule"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"[{timestamp}] Schedule triggered for app: {app_name}")
        
        # Store the timestamp for use in the main thread
        self._last_schedule_time = timestamp
        
        # Use QTimer to run this on the main thread to avoid threading issues
        # This is important because we're interacting with QProcess objects
        QTimer.singleShot(0, lambda: self._scheduled_app_run_main_thread(app_name))
        
        # Force UI update
        QApplication.processEvents()
        return True
    
    def _scheduled_app_run_main_thread(self, app_name):
        """Implementation of scheduled app run on the main thread"""
        timestamp = getattr(self, '_last_schedule_time', datetime.now().strftime('%H:%M:%S'))
        print(f"[{timestamp}] Executing scheduled run for {app_name} on main thread")
        
        # First, find the terminal tab and update it regardless of whether we restart the app
        # This will also mark the tab as updated with a blue background if it's not in focus
        self._update_terminal_for_scheduled_run(app_name, timestamp)
        
        # Force UI update
        QApplication.processEvents()
        
        # If app is already running, stop it first
        if self.is_app_running(app_name):
            print(f"App {app_name} is already running, stopping it first")
            self.stop_app(app_name)
            
            # Give a short delay before starting again
            QTimer.singleShot(1000, lambda: self._start_and_show_app(app_name))
        else:
            # Start the app immediately
            print(f"App {app_name} is not running, starting it now")
            self._start_and_show_app(app_name)
    
    def _update_terminal_for_scheduled_run(self, app_name, timestamp):
        """Update the terminal tab for a scheduled run even if the app is already running"""
        # This method will be overridden by MainWindow
        pass
    
    def _start_and_show_app(self, app_name):
        """Start an app and ensure its terminal tab is shown"""
        print(f"Starting scheduled app: {app_name}")
        if self.start_app(app_name):
            print(f"App {app_name} started successfully, creating terminal tab")
            # Emit a signal to notify the main window to create/show the terminal tab
            # We'll use QTimer to post this event to the main thread
            # For scheduled runs, we don't want to force focus on the tab
            QTimer.singleShot(0, lambda: self._notify_app_started(app_name, set_focus=False))
        else:
            print(f"Failed to start app {app_name}")
            
    def _notify_app_started(self, app_name, set_focus=True):
        """Notify that an app has started (to be overridden by MainWindow)"""
        # This will be connected to MainWindow.create_terminal_tab
        pass
    
    def run_scheduler(self):
        """Run the scheduler in a separate thread"""
        print("Scheduler thread started")
        
        # Run any apps that are scheduled with seconds immediately for testing
        for app_name, job in self.schedules.items():
            app_info = self.apps.get(app_name, {})
            settings = app_info.get("settings", {})
            if settings.get("schedule_enabled", False) and settings.get("schedule_type") == "Interval" and settings.get("interval_unit") == "Seconds":
                print(f"Immediately running scheduled app {app_name} for testing")
                # Run after a short delay to ensure UI is ready
                QTimer.singleShot(3000, lambda name=app_name: self.scheduled_app_run(name))
        
        # Counter for logging purposes
        tick_count = 0
        
        while True:
            try:
                # Run pending schedules
                schedule.run_pending()
                
                # Log every 10 seconds for debugging
                if tick_count % 10 == 0:
                    print(f"Scheduler tick {tick_count} - checking for pending jobs")
                    # List all active schedules
                    for app_name, job in self.schedules.items():
                        next_run = job.next_run
                        if next_run:
                            time_diff = (next_run - datetime.now()).total_seconds()
                            print(f"  App {app_name} next run in {time_diff:.1f} seconds")
                
                tick_count += 1
                time.sleep(1)
            except Exception as e:
                print(f"Error in scheduler: {e}")
                # Continue running even if there's an error
                time.sleep(1)