import json
from typing import List, Dict, Any, Optional


def ensure_tool_calls(response) -> None:
    """
    Ensure response has tool_calls populated, either from structured calling or parsed from content.
    Modifies the response object in place.
    
    Args:
        response: The model response object that may need tool_calls populated
    """
    # If tool_calls already exists and is not empty, keep it
    if hasattr(response, 'tool_calls') and response.tool_calls:
        return
    
    # Try to parse tool calls from content
    if hasattr(response, 'content') and response.content:
        parsed_calls = parse_tool_calls_from_content(response.content)
        
        if parsed_calls:
            # Convert parsed calls to the expected tool_calls format
            tool_calls = []
            for i, call in enumerate(parsed_calls):
                tool_calls.append({
                    "id": f"call_{i}",  # Generate a simple ID
                    "name": call["name"],
                    "args": call["arguments"]
                })
            
            # Set tool_calls on the response
            response.tool_calls = tool_calls


def parse_tool_calls_from_content(content: str) -> List[Dict[str, Any]]:
    """
    Parse tool calls from model response content that contains JSON-formatted tool calls.
    
    Args:
        content: The response content that may contain JSON tool call structures
        
    Returns:
        List of tool call dictionaries with "name" and "arguments" keys.
        Returns empty list if no valid tool calls found.
    """
    if not content or not content.strip():
        return []
    
    tool_calls = []
    
    # Split content by lines and try to parse each line as JSON
    lines = content.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        try:
            parsed = json.loads(line)
            
            # Check if this looks like a tool call (has "name" and "arguments" keys)
            if isinstance(parsed, dict) and "name" in parsed and "arguments" in parsed:
                tool_calls.append({
                    "name": parsed["name"].replace("functions.", ""),
                    "arguments": parsed["arguments"]
                })
                
        except json.JSONDecodeError:
            # This line is not valid JSON, skip it
            continue
    
    return tool_calls


def extract_tool_names(content: str) -> List[str]:
    """
    Extract just the tool names from model response content.
    
    Args:
        content: The response content that may contain JSON tool call structures
        
    Returns:
        List of tool names that were called.
    """
    tool_calls = parse_tool_calls_from_content(content)
    return [tool_call["name"] for tool_call in tool_calls]
