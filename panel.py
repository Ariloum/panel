import sys
import os
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon

# Import our modules
from ui.main_window import MainWindow
from utils.constants import ICON_PATHS

def main():
    # Create application
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Use Fusion style for consistent look across platforms
    
    # Set application icon
    if os.path.exists(ICON_PATHS.get("app", "")):
        app.setWindowIcon(QIcon(ICON_PATHS["app"]))
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    # Run application
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()