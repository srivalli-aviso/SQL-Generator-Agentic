"""
Script to download and test the gte-large-en-v1.5 embedding model.

This script downloads the model and verifies it works correctly.
"""

import sys
import os

def download_and_test_model():
    """
    Download and test the gte-large-en-v1.5 embedding model.
    
    This function:
    1. Downloads the model using sentence-transformers
    2. Tests embedding generation
    3. Verifies the embedding dimensions
    4. Tests batch processing
    """
    print("=" * 80)
    print("Downloading and Testing gte-large-en-v1.5 Model")
    print("=" * 80)
    
    try:
        from sentence_transformers import SentenceTransformer  # type: ignore
        print("✓ sentence-transformers is installed")
    except ImportError:
        print("✗ Error: sentence-transformers is not installed")
        print("Install it with: pip install sentence-transformers")
        return False
    
    # Model name - try both possible names
    model_names = [
        "gte-large-en-v1.5",
        "Alibaba-NLP/gte-large-en-v1.5"
    ]
    
    model = None
    model_name_used = None
    
    for model_name in model_names:
        try:
            print(f"\nTrying to load model: {model_name}")
            print("(This will download the model if not already cached)")
            print("Model size: ~1.3GB - this may take a few minutes...")
            
            # Try with trust_remote_code for Alibaba models
            if "Alibaba" in model_name or "gte" in model_name.lower():
                print("Using trust_remote_code=True (required for this model)")
                model = SentenceTransformer(model_name, trust_remote_code=True)
            else:
                model = SentenceTransformer(model_name)
            
            model_name_used = model_name
            print(f"✓ Successfully loaded model: {model_name}")
            break
        except Exception as e:
            print(f"✗ Failed to load {model_name}: {str(e)}")
            # Try with trust_remote_code if not already tried
            if "trust_remote_code" not in str(e).lower() and ("Alibaba" in model_name or "gte" in model_name.lower()):
                try:
                    print("Retrying with trust_remote_code=True...")
                    model = SentenceTransformer(model_name, trust_remote_code=True)
                    model_name_used = model_name
                    print(f"✓ Successfully loaded model: {model_name}")
                    break
                except Exception as e2:
                    print(f"✗ Still failed: {str(e2)}")
            
            if model_name != model_names[-1]:
                print(f"Trying alternative model name...")
            else:
                print("\nBoth model names failed. Checking available models...")
                return False
    
    if model is None:
        print("✗ Could not load the model")
        return False
    
    # Get model information
    embedding_dim = model.get_sentence_embedding_dimension()
    print(f"\n" + "=" * 80)
    print("Model Information:")
    print("=" * 80)
    print(f"Model Name: {model_name_used}")
    print(f"Embedding Dimension: {embedding_dim}")
    print(f"Expected Dimension: 1024")
    
    if embedding_dim == 1024:
        print("✓ Embedding dimension matches expected value (1024)")
    else:
        print(f"⚠ Warning: Embedding dimension is {embedding_dim}, expected 1024")
    
    # Test embedding generation
    print("\n" + "=" * 80)
    print("Testing Embedding Generation")
    print("=" * 80)
    
    test_texts = [
        "revenue by region and segment",
        "Show me quarterly financial metrics",
        "database schema table column"
    ]
    
    try:
        # Single text embedding
        print("\n1. Testing single text embedding...")
        embedding = model.encode(test_texts[0], normalize_embeddings=True)
        print(f"   ✓ Generated embedding with dimension: {len(embedding)}")
        
        # Batch embedding
        print("\n2. Testing batch embedding...")
        embeddings = model.encode(test_texts, normalize_embeddings=True)
        print(f"   ✓ Generated {len(embeddings)} embeddings")
        print(f"   ✓ Each embedding has dimension: {len(embeddings[0])}")
        
        # Test similarity
        print("\n3. Testing similarity calculation...")
        from numpy import dot
        from numpy.linalg import norm
        
        similarity = dot(embeddings[0], embeddings[1]) / (norm(embeddings[0]) * norm(embeddings[1]))
        print(f"   ✓ Similarity between texts: {similarity:.4f}")
        
        print("\n" + "=" * 80)
        print("✓ All tests passed! Model is ready to use.")
        print("=" * 80)
        print(f"\nTo use this model, update your config:")
        print(f'  embedding_model: str = "{model_name_used}"')
        print("\nThe model is now cached and will load faster on subsequent uses.")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = download_and_test_model()
    sys.exit(0 if success else 1)

