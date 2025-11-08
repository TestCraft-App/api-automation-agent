import os
from pathlib import Path
from typing import List, Set


class FolderStructureGenerator:
    """
    Generates a concise, machine-readable folder/file tree from a given root path,
    respecting include/exclude rules, depth, and file count limits.
    """

    def __init__(self, max_depth: int = 3, max_files: int = 100, ignore_list: Set[str] = None):
        self.max_depth = max_depth
        self.max_files = max_files
        self.file_count = 0
        self.tree_output = []

        if ignore_list is None:
            self.ignore_list = {"node_modules", "dist", "logs", ".git", ".vscode", ".DS_Store", "__pycache__"}
        else:
            self.ignore_list = ignore_list

    def _is_ignored(self, item_name: str) -> bool:
        """Checks if a file or folder should be ignored."""
        if item_name in self.ignore_list:
            return True
        if item_name.startswith("."):
            return True
        return False

    def _walk_directory(self, current_path: Path, depth: int, prefix: str):
        """Recursively walks the directory to build the tree structure."""
        if depth >= self.max_depth:
            return

        try:
            items = list(current_path.iterdir())
        except PermissionError:
            self.tree_output.append(f"{prefix}├── [Permission Denied]")
            return

        filtered_items = [item for item in items if not self._is_ignored(item.name)]
        filtered_items.sort(key=lambda x: (not x.is_dir(), x.name.lower()))

        for i, item in enumerate(filtered_items):

            if self.file_count >= self.max_files:
                self.tree_output.append(f"{prefix}└── ... (limit reached)")
                return

            is_last_item = i == len(filtered_items) - 1
            tree_prefix = "└── " if is_last_item else "├── "
            self.tree_output.append(f"{prefix}{tree_prefix}{item.name}")
            self.file_count += 1

            if item.is_dir():
                child_prefix = (prefix + "    ") if is_last_item else (prefix + "│   ")
                self._walk_directory(item, depth + 1, child_prefix)

    def generate(self, start_path: str) -> str:
        """
        Generates the folder tree for the given path.
        """
        self.file_count = 0
        self.tree_output = []

        root_path = Path(start_path)
        if not root_path.is_dir():
            return f"Error: Path '{start_path}' is not a valid directory."
        self.tree_output.append(f"{root_path.name}/")
        self._walk_directory(root_path, 0, "")
        return "\n".join(self.tree_output)
