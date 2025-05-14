"""
Path resolver module for Termora.

This module handles resolving natural language references to file paths.
"""

import os
import platform
from pathlib import Path
from typing import Dict, Optional

class PathResolver:
    """
    Resolves natural language path references to actual file system paths.
    """
    
    def __init__(self):
        """Initialize the path resolver with common directories cache."""
        self.path_cache = {}
        self.update_common_paths()
    
    def update_common_paths(self):
        """Update the cache of common paths."""
        home = Path.home()

        # Map common names to paths
        self.path_cache = {
            "home": home,
            "desktop": home / "Desktop",
            "downloads": home / "Downloads",
            "documents": home / "Documents",
            "pictures": home / "Pictures",
            "music": home / "Music",
            "videos": home / "Videos",
            "applications": Path("/Applications") if platform.system() == "Darwin" else home / "Applications"
        }
        
        # Add subdirectories of desktop (for frequently used folders)
        if (home / "Desktop").exists():
            for item in (home / "Desktop").iterdir():
                if item.is_dir():
                    self.path_cache[item.name.lower()] = item
    
    def resolve(self, text: str) -> Optional[Path]:
        """
        Resolve a natural language path reference to an actual path.
        
        Args:
            text: Natural language text referring to a location
            
        Returns:
            Path object or None if no match
        """
        
        # Check for exact matches in our cache
        text_lower = text.lower()
        
        if "folder" in text_lower or "directory" in text_lower:
            # Remove "folder"/"directory" words
            clean_text = text_lower.replace("folder", "").replace("directory", "").strip()
            
            # Check for direct matches
            for name, path in self.path_cache.items():
                if clean_text == name or clean_text == name.lower():
                    return path
            
            # Check for fuzzy matches
            for name, path in self.path_cache.items():
                if clean_text in name or name in clean_text:
                    return path
        
        return None

    def expand_path_references(self, text: str) -> str:
        """
        Expand natural language path references in a text string.
        
        Args:
            text: Text potentially containing path references
            
        Returns:
            Text with path references expanded to actual paths
        """
        
        # Common patterns for path references
        patterns = [
            r'(in|on|at|to) (?:the|my)? ([a-zA-Z0-9_\- ]+) (?:folder|directory|path)',
            r'([a-zA-Z0-9_\- ]+) (?:folder|directory|path)'
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                if len(match.groups()) > 1:
                    path_ref = match.group(2)
                else:
                    path_ref = match.group(1)
                    
                resolved_path = self.resolve(path_ref)
                if resolved_path:
                    # Replace the reference with the actual path
                    text = text.replace(match.group(0), str(resolved_path))
                    
        return text