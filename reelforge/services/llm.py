"""
LLM (Large Language Model) Service
"""

from typing import Optional

from reelforge.services.base import BaseService


class LLMService(BaseService):
    """
    LLM (Large Language Model) service
    
    Provides unified access to various LLM providers (Qwen, OpenAI, DeepSeek, Ollama, etc.)
    
    Usage:
        # Direct call (recommended)
        answer = await reelforge.llm("Explain atomic habits")
        
        # With parameters
        answer = await reelforge.llm(
            prompt="Explain atomic habits in 3 sentences",
            temperature=0.7,
            max_tokens=2000
        )
        
        # Explicit call syntax
        answer = await reelforge.llm.call(prompt="Hello")
        
        # Check active LLM
        print(f"Using: {reelforge.llm.active}")
        
        # List available LLMs
        print(f"Available: {reelforge.llm.available}")
    """
    
    def __init__(self, router):
        super().__init__(router, "llm")
    
    async def __call__(
        self,
        prompt: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """
        Generate text using LLM
        
        Args:
            prompt: The prompt to generate from
            api_key: API key (optional, uses config if not provided)
            base_url: Base URL (optional, uses config if not provided)
            model: Model name (optional, uses config if not provided)
            temperature: Sampling temperature (0.0-2.0). Lower is more deterministic.
            max_tokens: Maximum tokens to generate
            **kwargs: Additional provider-specific parameters
        
        Returns:
            Generated text
        
        Examples:
            # Use config from config.yaml
            answer = await reelforge.llm("Explain atomic habits")
            
            # Override with custom parameters
            answer = await reelforge.llm(
                "Explain the concept of atomic habits in 3 sentences",
                api_key="sk-custom-key",
                base_url="https://api.custom.com/v1",
                model="custom-model",
                temperature=0.7,
                max_tokens=500
            )
        """
        params = {"prompt": prompt}
        
        # Add optional LLM parameters (will override config if provided)
        if api_key is not None:
            params["api_key"] = api_key
        if base_url is not None:
            params["base_url"] = base_url
        if model is not None:
            params["model"] = model
        
        if temperature is not None:
            params["temperature"] = temperature
        if max_tokens is not None:
            params["max_tokens"] = max_tokens
        
        params.update(kwargs)
        
        return await self._config_manager.call(self._capability_type, **params)

