"""
ReelForge CLI
"""

import asyncio

from loguru import logger

from reelforge.app import app


async def test_llm():
    """Test LLM capability"""
    # Initialize app
    await app.initialize()
    
    # Test prompt
    prompt = "Explain the concept of atomic habits in 3 sentences."
    
    logger.info(f"\n📝 Test Prompt: {prompt}\n")
    
    # Call LLM
    result = await app.router.call("llm", prompt=prompt)
    
    logger.info(f"\n✨ Result:\n{result}\n")


def main():
    """Main CLI entry point"""
    logger.info("🚀 ReelForge CLI\n")
    
    # Run test
    asyncio.run(test_llm())


if __name__ == "__main__":
    main()

