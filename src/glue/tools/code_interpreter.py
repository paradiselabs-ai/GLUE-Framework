# src/glue/tools/code_interpreter.py

# ==================== Imports ====================
from typing import Any, Dict, List, Optional
import subprocess
import tempfile
import os
import asyncio
from pathlib import Path
from .base import ToolConfig, ToolPermission
from .magnetic import MagneticTool
from ..magnetic.field import AttractionStrength, ResourceState

# ==================== Constants ====================
SUPPORTED_LANGUAGES = {
    "python": {
        "extension": "py",
        "command": "python",
        "timeout": 30
    },
    "javascript": {
        "extension": "js",
        "command": "node",
        "timeout": 30
    }
}

# ==================== Code Interpreter Tool ====================
class CodeInterpreterTool(MagneticTool):
    """Tool for executing code in various languages with magnetic capabilities"""
    
    def __init__(
        self,
        name: str = "code_interpreter",
        description: str = "Executes code in a sandboxed environment",
        supported_languages: Optional[List[str]] = None,
        sandbox_dir: Optional[str] = None,
        strength: AttractionStrength = AttractionStrength.MEDIUM
    ):
        super().__init__(
            name=name,
            description=description,
            strength=strength,
            config=ToolConfig(
                required_permissions=[
                    ToolPermission.EXECUTE,
                    ToolPermission.FILE_SYSTEM,
                    ToolPermission.MAGNETIC
                ],
                timeout=60.0,
                cache_results=False
            )
        )
        self.supported_languages = (
            {lang: SUPPORTED_LANGUAGES[lang] 
             for lang in supported_languages if lang in SUPPORTED_LANGUAGES}
            if supported_languages
            else SUPPORTED_LANGUAGES
        )
        self.sandbox_dir = sandbox_dir or tempfile.mkdtemp(prefix="glue_sandbox_")
        self._temp_files: List[str] = []

    async def initialize(self) -> None:
        """Initialize sandbox environment"""
        os.makedirs(self.sandbox_dir, exist_ok=True)
        await super().initialize()

    async def cleanup(self) -> None:
        """Cleanup temporary files and magnetic resources"""
        # Clean up temp files first
        for file_path in self._temp_files[:]:  # Create a copy of the list
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                self._temp_files.remove(file_path)
            except OSError:
                pass
        
        # Clean up sandbox directory if empty
        try:
            if os.path.exists(self.sandbox_dir) and not os.listdir(self.sandbox_dir):
                os.rmdir(self.sandbox_dir)
        except OSError:
            pass
            
        # Clean up magnetic resources
        await super().cleanup()

    async def execute(
        self,
        code: str,
        language: str,
        timeout: Optional[float] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute code in specified language with state awareness
        
        Args:
            code: Source code to execute
            language: Programming language
            timeout: Execution timeout in seconds
            **kwargs: Additional execution parameters
            
        Returns:
            Dict containing execution results and metadata
            
        Raises:
            ResourceLockedException: If tool is locked
            ResourceStateException: If tool is not in a field
            ValueError: For unsupported languages
            TimeoutError: When execution exceeds timeout
            RuntimeError: For other execution failures
        """
        # State checks handled by parent
        await super().execute(code=code, language=language, timeout=timeout, **kwargs)

        if language not in self.supported_languages:
            raise ValueError(
                f"Unsupported language: {language}. "
                f"Supported: {list(self.supported_languages.keys())}"
            )

        lang_config = self.supported_languages[language]
        timeout = timeout or lang_config["timeout"]

        # Create temporary file
        temp_file = None
        try:
            # Create sandbox directory if needed
            os.makedirs(self.sandbox_dir, exist_ok=True)
            
            # Create and write temp file
            temp_file = tempfile.NamedTemporaryFile(
                suffix=f".{lang_config['extension']}",
                dir=self.sandbox_dir,
                mode='w',
                delete=False
            )
            temp_file.write(code)
            temp_file.close()
            self._temp_files.append(temp_file.name)

            # Execute code
            process = await asyncio.create_subprocess_exec(
                lang_config["command"],
                temp_file.name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                if process:
                    process.kill()
                    try:
                        await process.wait()
                    except:
                        pass
                raise TimeoutError(
                    f"Code execution timed out after {timeout} seconds"
                )

            # Update state based on attractions
            if self._attracted_to:
                self._state = ResourceState.SHARED

            return {
                "success": process.returncode == 0,
                "output": stdout.decode().strip(),
                "error": stderr.decode().strip(),
                "exit_code": process.returncode,
                "language": language,
                "execution_time": None  # TODO: Add execution time tracking
            }

        except TimeoutError:
            raise  # Re-raise timeout errors directly
        except Exception as e:
            raise RuntimeError(f"Code execution failed: {str(e)}")

    def __str__(self) -> str:
        langs = ", ".join(self.supported_languages.keys())
        return (
            f"{self.name}: {self.description} "
            f"(Magnetic Code Interpreter, Languages: {langs}, "
            f"Strength: {self.strength.name}, State: {self._state.name})"
        )
