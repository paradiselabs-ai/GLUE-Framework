# src/glue/tools/file_handler.py

# ==================== Imports ====================
from typing import Any, Dict, List, Optional, Union
import os
import json
import yaml
import csv
from pathlib import Path
from .base import ToolConfig, ToolPermission
from .magnetic import MagneticTool
from ..magnetic.field import AttractionStrength, ResourceState

# ==================== Constants ====================
SUPPORTED_FORMATS = {
    ".txt": "text",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".csv": "csv"
}

# ==================== File Handler Tool ====================
class FileHandlerTool(MagneticTool):
    """Tool for handling file operations with various formats and magnetic capabilities"""
    
    def __init__(
        self,
        name: str = "file_handler",
        description: str = "Handles file operations with format support",
        base_path: Optional[str] = None,
        allowed_formats: Optional[List[str]] = None,
        strength: AttractionStrength = AttractionStrength.MEDIUM
    ):
        super().__init__(
            name=name,
            description=description,
            strength=strength,
            config=ToolConfig(
                required_permissions=[
                    ToolPermission.FILE_SYSTEM,
                    ToolPermission.READ,
                    ToolPermission.WRITE,
                    ToolPermission.MAGNETIC
                ],
                cache_results=False
            )
        )
        self.base_path = os.path.abspath(base_path or os.getcwd())
        self.allowed_formats = (
            {fmt: SUPPORTED_FORMATS[fmt] 
             for fmt in allowed_formats if fmt in SUPPORTED_FORMATS}
            if allowed_formats
            else SUPPORTED_FORMATS
        )

    def _validate_path(self, file_path: str) -> Path:
        """Validate and resolve file path"""
        # Convert to absolute path if relative
        if not os.path.isabs(file_path):
            file_path = os.path.join(self.base_path, file_path)
        
        # Resolve to absolute path, following symlinks
        abs_path = os.path.abspath(os.path.realpath(file_path))
        base_path = os.path.abspath(os.path.realpath(self.base_path))
        
        # Check if path is within base directory
        if not abs_path.startswith(base_path):
            raise ValueError(
                f"Access denied: {file_path} is outside base directory"
            )

        return Path(abs_path)

    def _get_format_handler(self, file_path: Path) -> str:
        """Get appropriate format handler for file"""
        suffix = file_path.suffix.lower()
        if suffix not in self.allowed_formats:
            raise ValueError(
                f"Unsupported format: {suffix}. "
                f"Supported: {list(self.allowed_formats.keys())}"
            )
        return self.allowed_formats[suffix]

    async def execute(
        self,
        operation: str,
        file_path: str,
        content: Any = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute file operation with state awareness
        
        Args:
            operation: Operation type (read/write/append/delete)
            file_path: Path to file
            content: Content for write/append operations
            **kwargs: Additional operation parameters
            
        Returns:
            Dict containing operation results
        
        Raises:
            ResourceLockedException: If tool is locked
            ResourceStateException: If tool is not in a field
            ValueError: For invalid operations or formats
            FileNotFoundError: When file doesn't exist for read/delete
            RuntimeError: For general operation failures
        """
        # State checks handled by parent
        await super().execute(
            operation=operation,
            file_path=file_path,
            content=content,
            **kwargs
        )

        path = self._validate_path(file_path)
        format_handler = self._get_format_handler(path)

        if operation not in ["read", "write", "append", "delete"]:
            raise ValueError(f"Unsupported operation: {operation}")

        try:
            result = None
            if operation == "read":
                result = await self._read_file(path, format_handler)
            elif operation == "write":
                result = await self._write_file(
                    path, content, format_handler, mode='w'
                )
            elif operation == "append":
                result = await self._write_file(
                    path, content, format_handler, mode='a'
                )
            elif operation == "delete":
                result = await self._delete_file(path)

            # Update state based on attractions
            if self._attracted_to:
                self._state = ResourceState.SHARED

            return result

        except (ValueError, FileNotFoundError) as e:
            # Re-raise these exceptions directly
            raise
        except Exception as e:
            raise RuntimeError(f"File operation failed: {str(e)}")

    async def _read_file(
        self,
        path: Path,
        format_handler: str
    ) -> Dict[str, Any]:
        """Read file content based on format"""
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        with open(path, 'r') as f:
            if format_handler == "text":
                content = f.read()
            elif format_handler == "json":
                content = json.load(f)
            elif format_handler == "yaml":
                content = yaml.safe_load(f)
            elif format_handler == "csv":
                content = list(csv.DictReader(f))

        return {
            "success": True,
            "operation": "read",
            "format": format_handler,
            "content": content,
            "path": str(path)
        }

    async def _write_file(
        self,
        path: Path,
        content: Any,
        format_handler: str,
        mode: str
    ) -> Dict[str, Any]:
        """Write content to file based on format"""
        os.makedirs(path.parent, exist_ok=True)

        if format_handler == "csv" and not isinstance(content, list):
            raise ValueError("CSV content must be a list of dictionaries")

        with open(path, mode) as f:
            if format_handler == "text":
                f.write(str(content))
            elif format_handler == "json":
                json.dump(content, f, indent=2)
            elif format_handler == "yaml":
                yaml.safe_dump(content, f)
            elif format_handler == "csv":
                writer = csv.DictWriter(f, fieldnames=content[0].keys())
                if mode == 'w':
                    writer.writeheader()
                writer.writerows(content)

        return {
            "success": True,
            "operation": mode == 'w' and "write" or "append",
            "format": format_handler,
            "path": str(path)
        }

    async def _delete_file(self, path: Path) -> Dict[str, Any]:
        """Delete file"""
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        os.remove(path)
        return {
            "success": True,
            "operation": "delete",
            "path": str(path)
        }

    def __str__(self) -> str:
        formats = ", ".join(self.allowed_formats.keys())
        return (
            f"{self.name}: {self.description} "
            f"(Magnetic File Handler, Formats: {formats}, "
            f"Strength: {self.strength.name}, State: {self._state.name})"
        )
