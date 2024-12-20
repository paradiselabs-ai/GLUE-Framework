import pytest
import sys
from pathlib import Path

# Add src directory to Python path
src_path = str(Path(__file__).parent.parent.parent / 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from glue.magnetic.field import MagneticField, MagneticResource, ResourceState
from glue.core.context import ContextAnalyzer, InteractionType

async def create_resources(field: MagneticField):
    """Create and add basic resources to field"""
    researcher = MagneticResource("researcher")
    writer = MagneticResource("writer")
    web_search = MagneticResource("web_search")
    file_handler = MagneticResource("file_handler")
    
    await field.add_resource(researcher)
    await field.add_resource(writer)
    await field.add_resource(web_search)
    await field.add_resource(file_handler)
    
    return researcher, writer, web_search, file_handler

@pytest.mark.asyncio
async def test_chat_interaction():
    """Test direct model-to-model communication"""
    async with MagneticField("test_field") as field:
        researcher, writer, _, _ = await create_resources(field)
        
        # Set up chat only
        await field.enable_chat(researcher, writer)
        
        # Verify chat state
        assert researcher._state == ResourceState.CHATTING
        assert writer._state == ResourceState.CHATTING
        assert researcher in writer._attracted_to
        assert writer in researcher._attracted_to

@pytest.mark.asyncio
async def test_research_flow():
    """Test research workflow with web search"""
    async with MagneticField("test_field") as field:
        researcher, writer, web_search, _ = await create_resources(field)
        
        # Set up research flow
        await field.attract(researcher, web_search)
        await field.enable_pull(writer, web_search)
        
        # Verify researcher can use web_search
        assert web_search in researcher._attracted_to
        assert researcher._state == ResourceState.SHARED
        
        # Verify writer can only pull from web_search
        assert web_search in writer._attracted_to
        assert writer._state == ResourceState.PULLING

@pytest.mark.asyncio
async def test_file_operations():
    """Test file handling workflow"""
    async with MagneticField("test_field") as field:
        _, writer, _, file_handler = await create_resources(field)
        
        # Set up file handling only
        await field.attract(writer, file_handler)
        
        # Verify writer can use file_handler
        assert file_handler in writer._attracted_to
        assert writer._state == ResourceState.SHARED

@pytest.mark.asyncio
async def test_context_awareness():
    """Test interaction with context analyzer"""
    async with MagneticField("test_field") as field:
        researcher, writer, web_search, file_handler = await create_resources(field)
        analyzer = ContextAnalyzer()
        
        # Test research request
        context = analyzer.analyze("research the history of paperclips")
        await field.update_context(context)
        
        # Set up relationships based on context
        await field.attract(researcher, web_search)
        
        assert context.interaction_type == InteractionType.RESEARCH
        assert "web_search" in context.tools_required
        assert web_search in researcher._attracted_to
        
        # Test file operation
        context = analyzer.analyze("save the research to a file")
        await field.update_context(context)
        
        # Set up new relationships
        await field.attract(writer, file_handler)
        
        assert "file_handler" in context.tools_required
        assert file_handler in writer._attracted_to

@pytest.mark.asyncio
async def test_workflow_transitions():
    """Test transitions between different interactions"""
    async with MagneticField("test_field") as field:
        researcher, writer, web_search, file_handler = await create_resources(field)
        
        # Start with research
        await field.attract(researcher, web_search)
        await field.enable_pull(writer, web_search)
        
        assert web_search in researcher._attracted_to
        assert writer._state == ResourceState.PULLING
        
        # Clear previous relationships
        await field.repel(writer, web_search)
        
        # Transition to file operation
        await field.attract(writer, file_handler)
        
        assert file_handler in writer._attracted_to
        assert writer._state == ResourceState.SHARED
        
        # Clear previous relationships
        await field.repel(researcher, web_search)
        await field.repel(writer, file_handler)
        
        # Transition to chat
        await field.enable_chat(researcher, writer)
        
        assert researcher._state == ResourceState.CHATTING
        assert writer._state == ResourceState.CHATTING
