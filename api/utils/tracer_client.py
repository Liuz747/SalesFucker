"""
Langfuse integration
"""

from typing import Dict, Any, Optional
from langfuse import Langfuse

from config import mas_config


def trace_conversation(input_data: Dict[str, Any], output_data: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None):
    """
    Trace a conversation
    
    Args:
        input_data: Input data to trace
        output_data: Output data to trace  
        metadata: Optional metadata
    """
    client = Langfuse(
        secret_key=mas_config.LANGFUSE_SECRET_KEY,
        public_key=mas_config.LANGFUSE_PUBLIC_KEY,
        host=mas_config.LANGFUSE_HOST
    )
    
    try:
        client.trace(
            name="conversation",
            input=input_data,
            output=output_data,
            metadata=metadata or {}
        )
        client.flush()
    except Exception as e:
        print(f"Langfuse trace failed: {e}")