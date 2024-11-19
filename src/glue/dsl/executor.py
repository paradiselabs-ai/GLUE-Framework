# src/glue/dsl/executor.py

"""GLUE DSL Executor"""

import os
import asyncio
from typing import Any, Dict
from .parser import GlueApp, ModelConfig, ToolConfig, CBMConfig
from ..adhesive import (
    workspace, double_side_tape,
    tool as create_tool
)
from ..providers import (
    OpenRouterProvider
)
from ..magnetic.field import MagneticField
from ..core.cbm import CBM

class GlueExecutor:
    """Executor for GLUE Applications"""
    
    def __init__(self, app: GlueApp):
        self.app = app
        self.tools = {}
        self.models = {}
        self.cbm = None
        self._setup_environment()
    
    def _setup_environment(self):
        """Setup environment from .env file"""
        # Load environment variables if not already set
        if not os.getenv("OPENROUTER_API_KEY"):
            from dotenv import load_dotenv
            load_dotenv()
    
    async def _setup_tools(self, field: MagneticField):
        """Setup tools"""
        print("\nSetting up tools...")
        print(f"Available tools: {self.app.tools}")
        print(f"Tool configs: {self.app.tool_configs}")
        
        # Create tools with appropriate configuration
        for tool_name in self.app.tools:
            print(f"\nSetting up tool: {tool_name}")
            
            # Get tool config from GLUE file
            tool_config = self.app.tool_configs.get(tool_name)
            if not tool_config:
                print(f"No config found for tool: {tool_name}")
                continue
            
            print(f"Tool config: {tool_config}")
            
            # Get API key from environment if specified
            api_key = None
            if tool_config.api_key and tool_config.api_key.startswith("env:"):
                env_var = tool_config.api_key.replace("env:", "")
                api_key = os.getenv(env_var)
                if not api_key:
                    raise ValueError(
                        f"No API key found in environment variable {env_var} "
                        f"for tool {tool_name}"
                    )
                print(f"Using API key from {env_var}")
            
            try:
                # Create tool with config
                print(f"Creating tool with provider: {tool_config.provider}")
                tool = create_tool(
                    tool_name,
                    api_key=api_key,
                    provider=tool_config.provider,
                    **tool_config.config
                )
                
                # Add tool to field
                print("Adding tool to field")
                await field.add_resource(tool)
                
                self.tools[tool_name] = tool
                print(f"Tool {tool_name} setup complete")
            except Exception as e:
                print(f"Error setting up tool {tool_name}: {str(e)}")
                raise
    
    async def _setup_models(self):
        """Setup models"""
        print("\nSetting up models...")
        print(f"Available models: {self.app.models.keys()}")
        
        for model_name, config in self.app.models.items():
            print(f"\nSetting up model: {model_name}")
            print(f"Model config: {config}")
            
            if config.provider == "openrouter":
                api_key = os.getenv(config.api_key.replace("env:", ""))
                
                # Extract model configuration
                model_settings = {
                    "api_key": api_key,
                    "system_prompt": config.role,
                }
                
                # Add optional configuration
                if "model" in config.config:
                    model_settings["model"] = config.config["model"]
                if "temperature" in config.config:
                    model_settings["temperature"] = float(config.config["temperature"])
                if "max_tokens" in config.config:
                    model_settings["max_tokens"] = int(config.config["max_tokens"])
                
                print(f"Creating model with settings: {model_settings}")
                self.models[model_name] = OpenRouterProvider(**model_settings)
                print(f"Model {model_name} setup complete")
    
    async def _setup_cbm(self, cbm_config: CBMConfig):
        """Setup CBM with models and bindings"""
        # Create CBM instance
        self.cbm = CBM(self.app.name)
        
        # Add models to CBM
        for model_name in cbm_config.models:
            model = self.models.get(model_name)
            if not model:
                raise ValueError(f"Model {model_name} not found")
            self.cbm.add_model(model)
        
        # Set up double-side tape bindings
        for model1, model2 in cbm_config.double_side_tape:
            self.cbm.bind_models(model1, model2, binding_type='double_side_tape')
        
        # Set up permanent tool bindings
        for tool_name, model_name in cbm_config.glue.items():
            tool = self.tools.get(tool_name)
            if not tool:
                raise ValueError(f"Tool {tool_name} not found")
            self.cbm.bind_models(model_name, tool_name, binding_type='glue')
        
        # Set up magnetic tool sharing
        for tool_name, model_names in cbm_config.magnets.items():
            tool = self.tools.get(tool_name)
            if not tool:
                raise ValueError(f"Tool {tool_name} not found")
            for model_name in model_names:
                model = self.models.get(model_name)
                if not model:
                    raise ValueError(f"Model {model_name} not found")
                self.cbm.bind_models(model_name, tool_name, binding_type='magnet')
    
    async def execute(self) -> Any:
        """Execute GLUE application"""
        # Setup models
        await self._setup_models()
        
        try:
            # Create magnetic field
            async with MagneticField(self.app.name) as field:
                # Setup tools in field
                await self._setup_tools(field)
                
                # Setup CBM if configured
                if self.app.cbm_config:
                    await self._setup_cbm(self.app.cbm_config)
                    model = self.cbm
                else:
                    # Get main model
                    model = self.models.get(self.app.model)
                    if not model:
                        raise ValueError(f"Model {self.app.model} not found")
                
                # Create workspace
                async with workspace(self.app.name) as ws:
                    # Interactive prompt loop
                    while True:
                        print("\nprompt:", flush=True)
                        user_input = await asyncio.get_event_loop().run_in_executor(None, input)
                        
                        if user_input.lower() in ['exit', 'quit']:
                            break
                        
                        # Process input through CBM or single model
                        print("\nthinking...", flush=True)
                        if self.cbm:
                            response = await self.cbm.process_input(user_input)
                        else:
                            response = await model.generate(user_input)
                        
                        # Execute chain if defined
                        if not self.cbm and self.app.models[self.app.model].chain:
                            print("\nexecuting chain...", flush=True)
                            result = response
                            for tool_name in self.app.models[self.app.model].chain["tools"]:
                                print(f"\nExecuting tool: {tool_name}")
                                tool = self.tools[tool_name]
                                # Let each tool handle its own input format
                                if hasattr(tool, 'prepare_input'):
                                    print("Preparing input...")
                                    result = await tool.prepare_input(result)
                                print(f"Executing with input: {result}")
                                result = await tool.execute(result)
                            
                            # Have model process result if needed
                            if isinstance(result, (list, dict)):
                                print("\nprocessing results...", flush=True)
                                result = await model.generate(
                                    f"Here are the results:\n\n{result}\n\n"
                                    "Please analyze and summarize these results."
                                )
                            
                            print(f"\nresult: {result}", flush=True)
                        else:
                            print(f"\nresponse: {response}", flush=True)
        finally:
            # Cleanup any remaining sessions
            for tool in self.tools.values():
                if hasattr(tool, 'cleanup'):
                    await tool.cleanup()

async def execute_glue_app(app: GlueApp) -> Any:
    """Execute GLUE application"""
    executor = GlueExecutor(app)
    return await executor.execute()
