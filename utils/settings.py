import os
import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom

class GlobalSettings:
    """Global application settings"""
    def __init__(self):
        self.settings_path = "global_settings.xml"
        self.settings = {
            "left_panel_font_size": 20,
            "terminal_font_size": 20,
            "settings_font_size": 20,
            "window_x": 100,
            "window_y": 100,
            "window_width": 1400,
            "window_height": 800,
            "splitter_sizes": [300, 700]
        }
        self.load_settings()
    
    def load_settings(self):
        """Load settings from XML file"""
        try:
            if os.path.exists(self.settings_path):
                tree = ET.parse(self.settings_path)
                root = tree.getroot()
                
                for elem in root:
                    if elem.tag in self.settings and elem.text:
                        # Special handling for splitter_sizes which should be a list of integers
                        if elem.tag == "splitter_sizes":
                            try:
                                # Try to parse as a list of integers
                                sizes_str = elem.text.strip('[]').split(',')
                                self.settings[elem.tag] = [int(size.strip()) for size in sizes_str if size.strip()]
                            except Exception:
                                # Keep default if parsing fails
                                pass
                        else:
                            # Convert numeric strings to integers
                            try:
                                self.settings[elem.tag] = int(elem.text)
                            except ValueError:
                                self.settings[elem.tag] = elem.text
        except Exception as e:
            print(f"Error loading global settings: {e}")
    
    def save_settings(self):
        """Save settings to XML file"""
        try:
            root = ET.Element("global_settings")
            
            for key, value in self.settings.items():
                elem = ET.SubElement(root, key)
                elem.text = str(value)
            
            # Save to file with pretty formatting
            rough_string = ET.tostring(root, 'utf-8')
            reparsed = minidom.parseString(rough_string)
            pretty_xml = reparsed.toprettyxml(indent="  ")
            
            with open(self.settings_path, "w") as f:
                f.write(pretty_xml)
                
            return True
        except Exception as e:
            print(f"Error saving global settings: {e}")
            return False

# Initialize global settings
global_settings = GlobalSettings()