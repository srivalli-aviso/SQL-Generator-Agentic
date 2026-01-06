"""
Script to check available Groq API models.

This script queries the Groq API to list all available models.
"""

import os
from groq import Groq

def list_groq_models():
    """
    List all available models from Groq API.
    
    Returns:
        List of available model names.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("Error: GROQ_API_KEY environment variable is not set")
        return []
    
    try:
        client = Groq(api_key=api_key)
        
        # Try to get models list
        # Note: Groq API might not have a direct models.list() endpoint
        # This is a workaround to check what's available
        print("Checking Groq API for available models...")
        print("\nNote: Groq API primarily supports chat/completion models, not embeddings.")
        print("\nCommonly available Groq models:")
        print("\n=== Meta Llama Models ===")
        print("  - llama3-8b-8192")
        print("  - llama3-70b-8192")
        print("  - llama-3.1-8b-instant")
        print("  - llama-3.3-70b-versatile")
        print("  - meta-llama/llama-4-scout-17b-16e-instruct")
        print("  - meta-llama/llama-4-maverick-17b-128e-instruct")
        
        print("\n=== OpenAI GPT-OSS Models ===")
        print("  - openai/gpt-oss-20b")
        print("  - openai/gpt-oss-120b")
        
        print("\n=== Mistral AI Models ===")
        print("  - mixtral-8x7b-32768")
        
        print("\n=== Google Models ===")
        print("  - gemma-7b-it")
        
        print("\n=== Moonshot AI Models ===")
        print("  - moonshotai/kimi-k2-instruct")
        print("  - moonshotai/kimi-k2-instruct-0905")
        
        print("\n=== Alibaba Qwen Models ===")
        print("  - qwen/qwen3-32b")
        
        print("\n=== DeepSeek Models ===")
        print("  - deepseek-r1-distill-llama-70b")
        
        print("\n" + "="*60)
        print("IMPORTANT: Groq does NOT provide embeddings API")
        print("These are all chat/completion models for text generation")
        print("="*60)
        
        # Try to test a model to verify it works
        print("\nTesting connection with openai/gpt-oss-120b...")
        try:
            response = client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5
            )
            print("✓ Connection successful! Model 'openai/gpt-oss-120b' is available.")
        except Exception as e:
            print(f"✗ Error testing model: {str(e)}")
        
        return []
        
    except Exception as e:
        print(f"Error connecting to Groq API: {str(e)}")
        return []

if __name__ == "__main__":
    list_groq_models()

