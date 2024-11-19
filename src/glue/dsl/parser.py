# src/glue/dsl/parser.py

"""GLUE DSL Parser"""

import re
from typing import Dict, List, Any, Optional, Tuple, ForwardRef
from dataclasses import dataclass, field
from .keywords import (
    get_keyword_type,
    PROVIDER_KEYWORDS,
    ROLE_KEYWORDS,
    CONFIG_KEYWORDS,
    OPERATION_KEYWORDS,
    APP_KEYWORDS,
    CBM_KEYWORDS
)

@dataclass
class ModelConfig:
    """Model Configuration"""
    provider: str
    api_key: Optional[str]
    config: Dict[str, Any]
    chain: Optional[Dict[str, Any]]
    role: Optional[str]

@dataclass
class ToolConfig:
    """Tool Configuration"""
    path: Optional[str]
    provider: Optional[str]
    api_key: Optional[str]
    config: Dict[str, Any]

@dataclass
class CBMConfig:
    """CBM Configuration"""
    models: List[str]
    double_side_tape: List[Tuple[str, str]]
    glue: Dict[str, str]
    magnets: Dict[str, List[str]]

@dataclass
class GlueApp:
    """GLUE Application Configuration"""
    name: str
    tools: List[str]
    model: str
    config: Dict[str, Any]
    # Store parsed models and tools
    models: Dict[str, ModelConfig] = field(default_factory=dict)
    tool_configs: Dict[str, ToolConfig] = field(default_factory=dict)
    cbm_config: Optional[CBMConfig] = None

class GlueParser:
    """Parser for GLUE DSL"""
    
    def __init__(self):
        self.app: Optional[GlueApp] = None
        self.models: Dict[str, ModelConfig] = {}
        self.tools: Dict[str, ToolConfig] = {}
        self.cbm_config: Optional[CBMConfig] = None
    
    def parse(self, content: str) -> GlueApp:
        """Parse GLUE DSL content"""
        # Remove comments
        content = re.sub(r'//.*$', '', content, flags=re.MULTILINE)
        print(f"\nCleaned content:\n{content}")
        
        # Extract blocks
        blocks = self._extract_blocks(content)
        print(f"\nExtracted blocks:\n{blocks}")
        
        # First pass: Find and parse app block
        for block_type, block_content in blocks:
            # Check for app block
            keyword_type, _ = get_keyword_type(block_type)
            if keyword_type == 'app':
                print(f"\nParsing app block: {block_type}")
                self._parse_app(block_content)
                break
        
        # Second pass: Parse remaining blocks
        for block_type, block_content in blocks:
            # Skip app blocks (already parsed)
            keyword_type, _ = get_keyword_type(block_type)
            if keyword_type == 'app':
                continue
            
            print(f"\nParsing block: {block_type}\nContent: {block_content}")
            
            if block_type == self.app.model:
                # This is a CBM block
                self._parse_cbm_block(block_type, block_content)
            elif ':' in block_type:
                self._parse_tool_path(block_type, block_content)
            elif '_' in block_type and any(block_type.endswith(suffix) for suffix in ROLE_KEYWORDS):
                model_name = block_type.split('_')[0]
                self._parse_role(model_name, block_content)
            else:
                # Check if this is a tool block
                block_type = block_type.strip()
                if block_type in (self.app.tools if self.app else []):
                    self._parse_tool_config(block_type, block_content)
                else:
                    self._parse_model(block_type, block_content)
        
        # Store parsed models and tools in app
        if self.app:
            self.app.models = self.models
            self.app.tool_configs = self.tools
            self.app.cbm_config = self.cbm_config
            
            # Debug output
            print("\nParsed tool configs:")
            for name, config in self.tools.items():
                print(f"{name}: {config}")
        
        return self.app
    
    def _parse_cbm_block(self, name: str, content: str):
        """Parse CBM block"""
        print(f"\nParsing CBM block: {name}")
        
        # Extract models
        models_match = re.search(r'models\s*=\s*([^{\n]+)', content)
        models = []
        if models_match:
            models = [m.strip() for m in models_match.group(1).split(',')]
        
        # Extract double_side_tape chains
        double_side_tape = []
        chain_match = re.search(r'double_side_tape\s*=\s*{([^}]+)}', content)
        if chain_match:
            chain_content = chain_match.group(1).strip()
            for line in chain_content.split('\n'):
                line = line.strip()
                if '>>' in line:
                    parts = [p.strip() for p in line.split('>>')]
                    for i in range(len(parts)-1):
                        double_side_tape.append((parts[i], parts[i+1]))
        
        # Extract glue bindings
        glue = {}
        glue_match = re.search(r'glue\s*{([^}]+)}', content)
        if glue_match:
            glue_content = glue_match.group(1).strip()
            for line in glue_content.split('\n'):
                line = line.strip()
                if ':' in line:
                    tool, model = [p.strip() for p in line.split(':')]
                    glue[tool] = model
        
        # Extract magnet bindings
        magnets = {}
        magnets_match = re.search(r'magnets\s*{([^}]+)}', content)
        if magnets_match:
            magnets_content = magnets_match.group(1).strip()
            for line in magnets_content.split('\n'):
                line = line.strip()
                if ':' in line:
                    tool, models_str = [p.strip() for p in line.split(':')]
                    # Extract models from array syntax [model1, model2]
                    models_list = re.findall(r'\[(.*?)\]', models_str)
                    if models_list:
                        magnets[tool] = [m.strip() for m in models_list[0].split(',')]
        
        self.cbm_config = CBMConfig(
            models=models,
            double_side_tape=double_side_tape,
            glue=glue,
            magnets=magnets
        )
    
    def _extract_blocks(self, content: str) -> List[Tuple[str, str]]:
        """Extract blocks from content"""
        blocks = []
        
        # Match block patterns
        def find_matching_brace(s: str, start: int) -> int:
            """Find matching closing brace"""
            count = 1
            i = start
            while count > 0 and i < len(s):
                if s[i] == '{':
                    count += 1
                elif s[i] == '}':
                    count -= 1
                i += 1
            return i - 1 if count == 0 else -1
        
        # Find blocks with braces
        i = 0
        while i < len(content):
            # Find block start
            match = re.search(r'(\w+(?:\s+\w+)?)\s*{', content[i:])
            if not match:
                break
                
            block_type = match.group(1)
            block_start = i + match.end()
            
            # Find matching closing brace
            block_end = find_matching_brace(content, block_start)
            if block_end == -1:
                break
                
            # Extract block content
            block_content = content[block_start:block_end].strip()
            blocks.append((block_type, block_content))
            
            i = block_end + 1
        
        # Find tool definitions
        for match in re.finditer(r'(\w+(?:_\w+)?)\s*:\s*"([^"]+)"', content):
            tool_name = match.group(1)
            tool_path = match.group(2)
            blocks.append((f"{tool_name}:", tool_path))
        
        # Find role definitions
        for match in re.finditer(r'(\w+(?:_role|_system|_prompt|_instruction))\s*=\s*"([^"]+)"', content):
            role_name = match.group(1)
            role_content = match.group(2)
            blocks.append((role_name, role_content))
        
        return blocks
    
    def _parse_app(self, content: str):
        """Parse app block"""
        print(f"\nParsing app block:\n{content}")
        
        # Extract app name
        name_match = re.search(r'(?:name|app_name|title)\s*=\s*"([^"]+)"', content)
        name = name_match.group(1) if name_match else "glue_app"
        
        # Extract tools
        tools_match = re.search(r'(?:tools|components)\s*=\s*([^,\n]+)', content)
        tools = []
        if tools_match:
            tools = [t.strip() for t in tools_match.group(1).split(',')]
        
        # Extract model
        model_match = re.search(r'(?:model|agent)\s*=\s*(\w+)', content)
        model = model_match.group(1) if model_match else None
        
        self.app = GlueApp(
            name=name,
            tools=tools,
            model=model,
            config={},
            models={},
            tool_configs={}
        )
    
    def _parse_model(self, name: str, content: str):
        """Parse model block"""
        print(f"\nParsing model {name}:\n{content}")
        
        provider = None
        api_key = None
        config = {}
        chain = None
        
        # Parse each line
        for line in content.split('\n'):
            line = line.strip()
            if not line:
                continue
                
            # Check for provider keywords
            keyword_type, normalized = get_keyword_type(line)
            
            if keyword_type == 'provider':
                provider = normalized
            elif keyword_type == 'config' and normalized == 'api_key':
                api_key = "env:OPENROUTER_API_KEY"
            elif line.startswith('os.'):
                api_key = f"env:{line[3:].upper()}"
            else:
                # Check for model settings
                setting_match = re.match(r'(\w+)\s*=\s*(?:"([^"]+)"|([^"\s]+))', line)
                if setting_match:
                    key = setting_match.group(1)
                    value = setting_match.group(2) or setting_match.group(3)
                    if key != 'double_side_tape':
                        config[key] = value
        
        # Check for chain
        chain_match = re.search(r'(?:double_side_tape|chain|sequence)\s*=\s*{\s*([^}]+)\s*}', content)
        print(f"\nChain match: {chain_match}")
        
        if chain_match:
            chain_content = chain_match.group(1).strip()
            print(f"\nChain content: {chain_content}")
            tools = [t.strip() for t in chain_content.split('>>')]
            chain = {"tools": tools}
        
        # Create or update model config
        if name not in self.models:
            self.models[name] = ModelConfig(
                provider=provider,
                api_key=api_key,
                config=config,
                chain=chain,
                role=None
            )
        else:
            model = self.models[name]
            if provider:
                model.provider = provider
            if api_key:
                model.api_key = api_key
            if chain:
                model.chain = chain
            model.config.update(config)
    
    def _parse_tool_path(self, name: str, content: str):
        """Parse tool path definition"""
        name = name.rstrip(':')
        if name not in self.tools:
            self.tools[name] = ToolConfig(
                path=content.strip(),
                provider=None,
                api_key=None,
                config={}
            )
        else:
            self.tools[name].path = content.strip()
    
    def _parse_tool_config(self, name: str, content: str):
        """Parse tool configuration block"""
        print(f"\nParsing tool config {name}:\n{content}")
        
        provider = None
        api_key = None
        config = {}
        
        # Parse each line
        for line in content.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            # First non-empty line is the provider
            if provider is None:
                provider = line
                continue
            
            # Check for environment variables
            if line.startswith('os.'):
                api_key = f"env:{line[3:].upper()}"
            else:
                # Check for tool settings
                setting_match = re.match(r'(\w+)\s*=\s*(?:"([^"]+)"|([^"\s]+))', line)
                if setting_match:
                    key = setting_match.group(1)
                    value = setting_match.group(2) or setting_match.group(3)
                    config[key] = value
        
        # Create or update tool config
        if name not in self.tools:
            self.tools[name] = ToolConfig(
                path=None,
                provider=provider,
                api_key=api_key,
                config=config
            )
        else:
            tool = self.tools[name]
            if provider:
                tool.provider = provider
            if api_key:
                tool.api_key = api_key
            tool.config.update(config)
        
        print(f"\nParsed tool config for {name}:")
        print(f"Provider: {provider}")
        print(f"API Key: {api_key}")
        print(f"Config: {config}")
    
    def _parse_role(self, name: str, content: str):
        """Parse role block"""
        if name not in self.models:
            # Create model if it doesn't exist
            self.models[name] = ModelConfig(
                provider=None,
                api_key=None,
                config={},
                chain=None,
                role=content
            )
        else:
            self.models[name].role = content

def parse_glue_file(path: str) -> GlueApp:
    """Parse GLUE file"""
    with open(path) as f:
        content = f.read()
    
    parser = GlueParser()
    return parser.parse(content)
