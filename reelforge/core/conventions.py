"""
ReelForge Tool Naming Convention
================================

All capability tools MUST follow this naming pattern:
    {type}_{id}

Where:
    - type: MUST be one of the known capability types (llm, tts, image, etc.)
    - id: Unique identifier for this specific capability
    
Parsing strategy (Fail Fast):
    - Match against known capability types only
    - If no match, return None (fail early to expose configuration errors)
    - No guessing or fallback - explicit is better than implicit

Examples:
    ✅ llm_call              → type: llm, id: call
    ✅ tts_edge              → type: tts, id: edge
    ✅ image_comfykit        → type: image, id: comfykit
    
    ❌ call_llm              → Wrong order
    ❌ llm-call              → Use underscore, not dash
    ❌ LLM_call              → Use lowercase
"""

from typing import Any, Optional

from pydantic import BaseModel, Field

# Known capability types
CAPABILITY_TYPES = {
    "llm",
    "tts",
    "image",
}


def parse_tool_name(tool_name: str) -> Optional[tuple[str, str]]:
    """
    Parse tool name into (type, id) - Fail Fast approach
    
    Only accepts tool names that match known capability types.
    Returns None for unknown types to fail early and expose configuration errors.
    
    Args:
        tool_name: Tool name following convention (e.g., "llm_qwen", "tts_edge")
    
    Returns:
        (type, id) tuple if matches known type, None otherwise
    
    Examples:
        >>> parse_tool_name("llm_call")
        ('llm', 'call')
        
        >>> parse_tool_name("tts_edge")
        ('tts', 'edge')
        
        >>> parse_tool_name("unknown_type_id")
        None  # Fail fast - unknown type
    """
    # Must contain at least one underscore
    if "_" not in tool_name:
        return None
    
    # Only match against known capability types (sorted by length, longest first)
    for cap_type in sorted(CAPABILITY_TYPES, key=len, reverse=True):
        # Match pattern: {known_type}_{id}
        if tool_name.startswith(cap_type + "_"):
            capability_id = tool_name[len(cap_type) + 1:]  # +1 for underscore
            if capability_id:  # Must have a non-empty id
                return cap_type, capability_id
    
    # No match found - return None to fail early
    return None


class CapabilityInfo(BaseModel):
    """
    Capability information
    
    Required: type and id (parsed from tool_name)
    Optional: everything else (from meta.reelforge)
    """

    # Required (parsed from tool_name)
    type: str = Field(description="Capability type (llm, tts, etc.)")
    id: str = Field(description="Unique identifier for this capability")
    
    # Optional (from meta.reelforge)
    display_name: Optional[str] = Field(
        default=None, description="Human-readable name for UI display"
    )
    description: Optional[str] = Field(default=None, description="Short description")
    is_default: bool = Field(default=False, description="Whether this is the default for this type")
    
    # Tool reference
    tool_name: str = Field(description="Original tool name")
    
    # Tool reference
    tool: Optional[Any] = Field(default=None, description="Tool object reference", exclude=True)
    
    @property
    def display_label(self) -> str:
        """Get display label for UI"""
        if self.display_name:
            return self.display_name
        # Auto-generate from id: "my_custom_v2" → "My Custom V2"
        return self.id.replace("_", " ").title()
    
    @property
    def full_id(self) -> str:
        """Get full identifier: type/id"""
        return f"{self.type}/{self.id}"

