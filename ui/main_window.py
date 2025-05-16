import os
from datetime import datetime
import threading
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                          QPushButton, QLabel, QTabWidget, QScrollArea, QFrame, 
                          QSplitter, QMessageBox)
from PyQt5.QtGui import QIcon, QFont, QColor
from PyQt5.QtCore import Qt, QTimer
import schedule

from utils.constants import COLORS, ICON_PATHS, APP_FOLDER
from utils.settings import global_settings
from models.group_manager import group_manager
from models.app_manager import AppManager
from ui.widgets import ColoredTextEdit, AppButton, AppGroupHeader
from ui.dialogs import GlobalSettingsDialog, SettingsDialog, GroupManagementDialog, NewAppDialog

from PyQt5.QtWidgets import QTabBar, QStylePainter, QStyleOptionTab
from PyQt5.QtGui import QPalette

from PyQt5.QtWidgets import QStyle

class CustomTabBar(QTabBar):
    """Tab bar that can highlight updated tabs."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.updated_tabs = set()
        # Store the normal background color for tabs
        self.normal_bg_color = QColor(COLORS['background'])
        # Color for updated tabs - use accent color directly for better visibility
        self.updated_bg_color = QColor(COLORS['accent'])

    def tabTextColor(self, index):
        """Return the text color for a tab"""
        if index in self.updated_tabs and index != self.currentIndex():
            return QColor(COLORS['text'])  # Normal text color for updated tabs
        return QColor(COLORS['text'])  # Default text color

    def tabBackgroundColor(self, index):
        """Return the background color for a tab"""
        if index in self.updated_tabs and index != self.currentIndex():
            return self.updated_bg_color  # Highlighted background for updated tabs
        elif index == self.currentIndex():
            return QColor(COLORS['panel'])  # Selected tab background
        return self.normal_bg_color  # Default background color

    def paintEvent(self, event):
        painter = QStylePainter(self)
        
        for index in range(self.count()):
            option = QStyleOptionTab()
            self.initStyleOption(option, index)
            
            # Set text color based on update status
            text_color = self.tabTextColor(index)
            option.palette.setColor(QPalette.WindowText, text_color)
            option.palette.setColor(QPalette.ButtonText, text_color)
            option.palette.setColor(QPalette.Text, text_color)
            
            # Set background color based on update status
            bg_color = self.tabBackgroundColor(index)
            option.palette.setColor(QPalette.Button, bg_color)
            option.palette.setColor(QPalette.Window, bg_color)
            
            painter.drawControl(QStyle.CE_TabBarTab, option)

class MainWindow(QMainWindow):
    """Main application window"""
    def __init__(self):
        super().__init__()
        # Ensure group manager is initialized first
        self.app_manager = AppManager()
        
        # Connect the app manager's notification method to our create_terminal_tab method
        self.app_manager._notify_app_started = lambda app_name, set_focus=True: self.create_terminal_tab(app_name, set_focus=set_focus)
        
        # Connect the app manager's terminal update method to our method
        self.app_manager._update_terminal_for_scheduled_run = self._update_terminal_for_scheduled_run
        
        self.init_ui()
        
        # Restore window position and size
        self.restore_window_geometry()
        
        # Set up schedules
        self.app_manager.setup_schedules()
        # Run scheduled tasks in the main event loop
        self.schedule_timer = QTimer(self)
        self.schedule_timer.timeout.connect(schedule.run_pending)
        self.schedule_timer.start(1000)
        
        # Auto-run apps
        self.auto_run_apps()
    
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Console App Manager")
        self.setMinimumSize(1400, 800)  # Increased from 1000x600 to 1400x800
        
        # Main widget and layout
        main_widget = QWidget()
        main_widget.setObjectName("mainWidget")
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(1, 1, 1, 1)  # Small margin for the border
        
        # Create splitter for resizable panels
        self.splitter = QSplitter(Qt.Horizontal)
        
        # Left panel - App list
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(20, 20, 20, 20)
        
        # Header with buttons
        header_layout = QHBoxLayout()
        
        # New app button
        new_btn = QPushButton("New")
        new_btn.setToolTip("Create a new application")
        new_btn.clicked.connect(self.create_new_app)
        header_layout.addWidget(new_btn)
        
        # Group management button
        group_btn = QPushButton("Groups")
        group_btn.setToolTip("Manage application groups")
        group_btn.clicked.connect(self.open_group_management)
        header_layout.addWidget(group_btn)
        
        # Global settings button
        settings_btn = QPushButton("Settings")
        settings_btn.setToolTip("Global application settings")
        settings_btn.clicked.connect(self.open_global_settings)
        header_layout.addWidget(settings_btn)
        
        header_layout.addStretch()
        
        left_layout.addLayout(header_layout)
        
        # Scroll area for app buttons
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        
        scroll_content = QWidget()
        self.app_list_layout = QVBoxLayout(scroll_content)
        self.app_list_layout.setAlignment(Qt.AlignTop)
        self.app_list_layout.setSpacing(5)  # Reduced spacing for tighter layout
        self.app_list_layout.setContentsMargins(5, 5, 5, 5)  # Reduced margins
        
        scroll_area.setWidget(scroll_content)
        left_layout.addWidget(scroll_area)
        
        # Right panel - Terminal tabs
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(20, 20, 20, 20)
        
        # Tab widget for terminals
        self.terminal_tabs = QTabWidget()
        self.terminal_tabs.setTabBar(CustomTabBar())
        self.terminal_tabs.setTabsClosable(True)
        self.terminal_tabs.tabCloseRequested.connect(self.close_terminal_tab)
        self.terminal_tabs.currentChanged.connect(self.on_terminal_tab_changed)
        
        # Set tab font size
        tab_font = QFont()
        tab_font.setPointSize(global_settings.settings["left_panel_font_size"])
        self.terminal_tabs.setFont(tab_font)
        
        right_layout.addWidget(self.terminal_tabs)
        
        # Add panels to splitter
        self.splitter.addWidget(left_panel)
        self.splitter.addWidget(right_panel)
        
        # Set initial sizes from saved settings or defaults
        splitter_sizes = global_settings.settings.get("splitter_sizes", [300, 700])
        # Ensure splitter_sizes is a list of integers
        if not isinstance(splitter_sizes, list):
            splitter_sizes = [300, 700]  # Default if not a list
        self.splitter.setSizes(splitter_sizes)
        
        # Connect splitter moved signal to save the sizes
        self.splitter.splitterMoved.connect(self.save_splitter_sizes)
        
        main_layout.addWidget(self.splitter)
        self.setCentralWidget(main_widget)
        
        # Populate app list
        self.populate_app_list()
        
        # Set dark theme
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{
                background-color: {COLORS['background']};
                color: {COLORS['text']};
                font-size: {global_settings.settings["left_panel_font_size"]}px;
            }}
            #mainWidget {{
                border: 1px solid {COLORS['border']};
                border-radius: 0px;
            }}
            QTabWidget::pane {{
                border: none;
                background-color: {COLORS['panel']};
                border-radius: 8px;
            }}
            QTabBar::tab {{
                /* Removed background-color to allow custom painting */
                color: {COLORS['text']};
                padding: 16px 24px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-size: {global_settings.settings["left_panel_font_size"]}px;
                border: none;
                margin-right: 4px;
            }}
            QTabBar::tab:selected {{
                /* Keep only the border styling, background is handled by CustomTabBar */
                border-bottom: 2px solid {COLORS['accent']};
            }}
            QTabBar::tab:hover:!selected {{
                /* Lighter hover effect that won't override our custom background */
                opacity: 0.8;
            }}
            QScrollArea, QScrollBar {{
                background-color: {COLORS['background']};
                border: none;
            }}
            QScrollBar:vertical {{
                width: 20px;
                background: {COLORS['background']};
            }}
            QScrollBar:horizontal {{
                height: 20px;
                background: {COLORS['background']};
            }}
            QScrollBar::handle {{
                background-color: {COLORS['border']};
                border-radius: 10px;
                margin: 4px;
            }}
            QScrollBar::handle:hover {{
                background-color: {COLORS['text_secondary']};
            }}
            QScrollBar::add-line, QScrollBar::sub-line {{
                background: none;
                border: none;
            }}
            QScrollBar::add-page, QScrollBar::sub-page {{
                background: none;
            }}
            QLabel {{
                color: {COLORS['text']};
                font-size: {global_settings.settings["left_panel_font_size"]}px;
            }}
            QPushButton {{
                font-size: {global_settings.settings["left_panel_font_size"]}px;
                padding: 8px;
                background-color: {COLORS['accent']};
                color: white;
                border: none;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['accent_hover']};
            }}
            QLineEdit, QComboBox, QSpinBox, QCheckBox, QTimeEdit {{
                font-size: {global_settings.settings["left_panel_font_size"]}px;
                padding: 8px;
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                background-color: {COLORS['panel']};
                color: {COLORS['text']};
            }}
        """)
    
    def on_terminal_tab_changed(self, index):
        """Clear highlight when a tab is selected"""
        tab_bar = self.terminal_tabs.tabBar()
        if hasattr(tab_bar, 'updated_tabs') and index in tab_bar.updated_tabs:
            print(f"Clearing updated status for tab {index} as it's now selected")
            tab_bar.updated_tabs.discard(index)
            tab_bar.update()  # This will trigger a repaint with normal background color
    
    def restore_window_geometry(self):
        """Restore window position and size from settings"""
        x = global_settings.settings.get("window_x", 100)
        y = global_settings.settings.get("window_y", 100)
        width = global_settings.settings.get("window_width", 1400)
        height = global_settings.settings.get("window_height", 800)
        
        # Ensure the window is not positioned off-screen
        from PyQt5.QtWidgets import QApplication
        desktop = QApplication.desktop().availableGeometry()
        x = max(0, min(x, desktop.width() - width))
        y = max(0, min(y, desktop.height() - height))
        
        self.setGeometry(x, y, width, height)
    
    def save_window_geometry(self):
        """Save window position and size to settings"""
        global_settings.settings["window_x"] = self.x()
        global_settings.settings["window_y"] = self.y()
        global_settings.settings["window_width"] = self.width()
        global_settings.settings["window_height"] = self.height()
        global_settings.save_settings()
    
    def save_splitter_sizes(self):
        """Save splitter sizes when changed"""
        global_settings.settings["splitter_sizes"] = self.splitter.sizes()
        global_settings.save_settings()
    
    def closeEvent(self, event):
        """Override close event to save window geometry"""
        self.save_window_geometry()
        event.accept()
    
    def populate_app_list(self):
        """Populate the app list in the left panel with group headers"""
        # Clear existing items
        while self.app_list_layout.count():
            item = self.app_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Group apps by category from settings
        app_groups = {}
        ungrouped_apps = []
        
        for app_name, app_info in self.app_manager.apps.items():
            # Check if settings exists and is not None
            if app_info.get("settings") is None:
                ungrouped_apps.append((app_name, app_info))
                continue
                
            # Safely get the group value
            group = app_info["settings"].get("group", "")
            if group and isinstance(group, str):
                group = group.strip()
                if group:
                    if group not in app_groups:
                        app_groups[group] = []
                    app_groups[group].append((app_name, app_info))
                else:
                    ungrouped_apps.append((app_name, app_info))
            else:
                ungrouped_apps.append((app_name, app_info))
        
        # Add groups and apps
        for group_name in sorted(app_groups.keys()):
            # Add group header
            group_header = AppGroupHeader(group_name)
            self.app_list_layout.addWidget(group_header)
            
            # Add apps in this group
            for app_name, app_info in sorted(app_groups[group_name], key=lambda x: x[0]):
                app_button = AppButton(app_name, app_info)
                app_button.clicked.connect(self.on_app_clicked)
                app_button.toggle_state.connect(self.toggle_app_state)
                app_button.settings_clicked.connect(self.open_app_settings)
                
                # Ensure URL is set correctly
                url = app_info["settings"].get("url", "")
                if url:
                    app_button.update_url(url)
                    
                self.app_list_layout.addWidget(app_button)
        
        # Add ungrouped apps at the end
        if ungrouped_apps:
            group_header = AppGroupHeader("Ungrouped")
            self.app_list_layout.addWidget(group_header)
            
            for app_name, app_info in sorted(ungrouped_apps, key=lambda x: x[0]):
                app_button = AppButton(app_name, app_info)
                app_button.clicked.connect(self.on_app_clicked)
                app_button.toggle_state.connect(self.toggle_app_state)
                app_button.settings_clicked.connect(self.open_app_settings)
                
                # Ensure URL is set correctly
                url = app_info["settings"].get("url", "")
                if url:
                    app_button.update_url(url)
                    
                self.app_list_layout.addWidget(app_button)
    
    def on_app_clicked(self, app_name):
        """Handle app button click"""
        # Find the tab with this app_name and switch to it if it exists
        for i in range(self.terminal_tabs.count()):
            tab_widget = self.terminal_tabs.widget(i)
            if hasattr(tab_widget, 'app_name') and tab_widget.app_name == app_name:
                self.terminal_tabs.setCurrentIndex(i)
                return
                
        # If app is running but no tab was found, create a new tab
        if self.app_manager.is_app_running(app_name):
            self.create_terminal_tab(app_name)
    
    def toggle_app_state(self, app_name, start):
        """Toggle app running state"""
        if start:
            # If the app is already marked as running but we're trying to start it again,
            # we need to stop it first and then restart it
            if self.app_manager.is_app_running(app_name):
                self.app_manager.stop_app(app_name)
                # Find and clear the existing terminal tab
                for i in range(self.terminal_tabs.count()):
                    tab_widget = self.terminal_tabs.widget(i)
                    if hasattr(tab_widget, 'app_name') and tab_widget.app_name == app_name:
                        if isinstance(tab_widget, ColoredTextEdit):
                            tab_widget.clear()
                            tab_widget.append_colored_text("[Restarting application...]\n", COLORS['accent'])
                            break
                
                # Use a timer to delay the restart slightly
                QTimer.singleShot(500, lambda: self._start_app_delayed(app_name))
            else:
                # Start the app immediately
                if self.app_manager.start_app(app_name):
                    # Create or update the terminal tab
                    self.create_terminal_tab(app_name)
        else:
            self.app_manager.stop_app(app_name)
            # Don't remove the tab when stopping the app
            # Just update the button state
        
        # Update button state
        self.update_app_buttons()
    
    def _start_app_delayed(self, app_name):
        """Start an app after a short delay (used for restart)"""
        if self.app_manager.start_app(app_name):
            # Create or update the terminal tab
            self.create_terminal_tab(app_name)
    
    def create_terminal_tab(self, app_name, set_focus=True):
        """Create a new terminal tab for an app or reconnect an existing one
        set_focus: if True, switch to this tab; if False, do not change current tab
        """
        print(f"Creating/showing terminal tab for {app_name}")
        terminal = None
        tab_index = -1
        
        # Check if tab already exists by app_name
        for i in range(self.terminal_tabs.count()):
            tab_widget = self.terminal_tabs.widget(i)
            if hasattr(tab_widget, 'app_name') and tab_widget.app_name == app_name:
                terminal = tab_widget
                tab_index = i
                print(f"Found existing tab for {app_name} at index {i}")
                break
        
        # If no existing tab was found, create a new one
        if terminal is None:
            # Get short name for tab if available
            app_info = self.app_manager.apps.get(app_name, {})
            short_name = ""
            if app_info and "settings" in app_info:
                short_name = app_info["settings"].get("short_name", "")
            
            # Use short name if available, otherwise use app name
            tab_name = short_name if short_name else app_name
            
            # Create new tab with colored text edit
            terminal = ColoredTextEdit()
            terminal.app_name = app_name  # Store app_name in the widget for reference
            
            # Ensure terminal uses the correct font size
            font = QFont("Consolas", global_settings.settings["terminal_font_size"])
            terminal.setFont(font)
            
            tab_index = self.terminal_tabs.addTab(terminal, tab_name)
            print(f"Created new tab for {app_name} at index {tab_index}")
        
        # Add a message indicating this is a scheduled run
        if self.app_manager.is_app_running(app_name):
            timestamp = datetime.now().strftime('%H:%M:%S')
            terminal.append_colored_text(f"[{timestamp}] App started\n", COLORS['accent'])
            
            # Get command information for display
            app_info = self.app_manager.apps.get(app_name, {})
            if app_info and "settings" in app_info:
                command = app_info["settings"].get("command", "")
                if command:
                    terminal.append_colored_text(f"Running command: {command}\n", COLORS['accent'])
                    
                    # Add special note for Python apps to help with debugging
                    if "python" in command.lower() or command.lower().endswith(".py"):
                        terminal.append_colored_text("Note: Using unbuffered Python output (-u flag)\n", COLORS['success'])
        
        # Set as current tab if requested
        if set_focus:
            self.terminal_tabs.setCurrentIndex(tab_index)
            print(f"Set current tab to {tab_index} for {app_name}")
        
        # Force UI update
        from PyQt5.QtWidgets import QApplication
        QApplication.processEvents()
        
        # Connect process output to terminal
        if app_name in self.app_manager.processes:
            process = self.app_manager.processes[app_name]
            
            # Disconnect any existing connections to avoid duplicates
            try:
                process.readyReadStandardOutput.disconnect()
                process.readyReadStandardError.disconnect()
                process.finished.disconnect()
            except:
                pass  # Ignore if there were no connections
            
            # Connect signals
            process.readyReadStandardOutput.connect(
                lambda: self.process_output(process, terminal, app_name, "stdout"))
            process.readyReadStandardError.connect(
                lambda: self.process_output(process, terminal, app_name, "stderr"))
            process.finished.connect(
                lambda: self.process_finished(app_name))
            
            print(f"Connected process signals for {app_name}")
            
        # Update app buttons to reflect current state
        self.update_app_buttons()
    
    def process_output(self, process, terminal, app_name, output_type):
        """Handle process output"""
        try:
            if output_type == "stdout":
                data = process.readAllStandardOutput().data().decode("utf-8", errors="replace")
                color = COLORS['text']
            else:  # stderr
                data = process.readAllStandardError().data().decode("utf-8", errors="replace")
                color = COLORS['error']
            
            # Skip empty output
            if not data.strip():
                return
                
            # Apply syntax highlighting based on common patterns
            lines = data.split("\n")
            for line in lines:
                line = line.rstrip()  # Remove trailing whitespace but keep the line
                if not line:  # Skip completely empty lines
                    continue
                    
                # Special handling for Python web frameworks
                if any(pattern in line for pattern in ["Launching Gradio interface", "Running on local URL", "* Running on", "* Serving Flask app", "* Debug mode", "Starting development server"]):
                    terminal.append_colored_text(line + "\n", COLORS['success'])
                # Special handling for VIDLastFrame and similar apps
                elif any(pattern in line for pattern in ["frame", "processing", "video", "image", "extracting", "extracted", "saving"]):
                    terminal.append_colored_text(line + "\n", COLORS['accent'])
                # Highlight based on content
                elif "error" in line.lower() or "exception" in line.lower() or "fail" in line.lower():
                    terminal.append_colored_text(line + "\n", COLORS['error'])
                elif "warning" in line.lower():
                    terminal.append_colored_text(line + "\n", COLORS['warning'])
                elif "info" in line.lower() or "notice" in line.lower():
                    terminal.append_colored_text(line + "\n", COLORS['success'])
                elif "debug" in line.lower():
                    terminal.append_colored_text(line + "\n", COLORS['accent'])
                elif line.strip().startswith(">") or line.strip().startswith("$"):
                    terminal.append_colored_text(line + "\n", "#9876AA")  # Purple for commands
                elif "http://" in line or "https://" in line:
                    terminal.append_colored_text(line + "\n", COLORS['accent'])  # Highlight URLs
                else:
                    terminal.append_colored_text(line + "\n", color)
        except Exception as e:
            # Log the error and ensure we don't lose output
            error_msg = f"Error processing output: {str(e)}\n"
            terminal.append_colored_text(error_msg, COLORS['error'])
            # Try to display the raw data
            try:
                if data and isinstance(data, str):
                    terminal.append_colored_text(f"Raw output: {data}\n", COLORS['text'])
            except:
                pass
        
        # Mark tab as updated if not currently selected
        for i in range(self.terminal_tabs.count()):
            if self.terminal_tabs.widget(i) is terminal:
                if self.terminal_tabs.currentIndex() != i:
                    tab_bar = self.terminal_tabs.tabBar()
                    if hasattr(tab_bar, 'updated_tabs'):
                        # Add this tab to the updated_tabs set
                        tab_bar.updated_tabs.add(i)
                        # Force a repaint to show the updated background color
                        tab_bar.update()
                        print(f"Marked tab {i} for {app_name} as updated with blue background from process output")
                break
        
        # Force UI update
        from PyQt5.QtWidgets import QApplication
        QApplication.processEvents()
    
    def process_finished(self, app_name):
        """Handle process finished event"""
        print(f"Process finished for {app_name}")
        
        # Remove from processes dict if it's still there
        if app_name in self.app_manager.processes:
            print(f"Removing {app_name} from processes dictionary in process_finished")
            del self.app_manager.processes[app_name]
        
        # Update button state
        self.update_app_buttons()
        
        # Add finished message to terminal
        for i in range(self.terminal_tabs.count()):
            tab_widget = self.terminal_tabs.widget(i)
            if hasattr(tab_widget, 'app_name') and tab_widget.app_name == app_name:
                if isinstance(tab_widget, ColoredTextEdit):
                    timestamp = datetime.now().strftime('%H:%M:%S')
                    tab_widget.append_colored_text(f"\n[{timestamp}] Process finished\n", COLORS['warning'])
                    print(f"Added finished message to terminal tab for {app_name}")
                break
    
    def close_terminal_tab(self, index):
        """Close a terminal tab and stop the associated app"""
        tab_widget = self.terminal_tabs.widget(index)
        
        # Get the app name from the widget
        if hasattr(tab_widget, 'app_name'):
            app_name = tab_widget.app_name
            self.app_manager.stop_app(app_name)
        
        self.terminal_tabs.removeTab(index)
        self.update_app_buttons()
    
    def update_app_buttons(self, running_apps=None):
        """Update all app buttons to reflect current state
        
        Args:
            running_apps: Optional dictionary of app_name -> is_running state to use
                         instead of checking the app_manager
        """
        for i in range(self.app_list_layout.count()):
            item = self.app_list_layout.itemAt(i)
            if item and item.widget() and isinstance(item.widget(), AppButton):
                app_button = item.widget()
                app_name = app_button.app_name
                
                # Determine if the app is running
                if running_apps is not None and app_name in running_apps:
                    # Use the provided running state
                    is_running = running_apps[app_name]
                else:
                    # Check the app manager
                    is_running = self.app_manager.is_app_running(app_name)
                    
                app_button.update_state(is_running)
    
    def create_new_app(self):
        """Create a new application"""
        import xml.etree.ElementTree as ET
        import xml.dom.minidom as minidom
        
        dialog = NewAppDialog(self)
        if dialog.exec_():
            app_name, folder_name = dialog.get_app_details()
            
            if not app_name or not folder_name:
                QMessageBox.warning(self, "Error", "Application name and folder name cannot be empty.")
                return
            
            # Check if folder already exists
            app_folder_path = os.path.join(APP_FOLDER, folder_name)
            if os.path.exists(app_folder_path):
                QMessageBox.warning(self, "Error", f"Folder '{folder_name}' already exists. Please choose a different folder name.")
                return
            
            # Create app folder
            os.makedirs(app_folder_path, exist_ok=True)
            
            # Create default settings.xml file
            settings_path = os.path.join(app_folder_path, "settings.xml")
            
            # Create default settings
            settings = {
                "display_name": app_name,
                "short_name": "",
                "path": "",
                "command": "",
                "url": "",
                "autorun": "false",
                "schedule_enabled": "false",
                "schedule_type": "Interval",
                "interval_value": "60",
                "interval_unit": "Minutes",
                "schedule_time": "12:00",
                "group": ""
            }
            
            # Create XML structure
            root = ET.Element("settings")
            
            for key, value in settings.items():
                elem = ET.SubElement(root, key)
                elem.text = value
            
            # Save to file with pretty formatting
            rough_string = ET.tostring(root, 'utf-8')
            reparsed = minidom.parseString(rough_string)
            pretty_xml = reparsed.toprettyxml(indent="  ")
            
            with open(settings_path, "w") as f:
                f.write(pretty_xml)
            
            # Store the current running state of all apps
            running_apps = {}
            for app_name_key in self.app_manager.apps.keys():
                running_apps[app_name_key] = self.app_manager.is_app_running(app_name_key)
            
            # Add the new app to the app manager
            self.app_manager.apps[folder_name] = {
                "name": folder_name,
                "path": app_folder_path,
                "settings_path": settings_path,
                "settings": settings
            }
            
            # Repopulate the app list
            self.populate_app_list()
            
            # Update app buttons to restore their running state
            self.update_app_buttons(running_apps)
            
            QMessageBox.information(self, "Success", f"Application '{app_name}' created successfully.")
    
    def open_global_settings(self):
        """Open global settings dialog"""
        dialog = GlobalSettingsDialog(self)
        if dialog.exec_():
            # Update UI with new font sizes
            self.update_font_sizes()
    
    def open_group_management(self):
        """Open group management dialog"""
        dialog = GroupManagementDialog(self)
        if dialog.exec_():
            # Store the current running state of all apps
            running_apps = {}
            for app_name in self.app_manager.apps.keys():
                running_apps[app_name] = self.app_manager.is_app_running(app_name)
                
            # Refresh app list to reflect group changes
            self.populate_app_list()
            
            # Update app buttons to restore their running state
            self.update_app_buttons(running_apps)
    
    def update_font_sizes(self):
        """Update UI with new font sizes from global settings"""
        # Update app buttons
        for i in range(self.app_list_layout.count()):
            item = self.app_list_layout.itemAt(i)
            if item and item.widget():
                if isinstance(item.widget(), AppButton):
                    font = item.widget().name_label.font()
                    font.setPointSize(global_settings.settings["left_panel_font_size"])
                    item.widget().name_label.setFont(font)
                elif isinstance(item.widget(), AppGroupHeader):
                    for child in item.widget().findChildren(QLabel):
                        font = child.font()
                        font.setPointSize(global_settings.settings["left_panel_font_size"])
                        child.setFont(font)
        
        # Update terminal tabs
        for i in range(self.terminal_tabs.count()):
            terminal = self.terminal_tabs.widget(i)
            if isinstance(terminal, ColoredTextEdit):
                font = QFont("Consolas", global_settings.settings["terminal_font_size"])
                terminal.setFont(font)
        
        # Update tab bar font size
        tab_font = QFont()
        tab_font.setPointSize(global_settings.settings["left_panel_font_size"])
        self.terminal_tabs.setFont(tab_font)
        
        # Update main window stylesheet to reflect new font sizes
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{
                background-color: {COLORS['background']};
                color: {COLORS['text']};
                font-size: {global_settings.settings["left_panel_font_size"]}px;
            }}
            QTabWidget::pane {{
                border: none;
                background-color: {COLORS['panel']};
                border-radius: 8px;
            }}
            QTabBar::tab {{
                /* Removed background-color to allow custom painting */
                color: {COLORS['text']};
                padding: 16px 24px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-size: {global_settings.settings["left_panel_font_size"]}px;
                border: none;
                margin-right: 4px;
            }}
            QTabBar::tab:selected {{
                /* Keep only the border styling, background is handled by CustomTabBar */
                border-bottom: 2px solid {COLORS['accent']};
            }}
            QTabBar::tab:hover:!selected {{
                /* Lighter hover effect that won't override our custom background */
                opacity: 0.8;
            }}
            QScrollArea, QScrollBar {{
                background-color: {COLORS['background']};
                border: none;
            }}
            QScrollBar:vertical {{
                width: 20px;
                background: {COLORS['background']};
            }}
            QScrollBar:horizontal {{
                height: 20px;
                background: {COLORS['background']};
            }}
            QScrollBar::handle {{
                background-color: {COLORS['border']};
                border-radius: 10px;
                margin: 4px;
            }}
            QScrollBar::handle:hover {{
                background-color: {COLORS['text_secondary']};
            }}
            QScrollBar::add-line, QScrollBar::sub-line {{
                background: none;
                border: none;
            }}
            QScrollBar::add-page, QScrollBar::sub-page {{
                background: none;
            }}
            QLabel {{
                color: {COLORS['text']};
                font-size: {global_settings.settings["left_panel_font_size"]}px;
            }}
            QPushButton {{
                font-size: {global_settings.settings["left_panel_font_size"]}px;
                padding: 8px;
                background-color: {COLORS['accent']};
                color: white;
                border: none;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['accent_hover']};
            }}
            QLineEdit, QComboBox, QSpinBox, QCheckBox, QTimeEdit {{
                font-size: {global_settings.settings["left_panel_font_size"]}px;
                padding: 8px;
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                background-color: {COLORS['panel']};
                color: {COLORS['text']};
            }}
        """)
    
    def update_app_url(self, app_name):
        """Update the URL for an app button"""
        if app_name in self.app_manager.apps:
            url = self.app_manager.apps[app_name]["settings"].get("url", "")
            # Ensure URL is a string
            url = str(url) if url is not None else ""
            print(f"DEBUG: Updating app button URL for {app_name} to: '{url}'")
            
            # Find the app button
            for i in range(self.app_list_layout.count()):
                item = self.app_list_layout.itemAt(i)
                if item and item.widget() and isinstance(item.widget(), AppButton):
                    app_button = item.widget()
                    if app_button.app_name == app_name:
                        print(f"DEBUG: Found app button for {app_name}, current URL: '{app_button.url}'")
                        app_button.update_url(url)
                        print(f"DEBUG: Updated app button URL to: '{app_button.url}'")
                        break
    
    def open_app_settings(self, app_name):
        """Open settings dialog for an app"""
        if app_name in self.app_manager.apps:
            app_info = self.app_manager.apps[app_name]
            settings_path = app_info["settings_path"]
            
            # Print the URL before opening the dialog
            old_url = app_info["settings"].get("url", "")
            old_url = str(old_url) if old_url is not None else ""
            print(f"DEBUG: URL before opening settings dialog: '{old_url}'")
            
            dialog = SettingsDialog(app_name, settings_path, self)
            if dialog.exec_():
                # Reload app settings
                self.app_manager.apps[app_name]["settings"] = \
                    self.app_manager.load_settings(settings_path)
                
                # Print the URL after reloading settings
                new_url = self.app_manager.apps[app_name]["settings"].get("url", "")
                new_url = str(new_url) if new_url is not None else ""
                print(f"DEBUG: URL after reloading settings: '{new_url}'")
                
                # Update schedules
                self.app_manager.setup_schedules()
                
                # Store the current running state of all apps before repopulating the list
                running_apps = {}
                for app_name_key in self.app_manager.apps.keys():
                    running_apps[app_name_key] = self.app_manager.is_app_running(app_name_key)
                
                # Update the URL for this app button
                self.update_app_url(app_name)
                
                # Update the app list to reflect name changes
                self.populate_app_list()
                
                # Update tab names if app is running
                if self.app_manager.is_app_running(app_name):
                    self.update_tab_name(app_name)
                    
                # Update app buttons to restore their running state
                self.update_app_buttons(running_apps)
    
    def update_tab_name(self, app_name):
        """Update tab name based on app settings"""
        if app_name in self.app_manager.apps:
            app_settings = self.app_manager.apps[app_name]["settings"]
            
            # Find the old tab name
            old_tab_name = app_name
            for i in range(self.terminal_tabs.count()):
                tab_widget = self.terminal_tabs.widget(i)
                if hasattr(tab_widget, 'app_name') and tab_widget.app_name == app_name:
                    old_tab_name = self.terminal_tabs.tabText(i)
                    break
            
            # Get the new tab name
            new_tab_name = app_settings.get("short_name", "")
            if not new_tab_name:
                new_tab_name = app_name
            
            # Update tab name
            for i in range(self.terminal_tabs.count()):
                if self.terminal_tabs.tabText(i) == old_tab_name:
                    self.terminal_tabs.setTabText(i, new_tab_name)
                    break
    
    def auto_run_apps(self):
        """Auto-run apps marked for autorun"""
        for app_name, app_info in self.app_manager.apps.items():
            if app_info["settings"].get("autorun", False):
                self.toggle_app_state(app_name, True)
        
        # After auto-running apps, check for scheduled apps and run them after a delay
        QTimer.singleShot(5000, self.check_scheduled_apps)
    
    def _update_terminal_for_scheduled_run(self, app_name, timestamp):
        """Update the terminal tab for a scheduled run even if the app is already running"""
        # Find the terminal tab for this app
        for i in range(self.terminal_tabs.count() if hasattr(self, 'terminal_tabs') else 0):
            tab_widget = self.terminal_tabs.widget(i)
            if hasattr(tab_widget, 'app_name') and tab_widget.app_name == app_name:
                if isinstance(tab_widget, ColoredTextEdit):
                    # Add a message about the scheduled run
                    message = f"\n[{timestamp}] Scheduled run triggered"  
                    tab_widget.append_colored_text(message + "\n", COLORS['accent'])
                    print(f"Updated terminal tab for {app_name} with scheduled run message")
                    
                    # Mark tab as updated if not currently selected
                    if self.terminal_tabs.currentIndex() != i:
                        tab_bar = self.terminal_tabs.tabBar()
                        if hasattr(tab_bar, 'updated_tabs'):
                            # Make sure to add this tab to the updated_tabs set
                            tab_bar.updated_tabs.add(i)
                            # Force a repaint to show the updated background color
                            tab_bar.update()
                            print(f"Marked tab {i} for {app_name} as updated with blue background")
                    
                    # Do NOT switch tab focus here!
                    # Force the UI to update immediately
                    from PyQt5.QtWidgets import QApplication
                    QApplication.processEvents()
                    return True
        
        # If no tab exists, create one but do NOT set focus
        self.create_terminal_tab(app_name, set_focus=False)
        print(f"No terminal tab found for {app_name}, created one without focus switch")
        return False
    
    def check_scheduled_apps(self):
        """Check for scheduled apps and run them for testing"""
        print("Checking for scheduled apps...")
        for app_name, app_info in self.app_manager.apps.items():
            settings = app_info["settings"]
            if settings.get("schedule_enabled", False):
                schedule_type = settings.get("schedule_type", "Interval")
                if schedule_type == "Interval" and settings.get("interval_unit") == "Seconds":
                    print(f"Found scheduled app {app_name} with seconds interval, running it now for testing")
                    # Directly trigger the app manager's scheduled run
                    self.app_manager.scheduled_app_run(app_name)