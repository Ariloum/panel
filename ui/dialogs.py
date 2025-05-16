import os
import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
                          QFormLayout, QLineEdit, QCheckBox, QTimeEdit, QComboBox, 
                          QSpinBox, QDialogButtonBox, QListWidget, QListWidgetItem, 
                          QGridLayout, QFileDialog, QMessageBox, QInputDialog, QWidget)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt, QTime

from utils.constants import COLORS, APP_FOLDER
from utils.settings import global_settings
from models.group_manager import group_manager

class GlobalSettingsDialog(QDialog):
    """Dialog for editing global application settings"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Global Settings")
        self.setMinimumWidth(800)
        
        # Set font size based on current settings
        font = self.font()
        font.setPointSize(global_settings.settings["settings_font_size"])
        self.setFont(font)
        
        # Restore dialog size if saved in global settings
        if "dialog_size_global_settings" in global_settings.settings:
            size = global_settings.settings["dialog_size_global_settings"].split(',')
            if len(size) == 2:
                try:
                    width, height = int(size[0]), int(size[1])
                    self.resize(width, height)
                except ValueError:
                    pass
        
        layout = QVBoxLayout(self)
        
        # Form for settings
        form_layout = QFormLayout()
        
        # Font size settings
        self.left_panel_font = QSpinBox()
        self.left_panel_font.setRange(8, 48)
        self.left_panel_font.setValue(global_settings.settings["left_panel_font_size"])
        form_layout.addRow("Left Panel Font Size:", self.left_panel_font)
        
        self.terminal_font = QSpinBox()
        self.terminal_font.setRange(8, 48)
        self.terminal_font.setValue(global_settings.settings["terminal_font_size"])
        form_layout.addRow("Terminal Font Size:", self.terminal_font)
        
        self.settings_font = QSpinBox()
        self.settings_font.setRange(8, 48)
        self.settings_font.setValue(global_settings.settings["settings_font_size"])
        form_layout.addRow("Settings Font Size:", self.settings_font)
        
        # Window position settings section
        position_label = QLabel("Window Position and Size")
        position_label.setStyleSheet(f"font-weight: bold; margin-top: 20px; font-size: 22px; color: {COLORS['text']};")
        layout.addWidget(position_label)
        
        # Checkbox to enable/disable remembering window position
        self.remember_position = QCheckBox("Remember window position and size")
        self.remember_position.setChecked(True)  # Always enabled by default
        layout.addWidget(self.remember_position)
        
        # Button box
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        
        # Add layouts to main layout
        layout.addLayout(form_layout)
        layout.addWidget(button_box)
        
        # Apply dark style
        self.setStyleSheet(f"""
            QDialog {{ 
                background-color: {COLORS['background']}; 
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
            }}
            QLabel {{ 
                color: {COLORS['text']}; 
            }}
            QPushButton {{ 
                background-color: {COLORS['accent']}; 
                color: white; 
                border: none; 
                padding: 8px 16px; 
                border-radius: 4px; 
            }}
            QPushButton:hover {{ 
                background-color: {COLORS['accent_hover']}; 
            }}
            QSpinBox {{ 
                border: 1px solid {COLORS['border']}; 
                border-radius: 4px; 
                padding: 8px; 
                background-color: {COLORS['panel']}; 
                color: {COLORS['text']}; 
            }}
            QCheckBox {{ 
                color: {COLORS['text']}; 
            }}
        """)
    
    def accept(self):
        """Save settings and close dialog"""
        global_settings.settings["left_panel_font_size"] = self.left_panel_font.value()
        global_settings.settings["terminal_font_size"] = self.terminal_font.value()
        global_settings.settings["settings_font_size"] = self.settings_font.value()
        
        # Save dialog size
        global_settings.settings["dialog_size_global_settings"] = f"{self.width()},{self.height()}"
        
        if global_settings.save_settings():
            super().accept()
    
    def reject(self):
        """Override reject to save dialog size"""
        # Save dialog size even when canceling
        global_settings.settings["dialog_size_global_settings"] = f"{self.width()},{self.height()}"
        global_settings.save_settings()
        super().reject()

class SettingsDialog(QDialog):
    """Dialog for editing application settings"""
    def __init__(self, app_name, settings_path, parent=None):
        super().__init__(parent)
        self.app_name = app_name
        self.settings_path = settings_path
        self.settings = {}
        self.load_settings()
        
        self.setWindowTitle(f"{app_name} Settings")
        self.setMinimumWidth(800)  # Doubled from 400 to 800
        
        # Set larger font for the entire dialog
        font = self.font()
        font.setPointSize(global_settings.settings["settings_font_size"])
        self.setFont(font)
        
        # Restore dialog size if saved in global settings
        dialog_key = f"dialog_size_{app_name.replace(' ', '_')}"
        if dialog_key in global_settings.settings:
            size = global_settings.settings[dialog_key].split(',')
            if len(size) == 2:
                try:
                    width, height = int(size[0]), int(size[1])
                    self.resize(width, height)
                except ValueError:
                    pass
        
        layout = QVBoxLayout(self)
        
        # Form for settings
        self.form_layout = QFormLayout()
        self.settings_widgets = {}
        
        # Add app name settings
        self.name_edit = QLineEdit(self.settings.get("display_name", app_name))
        self.form_layout.addRow("Display Name:", self.name_edit)
        self.settings_widgets["display_name"] = self.name_edit
        
        self.short_name_edit = QLineEdit(self.settings.get("short_name", ""))
        self.form_layout.addRow("Short Name (for tabs):", self.short_name_edit)
        self.settings_widgets["short_name"] = self.short_name_edit
        
        # Add group selection
        self.group_combo = QComboBox()
        self.group_combo.setEditable(True)
        self.group_combo.addItem("")
        
        # Add existing groups from group manager
        existing_groups = group_manager.load_groups()
        
        for group in existing_groups:
            self.group_combo.addItem(group)
        
        # Set current group
        current_group = self.settings.get("group", "")
        if current_group:
            index = self.group_combo.findText(current_group)
            if index >= 0:
                self.group_combo.setCurrentIndex(index)
            else:
                self.group_combo.setEditText(current_group)
        
        self.form_layout.addRow("Group:", self.group_combo)
        self.settings_widgets["group"] = self.group_combo
        
        # Add basic settings
        self.path_edit = QLineEdit(self.settings.get("path", ""))
        self.form_layout.addRow("Working Directory:", self.path_edit)
        self.settings_widgets["path"] = self.path_edit
        
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self.browse_directory)
        self.form_layout.addRow("", browse_btn)
        
        self.command_edit = QLineEdit(self.settings.get("command", ""))
        self.form_layout.addRow("Command:", self.command_edit)
        self.settings_widgets["command"] = self.command_edit
        
        # Add URL field
        url_value = self.settings.get("url", "")
        # Ensure URL is a string
        url_value = str(url_value) if url_value is not None else ""
        print(f"DEBUG: Initializing URL field with: '{url_value}'")
        self.url_edit = QLineEdit(url_value)
        self.url_edit.setPlaceholderText("https://example.com")
        self.form_layout.addRow("URL:", self.url_edit)
        self.settings_widgets["url"] = self.url_edit
        
        self.autorun_check = QCheckBox("Auto-run on startup")
        self.autorun_check.setChecked(self.settings.get("autorun", False))
        self.form_layout.addRow("", self.autorun_check)
        self.settings_widgets["autorun"] = self.autorun_check
        
        # Schedule settings
        schedule_group = QDialog()
        schedule_layout = QVBoxLayout(schedule_group)
        
        self.schedule_check = QCheckBox("Enable scheduling")
        self.schedule_check.setChecked(self.settings.get("schedule_enabled", False))
        schedule_layout.addWidget(self.schedule_check)
        self.settings_widgets["schedule_enabled"] = self.schedule_check
        
        schedule_type_layout = QHBoxLayout()
        self.schedule_type = QComboBox()
        self.schedule_type.addItems(["Interval", "Daily", "Weekly", "Monthly"])
        current_type = self.settings.get("schedule_type", "Interval")
        self.schedule_type.setCurrentText(current_type)
        schedule_type_layout.addWidget(QLabel("Schedule Type:"))
        schedule_type_layout.addWidget(self.schedule_type)
        schedule_layout.addLayout(schedule_type_layout)
        self.settings_widgets["schedule_type"] = self.schedule_type
        
        # Interval settings (seconds, minutes, hours)
        interval_widget = QWidget()
        interval_layout = QHBoxLayout(interval_widget)
        self.interval_value = QSpinBox()
        self.interval_value.setRange(1, 9999)
        self.interval_value.setValue(self.settings.get("interval_value", 60))
        self.interval_unit = QComboBox()
        self.interval_unit.addItems(["Seconds", "Minutes", "Hours"])
        self.interval_unit.setCurrentText(self.settings.get("interval_unit", "Minutes"))
        interval_layout.addWidget(QLabel("Every:"))
        interval_layout.addWidget(self.interval_value)
        interval_layout.addWidget(self.interval_unit)
        schedule_layout.addWidget(interval_widget)
        self.settings_widgets["interval_value"] = self.interval_value
        self.settings_widgets["interval_unit"] = self.interval_unit
        
        # Time settings for daily/weekly/monthly
        time_widget = QWidget()
        time_layout = QHBoxLayout(time_widget)
        self.time_edit = QTimeEdit()
        time_str = self.settings.get("schedule_time", "12:00")
        time_parts = time_str.split(":")
        if len(time_parts) >= 2:
            self.time_edit.setTime(QTime(int(time_parts[0]), int(time_parts[1])))
        time_layout.addWidget(QLabel("At time:"))
        time_layout.addWidget(self.time_edit)
        schedule_layout.addWidget(time_widget)
        self.settings_widgets["schedule_time"] = self.time_edit
        
        # Add custom parameters section
        custom_params_label = QLabel("Custom Parameters:")
        custom_params_label.setStyleSheet(f"font-weight: bold; margin-top: 20px; font-size: 22px; color: {COLORS['text']};")
        layout.addWidget(custom_params_label)
        
        self.params_layout = QGridLayout()
        self.params_layout.addWidget(QLabel("Name"), 0, 0)
        self.params_layout.addWidget(QLabel("Value"), 0, 1)
        
        # Add existing custom parameters
        self.param_widgets = []
        row = 1
        for key, value in self.settings.items():
            if key not in ["path", "command", "autorun", "schedule_enabled", 
                          "schedule_type", "interval_value", "interval_unit", "schedule_time",
                          "display_name", "short_name", "group", "url"]:
                self.add_param_row(row, key, value)
                row += 1
        
        # Add button for new parameter
        add_param_btn = QPushButton("Add Parameter")
        add_param_btn.clicked.connect(self.add_new_parameter)
        
        # Button box
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        
        # Add all layouts to main layout
        layout.addLayout(self.form_layout)
        layout.addWidget(schedule_group)
        layout.addLayout(self.params_layout)
        layout.addWidget(add_param_btn)
        layout.addWidget(button_box)
        
        # Connect signals
        self.schedule_type.currentTextChanged.connect(self.update_schedule_ui)
        self.update_schedule_ui(current_type)
        
        # Apply dark style
        self.setStyleSheet(f"""
            QDialog {{ 
                background-color: {COLORS['background']}; 
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
            }}
            QLabel {{ 
                color: {COLORS['text']}; 
            }}
            QPushButton {{ 
                background-color: {COLORS['accent']}; 
                color: white; 
                border: none; 
                padding: 8px 16px; 
                border-radius: 4px; 
            }}
            QPushButton:hover {{ 
                background-color: {COLORS['accent_hover']}; 
            }}
            QLineEdit, QComboBox, QSpinBox, QTimeEdit {{ 
                border: 1px solid {COLORS['border']}; 
                border-radius: 4px; 
                padding: 8px; 
                background-color: {COLORS['panel']}; 
                color: {COLORS['text']}; 
            }}
            QCheckBox {{ 
                color: {COLORS['text']}; 
            }}
        """)
    
    def update_schedule_ui(self, schedule_type):
        """Update UI based on selected schedule type"""
        if schedule_type == "Interval":
            self.interval_value.setVisible(True)
            self.interval_unit.setVisible(True)
            self.time_edit.setVisible(False)
        else:
            self.interval_value.setVisible(False)
            self.interval_unit.setVisible(False)
            self.time_edit.setVisible(True)
    
    def add_param_row(self, row, key="", value=""):
        """Add a row for custom parameter"""
        # Don't allow adding a URL parameter as it's already in the main form
        if key.lower() == "url":
            print(f"DEBUG: Skipping adding URL parameter in custom parameters section")
            return
            
        key_edit = QLineEdit(key)
        value_edit = QLineEdit(str(value))
        delete_btn = QPushButton("X")
        delete_btn.setMaximumWidth(30)
        
        self.params_layout.addWidget(key_edit, row, 0)
        self.params_layout.addWidget(value_edit, row, 1)
        self.params_layout.addWidget(delete_btn, row, 2)
        
        param_row = {"key": key_edit, "value": value_edit, "row": row, "delete": delete_btn}
        self.param_widgets.append(param_row)
        
        delete_btn.clicked.connect(lambda: self.delete_param_row(param_row))
    
    def delete_param_row(self, param_row):
        """Delete a parameter row"""
        for widget in [param_row["key"], param_row["value"], param_row["delete"]]:
            self.params_layout.removeWidget(widget)
            widget.deleteLater()
            
    def add_new_parameter(self):
        """Add a new parameter with validation"""
        # Get parameter name from user
        param_name, ok = QInputDialog.getText(self, "Add Parameter", "Enter parameter name:")
        
        if ok and param_name.strip():
            # Check if it's a reserved parameter name
            reserved_names = ["path", "command", "autorun", "schedule_enabled", 
                             "schedule_type", "interval_value", "interval_unit", "schedule_time",
                             "display_name", "short_name", "group", "url"]
            
            if param_name.strip().lower() in [name.lower() for name in reserved_names]:
                QMessageBox.warning(self, "Reserved Parameter", 
                                   f"'{param_name}' is a reserved parameter name. Please use a different name.")
                return
                
            # Check if parameter already exists
            for param in self.param_widgets:
                if param["key"].text().strip().lower() == param_name.strip().lower():
                    QMessageBox.warning(self, "Duplicate Parameter", 
                                       f"Parameter '{param_name}' already exists.")
                    return
            
            # Add the parameter row
            self.add_param_row(len(self.param_widgets) + 1, param_name.strip(), "")
    
    def browse_directory(self):
        """Open file dialog to browse for a directory"""
        directory = QFileDialog.getExistingDirectory(self, "Select Directory", self.path_edit.text())
        if directory:
            self.path_edit.setText(directory)
            
    def load_settings(self):
        """Load settings from XML file"""
        try:
            if os.path.exists(self.settings_path):
                tree = ET.parse(self.settings_path)
                root = tree.getroot()
                
                for elem in root:
                    if elem.tag == "parameters":
                        for param in elem:
                            self.settings[param.get("name")] = param.get("value")
                    else:
                        self.settings[elem.tag] = elem.text
                        if elem.tag == "url":
                            print(f"DEBUG: SettingsDialog loaded URL: {elem.text}")
                        
                # Convert boolean strings to actual booleans
                for key in ["autorun", "schedule_enabled"]:
                    if key in self.settings:
                        self.settings[key] = self.settings[key].lower() == "true"
                        
                # Convert numeric strings to integers
                if "interval_value" in self.settings:
                    self.settings["interval_value"] = int(self.settings["interval_value"])
                    
                # Print the URL after loading
                print(f"DEBUG: SettingsDialog final URL: {self.settings.get('url', '')}")
        except Exception as e:
            print(f"Error loading settings: {e}")
    
    def save_settings(self):
        """Save settings to XML file"""
        try:
            root = ET.Element("settings")
            
            # Add basic settings
            display_name_elem = ET.SubElement(root, "display_name")
            display_name_elem.text = self.name_edit.text()
            
            short_name_elem = ET.SubElement(root, "short_name")
            short_name_elem.text = self.short_name_edit.text()
            
            path_elem = ET.SubElement(root, "path")
            path_elem.text = self.path_edit.text()
            
            command_elem = ET.SubElement(root, "command")
            command_elem.text = self.command_edit.text()
            
            # Add URL
            url_elem = ET.SubElement(root, "url")
            url_text = self.url_edit.text().strip()
            url_elem.text = url_text
            print(f"DEBUG: Saving URL: '{url_text}'")
            
            autorun_elem = ET.SubElement(root, "autorun")
            autorun_elem.text = str(self.autorun_check.isChecked())
            
            # Add group and update group manager
            group_elem = ET.SubElement(root, "group")
            group_text = self.group_combo.currentText().strip()
            group_elem.text = group_text
            
            # Add to group manager if it's a new group
            if group_text:
                group_manager.add_group(group_text)
            
            # Add schedule settings
            schedule_enabled = ET.SubElement(root, "schedule_enabled")
            schedule_enabled.text = str(self.schedule_check.isChecked())
            
            schedule_type = ET.SubElement(root, "schedule_type")
            schedule_type.text = self.schedule_type.currentText()
            
            interval_value = ET.SubElement(root, "interval_value")
            interval_value.text = str(self.interval_value.value())
            
            interval_unit = ET.SubElement(root, "interval_unit")
            interval_unit.text = self.interval_unit.currentText()
            
            schedule_time = ET.SubElement(root, "schedule_time")
            schedule_time.text = self.time_edit.time().toString("HH:mm")
            
            # Add custom parameters
            params_elem = ET.SubElement(root, "parameters")
            for param in self.param_widgets:
                key = param["key"].text().strip()
                value = param["value"].text().strip()
                # Skip URL parameters as they're handled in the main form
                if key and key.lower() != "url":
                    param_elem = ET.SubElement(params_elem, "param")
                    param_elem.set("name", key)
                    param_elem.set("value", value)
            
            # Save to file with pretty formatting
            rough_string = ET.tostring(root, 'utf-8')
            reparsed = minidom.parseString(rough_string)
            pretty_xml = reparsed.toprettyxml(indent="  ")
            
            os.makedirs(os.path.dirname(self.settings_path), exist_ok=True)
            with open(self.settings_path, "w") as f:
                f.write(pretty_xml)
                
            return True
        except Exception as e:
            print(f"Error saving settings: {e}")
            return False
    
    def accept(self):
        """Override accept to save settings"""
        if self.save_settings():
            super().accept()

class NewAppDialog(QDialog):
    """Dialog for creating a new application"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create New Application")
        self.setMinimumWidth(500)
        
        # Set font size based on current settings
        font = self.font()
        font.setPointSize(global_settings.settings["settings_font_size"])
        self.setFont(font)
        
        layout = QVBoxLayout(self)
        
        # Form for app details
        form_layout = QFormLayout()
        
        # App name field
        self.app_name_edit = QLineEdit()
        form_layout.addRow("Application Name:", self.app_name_edit)
        
        # Folder name field
        self.folder_name_edit = QLineEdit()
        form_layout.addRow("Folder Name:", self.folder_name_edit)
        
        # Connect app name to auto-generate folder name
        self.app_name_edit.textChanged.connect(self.update_folder_name)
        
        layout.addLayout(form_layout)
        
        # Button box
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        # Apply dark style
        self.setStyleSheet(f"""
            QDialog {{ 
                background-color: {COLORS['background']}; 
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
            }}
            QLabel {{ 
                color: {COLORS['text']}; 
            }}
            QPushButton {{ 
                background-color: {COLORS['accent']}; 
                color: white; 
                border: none; 
                padding: 8px 16px; 
                border-radius: 4px; 
            }}
            QPushButton:hover {{ 
                background-color: {COLORS['accent_hover']}; 
            }}
            QLineEdit {{ 
                border: 1px solid {COLORS['border']}; 
                border-radius: 4px; 
                padding: 8px; 
                background-color: {COLORS['panel']}; 
                color: {COLORS['text']}; 
            }}
        """)
    
    def update_folder_name(self, text):
        """Auto-generate folder name from app name"""
        # Convert app name to a valid folder name (lowercase, replace spaces with underscores)
        folder_name = text.lower().replace(" ", "_")
        # Remove any special characters
        folder_name = ''.join(c for c in folder_name if c.isalnum() or c == '_')
        self.folder_name_edit.setText(folder_name)
    
    def get_app_details(self):
        """Return the app name and folder name"""
        return self.app_name_edit.text().strip(), self.folder_name_edit.text().strip()


class GroupManagementDialog(QDialog):
    """Dialog for managing app groups"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Manage Groups")
        self.setMinimumWidth(800)
        self.setMinimumHeight(600)
        
        # Set font size based on current settings
        font = self.font()
        font.setPointSize(global_settings.settings["settings_font_size"])
        self.setFont(font)
        
        # Restore dialog size if saved in global settings
        if "dialog_size_group_management" in global_settings.settings:
            size = global_settings.settings["dialog_size_group_management"].split(',')
            if len(size) == 2:
                try:
                    width, height = int(size[0]), int(size[1])
                    self.resize(width, height)
                except ValueError:
                    pass
        
        layout = QVBoxLayout(self)
        
        # Group list
        self.group_list = QListWidget()
        self.group_list.setSelectionMode(QListWidget.SingleSelection)
        layout.addWidget(QLabel("Groups:"))
        layout.addWidget(self.group_list)
        
        # Load existing groups
        self.load_groups()
        
        # Buttons for group management
        button_layout = QHBoxLayout()
        
        self.add_btn = QPushButton("Add Group")
        self.add_btn.clicked.connect(self.add_group)
        button_layout.addWidget(self.add_btn)
        
        self.rename_btn = QPushButton("Rename Group")
        self.rename_btn.clicked.connect(self.rename_group)
        button_layout.addWidget(self.rename_btn)
        
        self.delete_btn = QPushButton("Delete Group")
        self.delete_btn.clicked.connect(self.delete_group)
        button_layout.addWidget(self.delete_btn)
        
        layout.addLayout(button_layout)
        
        # Apps in group
        layout.addWidget(QLabel("Apps in selected group:"))
        self.apps_list = QListWidget()
        layout.addWidget(self.apps_list)
        
        # Connect group selection to update apps list
        self.group_list.currentItemChanged.connect(self.update_apps_list)
        
        # Button box
        button_box = QDialogButtonBox(QDialogButtonBox.Close)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        # Apply dark style
        self.setStyleSheet(f"""
            QDialog {{ 
                background-color: {COLORS['background']}; 
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
            }}
            QLabel {{ 
                color: {COLORS['text']}; 
            }}
            QPushButton {{ 
                background-color: {COLORS['accent']}; 
                color: white; 
                border: none; 
                padding: 8px 16px; 
                border-radius: 4px; 
            }}
            QPushButton:hover {{ 
                background-color: {COLORS['accent_hover']}; 
            }}
            QListWidget {{ 
                border: 1px solid {COLORS['border']}; 
                border-radius: 4px; 
                background-color: {COLORS['panel']}; 
                color: {COLORS['text']}; 
            }}
            QLineEdit {{ 
                border: 1px solid {COLORS['border']}; 
                border-radius: 4px; 
                padding: 8px; 
                background-color: {COLORS['panel']}; 
                color: {COLORS['text']}; 
            }}
        """)
    
    def load_groups(self):
        """Load existing groups from group manager"""
        self.group_list.clear()
        
        # Get all groups from group manager
        groups = group_manager.load_groups()
        
        # Add groups to list
        for group in groups:
            self.group_list.addItem(group)
    
    def update_apps_list(self, current, previous):
        """Update the list of apps in the selected group"""
        self.apps_list.clear()
        
        if not current:
            return
        
        selected_group = current.text()
        
        # Find apps in this group
        for app_dir in os.listdir(APP_FOLDER):
            app_path = os.path.join(APP_FOLDER, app_dir)
            if os.path.isdir(app_path):
                settings_path = os.path.join(app_path, "settings.xml")
                if os.path.exists(settings_path):
                    try:
                        tree = ET.parse(settings_path)
                        root = tree.getroot()
                        
                        for elem in root:
                            if elem.tag == "group" and elem.text and elem.text.strip() == selected_group:
                                # Add app to list
                                app_name = os.path.basename(app_path)
                                self.apps_list.addItem(app_name)
                                break
                    except Exception as e:
                        print(f"Error checking app group: {e}")
    
    def add_group(self):
        """Add a new group"""
        # Get group name from user
        group_name, ok = QInputDialog.getText(self, "Add Group", "Enter group name:")
        
        if ok and group_name.strip():
            # Add group using group manager
            if group_manager.add_group(group_name.strip()):
                # Refresh group list
                self.load_groups()
                
                # Select the new group
                items = self.group_list.findItems(group_name.strip(), Qt.MatchExactly)
                if items:
                    self.group_list.setCurrentItem(items[0])
            else:
                QMessageBox.warning(self, "Error", "Failed to add group")
    
    def rename_group(self):
        """Rename selected group"""
        current_item = self.group_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Warning", "Please select a group to rename")
            return
        
        old_name = current_item.text()
        new_name, ok = QInputDialog.getText(self, "Rename Group", "Enter new group name:", text=old_name)
        
        if ok and new_name.strip() and new_name.strip() != old_name:
            # Rename group using group manager
            if group_manager.rename_group(old_name, new_name.strip()):
                # Refresh group list
                self.load_groups()
                
                # Select the renamed group
                items = self.group_list.findItems(new_name.strip(), Qt.MatchExactly)
                if items:
                    self.group_list.setCurrentItem(items[0])
            else:
                QMessageBox.warning(self, "Error", "Failed to rename group")
    
    def delete_group(self):
        """Delete selected group"""
        current_item = self.group_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Warning", "Please select a group to delete")
            return
        
        group_name = current_item.text()
        reply = QMessageBox.question(self, "Confirm Delete", 
                                    f"Are you sure you want to delete the group '{group_name}'?", 
                                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            # Delete group using group manager
            if group_manager.delete_group(group_name):
                # Remove from list
                row = self.group_list.row(current_item)
                self.group_list.takeItem(row)
                self.apps_list.clear()
            else:
                QMessageBox.warning(self, "Error", "Failed to delete group")
    
    def closeEvent(self, event):
        """Override close event to save dialog size"""
        # Save dialog size
        global_settings.settings["dialog_size_group_management"] = f"{self.width()},{self.height()}"
        global_settings.save_settings()
        event.accept()
    
    def reject(self):
        """Override reject to save dialog size"""
        # Save dialog size
        global_settings.settings["dialog_size_group_management"] = f"{self.width()},{self.height()}"
        global_settings.save_settings()
        super().reject()