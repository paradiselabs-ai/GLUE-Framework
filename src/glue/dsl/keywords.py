# src/glue/dsl/keywords.py

"""GLUE DSL Keyword Mappings"""

# Model Provider Keywords
PROVIDER_KEYWORDS = {
    # OpenRouter keywords
    'openrouter': 'openrouter',
    
    # Future providers...
    'anthropic_direct': 'anthropic',
    'groq': 'groq',
    'mistral': 'mistral',
    'llama': 'llama'
}

# Model Role Keywords
ROLE_KEYWORDS = {
    # Role types
    'role': 'role',
    'system': 'role',
    'prompt': 'role',
    'instruction': 'role',
    'behavior': 'role',
    'personality': 'role',
    
    # Common role suffixes
    '_role': 'role',
    '_system': 'role',
    '_prompt': 'role',
    '_instruction': 'role',
    '_behavior': 'role',
    '_personality': 'role'
}

# Configuration Keywords
CONFIG_KEYWORDS = {
    # API Configuration
    'api': 'api_key',
    'key': 'api_key',
    'token': 'api_key',
    'api_key': 'api_key',
    'os.api_key': 'api_key',
    'os.key': 'api_key',
    
    # Model Configuration
    'temperature': 'temperature',
    'temp': 'temperature',
    'top_p': 'top_p',
    'sampling': 'top_p',
    'max_tokens': 'max_tokens',
    'length': 'max_tokens',
    'limit': 'max_tokens',
    
    # Memory Configuration
    'memory': 'memory',
    'context': 'memory',
    'history': 'memory',
    'recall': 'memory',
    'remember': 'memory',
    
    # Chain Configuration
    'chain': 'chain',
    'pipeline': 'chain',
    'sequence': 'chain',
    'flow': 'chain',
    'process': 'chain',
}

# Operation Keywords
OPERATION_KEYWORDS = {
    # Chain Operations
    'double_side_tape': 'chain',
    'tape': 'chain',
    'glue': 'chain',
    'bind': 'chain',
    'connect': 'chain',
    'link': 'chain',
    
    # Flow Control
    'if': 'condition',
    'when': 'condition',
    'unless': 'negative_condition',
    'else': 'alternative',
    'then': 'sequence',
    
    # Loops
    'repeat': 'loop',
    'while': 'loop',
    'until': 'loop',
    'foreach': 'loop',
    'iterate': 'loop'
}

# Application Keywords
APP_KEYWORDS = {
    # App Definition
    'app': 'app',
    'application': 'app',
    'glue': 'app',
    'glue_app': 'app',
    'agent': 'app',
    
    # App Configuration
    'name': 'name',
    'title': 'name',
    'description': 'description',
    'about': 'description',
    'version': 'version',
    
    # App Components
    'tools': 'tools',
    'models': 'models',
    'agents': 'models',
    'components': 'tools'
}

# CBM Keywords
CBM_KEYWORDS = {
    # CBM Definition
    'cbm': 'cbm',
    'team': 'cbm',
    'group': 'cbm',
    'ensemble': 'cbm',
    
    # CBM Components
    'models': 'models',
    'bindings': 'bindings',
    'magnets': 'magnets',
    'tools': 'tools',
    
    # CBM Operations
    'double_side_tape': 'chain',
    'glue': 'permanent',
    'magnets': 'shared'
}

def get_keyword_type(keyword: str) -> tuple[str, str]:
    """Get the type and normalized value for a keyword"""
    keyword = keyword.lower()
    
    # Special cases for app blocks
    if keyword in ['glue app', 'application']:
        return 'app', 'app'
    
    # Check for CBM block
    if keyword == 'cbm':
        return 'cbm', 'cbm'
    
    # Check each keyword mapping
    if keyword in PROVIDER_KEYWORDS:
        return 'provider', PROVIDER_KEYWORDS[keyword]
    elif keyword in ROLE_KEYWORDS:
        return 'role', ROLE_KEYWORDS[keyword]
    elif keyword in CONFIG_KEYWORDS:
        return 'config', CONFIG_KEYWORDS[keyword]
    elif keyword in OPERATION_KEYWORDS:
        return 'operation', OPERATION_KEYWORDS[keyword]
    elif keyword in APP_KEYWORDS:
        return 'app', APP_KEYWORDS[keyword]
    elif keyword in CBM_KEYWORDS:
        return 'cbm', CBM_KEYWORDS[keyword]
    
    # Check for role suffix
    for suffix in ROLE_KEYWORDS:
        if keyword.endswith(suffix):
            return 'role', 'role'
    
    return 'unknown', keyword
