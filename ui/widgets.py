from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
                          QTextEdit, QFrame, QSizePolicy)
from PyQt5.QtGui import QIcon, QColor, QTextCharFormat, QTextCursor, QFont
from PyQt5.QtCore import Qt, pyqtSignal, QSize

from utils.constants import COLORS, ICON_PATHS, ICON_SIZE
from utils.settings import global_settings

class ColoredTextEdit(QTextEdit):
    """Text edit widget with colored text support"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        font = QFont("Consolas", global_settings.settings["terminal_font_size"])
        self.setFont(font)
        self.setStyleSheet(f"background-color: {COLORS['panel']}; color: {COLORS['text']}; font-size: {global_settings.settings['terminal_font_size']}px;")
        
    def append_colored_text(self, text, color=COLORS['text']):
        cursor = self.textCursor()
        format = QTextCharFormat()
        format.setForeground(QColor(color))
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(text, format)
        self.setTextCursor(cursor)
        self.ensureCursorVisible()
        
        # Force UI update
        from PyQt5.QtWidgets import QApplication
        QApplication.processEvents()

class AppGroupHeader(QWidget):
    """Widget for app group headers with separator lines"""
    def __init__(self, group_name, parent=None):
        super().__init__(parent)
        self.group_name = group_name
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 10, 5, 2)  # Reduced spacing
        
        # Left separator line
        left_line = QFrame()
        left_line.setFrameShape(QFrame.HLine)
        left_line.setFixedHeight(1)  # Thinner line
        left_line.setStyleSheet(f"background-color: {COLORS['separator']};")
        
        # Group name label
        name_label = QLabel(group_name)
        font = QFont()
        font.setPointSize(global_settings.settings["left_panel_font_size"])
        name_label.setFont(font)
        name_label.setStyleSheet(f"color: {COLORS['text_secondary']}; text-overflow: ellipsis;")
        name_label.setAlignment(Qt.AlignCenter)
        
        # Adjust width based on font size to prevent overlap
        if global_settings.settings["left_panel_font_size"] >= 28:
            # For larger font sizes, allow more space
            min_width = 180
            name_label.setMinimumWidth(min_width)
            name_label.setMaximumWidth(min_width)
        else:
            # For smaller font sizes, use fixed width
            name_label.setFixedWidth(100)
        
        # Enable word wrapping for long group names
        name_label.setWordWrap(True)
        
        # Right separator line
        right_line = QFrame()
        right_line.setFrameShape(QFrame.HLine)
        right_line.setFixedHeight(1)  # Thinner line
        right_line.setStyleSheet(f"background-color: {COLORS['separator']};")
        
        # Add widgets to layout
        layout.addWidget(left_line)
        layout.addWidget(name_label)
        layout.addWidget(right_line)

class AppButton(QWidget):
    """Custom widget for app buttons in the left panel"""
    clicked = pyqtSignal(str)  # Signal emitted when app is clicked
    toggle_state = pyqtSignal(str, bool)  # Signal emitted when app state is toggled
    settings_clicked = pyqtSignal(str)  # Signal emitted when settings button is clicked
    
    def __init__(self, app_name, app_info, parent=None):
        super().__init__(parent)
        self.app_name = app_name
        self.app_info = app_info
        self.is_running = False
        
        # Get display name and short name from settings
        self.display_name = app_info["settings"].get("display_name", "")
        if not self.display_name:
            self.display_name = app_name
        
        # Get URL from settings
        self.url = app_info["settings"].get("url", "")
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)  # Reduced margins
        
        # State button (play/stop only - no pause)
        self.state_btn = QPushButton()
        self.state_btn.setIcon(QIcon(ICON_PATHS["play"]))
        self.state_btn.setIconSize(QSize(ICON_SIZE, ICON_SIZE))
        self.state_btn.setFixedSize(ICON_SIZE + 8, ICON_SIZE + 8)  # Smaller button
        self.state_btn.clicked.connect(self.toggle_app_state)
        layout.addWidget(self.state_btn)
        
        # App name
        self.name_label = QLabel(self.display_name)
        font = QFont()
        font.setPointSize(global_settings.settings["left_panel_font_size"])
        self.name_label.setFont(font)
        self.name_label.setStyleSheet(f"color: {COLORS['text']};")
        layout.addWidget(self.name_label)
        
        # Spacer - Add stretch to push buttons to the right
        layout.addStretch()
        
        # Web button for URL (if present) - Now positioned next to settings button
        self.www_btn = None
        if self.url:
            self.www_btn = QPushButton()
            self.www_btn.setIcon(QIcon(ICON_PATHS["web"]))
            self.www_btn.setIconSize(QSize(ICON_SIZE, ICON_SIZE))
            self.www_btn.setFixedSize(ICON_SIZE + 8, ICON_SIZE + 8)  # Same size as play button
            self.www_btn.setToolTip("Open URL in browser")
            self.www_btn.setStyleSheet(f"""
                QPushButton {{ 
                    background-color: transparent; 
                    border-radius: 4px; 
                    border: none;
                    padding: 4px;
                }}
                QPushButton:hover {{ 
                    background-color: rgba(255, 255, 255, 0.1); 
                }}
            """)
            self.www_btn.clicked.connect(self.open_url)
            layout.addWidget(self.www_btn)
        
        # Settings button - Now positioned after the URL button
        self.settings_btn = QPushButton()
        self.settings_btn.setIcon(QIcon(ICON_PATHS["settings"]))
        self.settings_btn.setIconSize(QSize(ICON_SIZE, ICON_SIZE))
        self.settings_btn.setFixedSize(ICON_SIZE + 8, ICON_SIZE + 8)  # Smaller button
        self.settings_btn.clicked.connect(lambda: self.settings_clicked.emit(self.app_name))
        layout.addWidget(self.settings_btn)
        
        # Style - Flat design
        self.setStyleSheet(f"""
            QWidget {{ 
                background-color: {COLORS['panel']}; 
                border-radius: 4px; 
                color: {COLORS['text']};
                padding: 2px;
                border: none;
            }}
            QWidget:hover {{ 
                background-color: {COLORS['border']}; 
            }}
            QPushButton {{ 
                background-color: transparent; 
                border-radius: 4px; 
                border: none;
                padding: 4px;
            }}
            QPushButton:hover {{ 
                background-color: rgba(255, 255, 255, 0.1); 
            }}
        """)
        
        # Make the whole widget clickable
        self.setCursor(Qt.PointingHandCursor)
    
    def open_url(self):
        """Open the URL in the default browser"""
        import webbrowser
        if self.url:
            webbrowser.open(self.url)
    
    def mousePressEvent(self, event):
        """Handle mouse press events"""
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.app_name)
        super().mousePressEvent(event)
    
    def toggle_app_state(self):
        """Toggle app running state"""
        self.toggle_state.emit(self.app_name, not self.is_running)
    
    def update_display_name(self, new_display_name):
        """Update the display name shown on the button"""
        self.display_name = new_display_name
        self.name_label.setText(self.display_name)
    
    def update_url(self, new_url):
        """Update the URL and add/remove WWW button as needed"""
        print(f"DEBUG: AppButton.update_url called for {self.app_name} - Old URL: '{self.url}', New URL: '{new_url}'")
        old_url = self.url
        # Ensure new_url is a string
        new_url = str(new_url) if new_url is not None else ""
        self.url = new_url
        self.url = new_url
        
        # If URL was added and WWW button doesn't exist
        if new_url and not self.www_btn:
            print(f"DEBUG: Adding WWW button for {self.app_name}")
            layout = self.layout()
            self.www_btn = QPushButton()
            self.www_btn.setIcon(QIcon(ICON_PATHS["web"]))
            self.www_btn.setIconSize(QSize(ICON_SIZE, ICON_SIZE))
            self.www_btn.setFixedSize(ICON_SIZE + 8, ICON_SIZE + 8)  # Same size as play button
            self.www_btn.setToolTip(f"Open URL: {new_url}")
            self.www_btn.setStyleSheet(f"""
                QPushButton {{ 
                    background-color: transparent; 
                    border-radius: 4px; 
                    border: none;
                    padding: 4px;
                }}
                QPushButton:hover {{ 
                    background-color: rgba(255, 255, 255, 0.1); 
                }}
            """)
            self.www_btn.clicked.connect(self.open_url)
            # Insert before the settings button (which is the last widget)
            layout.insertWidget(layout.count() - 1, self.www_btn)
        
        # If URL was removed and WWW button exists
        elif not new_url and self.www_btn:
            print(f"DEBUG: Removing WWW button for {self.app_name}")
            self.www_btn.deleteLater()
            self.www_btn = None
        
        # If URL was changed and WWW button exists
        elif new_url and self.www_btn:
            print(f"DEBUG: Updating WWW button tooltip for {self.app_name}")
            self.www_btn.setToolTip(f"Open URL: {new_url}")
            # Make sure the URL is actually updated for the open_url method
            self.url = new_url
    
    def update_state(self, is_running):
        """Update the state button based on app running state"""
        self.is_running = is_running
        if is_running:
            # For running apps, show stop icon with green background
            self.state_btn.setIcon(QIcon(ICON_PATHS["stop"]))
            self.setStyleSheet(f"""
                QWidget {{ 
                    background-color: {COLORS['success']}; 
                    border-radius: 4px; 
                    color: white;
                    padding: 2px;
                    border: none;
                }}
                QWidget:hover {{ 
                    background-color: #43A047; 
                }}
                QPushButton {{ 
                    background-color: transparent; 
                    border-radius: 4px; 
                    border: none;
                    padding: 4px;
                }}
                QPushButton:hover {{ 
                    background-color: rgba(255, 255, 255, 0.2); 
                }}
                QLabel {{ 
                    color: white; 
                }}
            """)
            
            # Update WWW button style if it exists
            if self.www_btn:
                self.www_btn.setStyleSheet(f"""
                    QPushButton {{ 
                        background-color: transparent; 
                        border-radius: 4px; 
                        border: none;
                        padding: 4px;
                    }}
                    QPushButton:hover {{ 
                        background-color: rgba(255, 255, 255, 0.2); 
                    }}
                """)
        else:
            self.state_btn.setIcon(QIcon(ICON_PATHS["play"]))
            self.setStyleSheet(f"""
                QWidget {{ 
                    background-color: {COLORS['panel']}; 
                    border-radius: 4px; 
                    color: {COLORS['text']};
                    padding: 2px;
                    border: none;
                }}
                QWidget:hover {{ 
                    background-color: {COLORS['border']}; 
                }}
                QPushButton {{ 
                    background-color: transparent; 
                    border-radius: 4px; 
                    border: none;
                    padding: 4px;
                }}
                QPushButton:hover {{ 
                    background-color: rgba(255, 255, 255, 0.1); 
                }}
                QLabel {{ 
                    color: {COLORS['text']}; 
                }}
            """)
            
            # Update WWW button style if it exists
            if self.www_btn:
                self.www_btn.setStyleSheet(f"""
                    QPushButton {{ 
                        background-color: transparent; 
                        border-radius: 4px; 
                        border: none;
                        padding: 4px;
                    }}
                    QPushButton:hover {{ 
                        background-color: rgba(255, 255, 255, 0.1); 
                    }}
                """)