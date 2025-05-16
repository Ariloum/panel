import os
import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom
from utils.constants import APP_FOLDER

class GroupManager:
    """Class to manage app groups"""
    def __init__(self):
        self.groups_path = "groups.xml"
        self.groups = set()
        self.load_groups()
    
    def load_groups(self):
        """Load groups from XML file and app settings"""
        self.groups = set()
        
        # Load from groups.xml if it exists
        if os.path.exists(self.groups_path):
            try:
                tree = ET.parse(self.groups_path)
                root = tree.getroot()
                
                for group_elem in root.findall("group"):
                    if group_elem.text and group_elem.text.strip():
                        self.groups.add(group_elem.text.strip())
            except Exception as e:
                print(f"Error loading groups: {e}")
        
        # Also load from app settings to ensure we have all groups
        for app_dir in os.listdir(APP_FOLDER):
            app_path = os.path.join(APP_FOLDER, app_dir)
            if os.path.isdir(app_path):
                settings_path = os.path.join(app_path, "settings.xml")
                if os.path.exists(settings_path):
                    try:
                        tree = ET.parse(settings_path)
                        root = tree.getroot()
                        for elem in root:
                            if elem.tag == "group" and elem.text and elem.text.strip():
                                self.groups.add(elem.text.strip())
                    except Exception:
                        pass
        
        return sorted(self.groups)
    
    def save_groups(self):
        """Save groups to XML file"""
        try:
            root = ET.Element("groups")
            
            for group_name in sorted(self.groups):
                group_elem = ET.SubElement(root, "group")
                group_elem.text = group_name
            
            # Save to file with pretty formatting
            rough_string = ET.tostring(root, 'utf-8')
            reparsed = minidom.parseString(rough_string)
            pretty_xml = reparsed.toprettyxml(indent="  ")
            
            with open(self.groups_path, "w") as f:
                f.write(pretty_xml)
                
            return True
        except Exception as e:
            print(f"Error saving groups: {e}")
            return False
    
    def add_group(self, group_name):
        """Add a new group"""
        if group_name and group_name.strip():
            self.groups.add(group_name.strip())
            return self.save_groups()
        return False
    
    def rename_group(self, old_name, new_name):
        """Rename a group"""
        if old_name in self.groups and new_name and new_name.strip():
            self.groups.remove(old_name)
            self.groups.add(new_name.strip())
            
            # Update group name in all apps
            for app_dir in os.listdir(APP_FOLDER):
                app_path = os.path.join(APP_FOLDER, app_dir)
                if os.path.isdir(app_path):
                    settings_path = os.path.join(app_path, "settings.xml")
                    if os.path.exists(settings_path):
                        try:
                            tree = ET.parse(settings_path)
                            root = tree.getroot()
                            updated = False
                            
                            for elem in root:
                                if elem.tag == "group" and elem.text and elem.text.strip() == old_name:
                                    elem.text = new_name
                                    updated = True
                            
                            if updated:
                                # Save updated settings
                                rough_string = ET.tostring(root, 'utf-8')
                                reparsed = minidom.parseString(rough_string)
                                pretty_xml = reparsed.toprettyxml(indent="  ")
                                
                                with open(settings_path, "w") as f:
                                    f.write(pretty_xml)
                        except Exception as e:
                            print(f"Error updating group name: {e}")
            
            return self.save_groups()
        return False
    
    def delete_group(self, group_name):
        """Delete a group"""
        if group_name in self.groups:
            self.groups.remove(group_name)
            
            # Remove group from all apps
            for app_dir in os.listdir(APP_FOLDER):
                app_path = os.path.join(APP_FOLDER, app_dir)
                if os.path.isdir(app_path):
                    settings_path = os.path.join(app_path, "settings.xml")
                    if os.path.exists(settings_path):
                        try:
                            tree = ET.parse(settings_path)
                            root = tree.getroot()
                            updated = False
                            
                            for elem in root:
                                if elem.tag == "group" and elem.text and elem.text.strip() == group_name:
                                    elem.text = ""
                                    updated = True
                            
                            if updated:
                                # Save updated settings
                                rough_string = ET.tostring(root, 'utf-8')
                                reparsed = minidom.parseString(rough_string)
                                pretty_xml = reparsed.toprettyxml(indent="  ")
                                
                                with open(settings_path, "w") as f:
                                    f.write(pretty_xml)
                        except Exception as e:
                            print(f"Error removing group: {e}")
            
            return self.save_groups()
        return False

# Initialize group manager
group_manager = GroupManager()