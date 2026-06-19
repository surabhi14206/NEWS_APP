import ollama
import numpy as np
import sys

def get_embedding(text: str, model_name: str = "nomic-embed-text") -> np.ndarray:
    """
    Fetch embedding vector from local Ollama and return it.
    """
    response = ollama.embeddings(model=model_name, prompt=text)
    return np.array(response["embedding"], dtype=np.float32)

def cosine_similarity(v1: np.ndarray, v2: np.ndarray) -> float:
    """
    Calculate cosine similarity: (A . B) / (||A|| * ||B||)
    """
    dot_product = np.dot(v1, v2)
    norm_v1 = np.linalg.norm(v1)
    norm_v2 = np.linalg.norm(v2)
    if norm_v1 < 1e-8 or norm_v2 < 1e-8:
        return 0.0
    return float(dot_product / (norm_v1 * norm_v2))

def test_run():
    print("=" * 60)
    print("TESTING SENTENCE EMBEDDINGS AND SIMILARITY MEASUREMENT")
    print("=" * 60)
    
    # Define some news test sentences
    sentences = [
        # Pair A: Highly similar news headlines (same story, different wording)
        ("RBI hikes key repo rate by 25 basis points to control inflation", 
         "Central bank raises interest rates to curb rising prices in India"),
        
        # Pair B: Related topics but different stories
        ("India's retail inflation rises to 5.4% in May due to food price shock", 
         "Monsoon deficit threatens crop yields and agricultural growth"),
         
        # Pair C: Completely unrelated news topics
        ("Tech giant launches new AI chatbot with advanced reasoning capabilities", 
         "Indian government signs new trade agreement with European Union"),
         
        # Pair D: Same title vs slight modification
        ("Sensex plunges 800 points amid global market sell-off", 
         "Sensex slides 800 points on global cues")
    ]

    print("Using Ollama model: 'nomic-embed-text'")
    print("-" * 60)
    
    for i, (s1, s2) in enumerate(sentences):
        print(f"\n[Pair {i+1}]")
        print(f"  Sentence 1: \"{s1}\"")
        print(f"  Sentence 2: \"{s2}\"")
        
        try:
            # 1. Get embeddings
            v1 = get_embedding(s1)
            v2 = get_embedding(s2)
            
            # 2. Calculate raw dot product
            raw_dot = np.dot(v1, v2)
            
            # 3. Calculate cosine similarity
            cos_sim = cosine_similarity(v1, v2)
            
            # 4. Calculate dot product after L2 normalization
            v1_norm = v1 / np.linalg.norm(v1) if np.linalg.norm(v1) > 1e-8 else v1
            v2_norm = v2 / np.linalg.norm(v2) if np.linalg.norm(v2) > 1e-8 else v2
            norm_dot = np.dot(v1_norm, v2_norm)
            
            print(f"  - Vector dimensions: {len(v1)}")
            print(f"  - Raw Dot Product: {raw_dot:.4f}")
            print(f"  - Cosine Similarity: {cos_sim:.4f} ({cos_sim*100:.2f}%)")
            print(f"  - Normalized Dot Product: {norm_dot:.4f} (Matches cosine similarity: {abs(norm_dot - cos_sim) < 1e-6})")
        except Exception as e:
            print(f"  [ERROR] Failed to run embedding check: {e}")
            print("  Make sure Ollama is running and the model 'nomic-embed-text' has been pulled:")
            print("  Command to run: ollama pull nomic-embed-text")
            sys.exit(1)

    print("\n" + "=" * 60)
    print("SUMMARY & CONCLUSION FOR NEWS CLASSIFICATION / SIMILARITY")
    print("=" * 60)
    print("1. Yes, classifying sentences into vectors and comparing them works beautifully!")
    print("2. For news similarity, Cosine Similarity is highly recommended because it captures")
    print("   the direction (meaning) of the sentences rather than the magnitude (length of sentence).")
    print("3. By normalizing vectors to unit length (L2 norm), the Dot Product becomes mathematically")
    print("   identical to Cosine Similarity. This allows us to use np.dot directly, which is extremely fast.")
    print("4. This is already integrated in fetch_indian_economy_news.py to filter and score web search results.")
    print("=" * 60)

if __name__ == "__main__":
    test_run()
