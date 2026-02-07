from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
import pickle
import os

class RegulatoryRetriever:
    """
    Vector-based retriever for regulatory documents using sentence embeddings
    and FAISS index for efficient similarity search.
    """
    
    def __init__(self, documents, model_name="all-MiniLM-L6-v2", cache_file="embeddings_cache.pkl"):
        """
        Initialize the retriever with documents and build the vector index.
        
        Args:
            documents (list): List of dictionaries with 'source' and 'text' keys
            model_name (str): Name of the sentence transformer model
            cache_file (str): File to cache embeddings for faster loading
        """
        self.documents = documents
        self.model_name = model_name
        self.cache_file = cache_file
        
        # Load or create embeddings
        if os.path.exists(cache_file):
            print(f"Loading cached embeddings from {cache_file}")
            with open(cache_file, 'rb') as f:
                cached_data = pickle.load(f)
                self.texts = cached_data['texts']
                self.sources = cached_data['sources']
                self.embeddings = cached_data['embeddings']
        else:
            print("Creating new embeddings...")
            self.model = SentenceTransformer(model_name)
            self.texts = [doc["text"] for doc in documents]
            self.sources = [doc["source"] for doc in documents]
            
            print(f"Encoding {len(self.texts)} documents...")
            self.embeddings = self.model.encode(self.texts, show_progress_bar=True)
            
            # Cache embeddings
            with open(cache_file, 'wb') as f:
                pickle.dump({
                    'texts': self.texts,
                    'sources': self.sources,
                    'embeddings': self.embeddings
                }, f)
            print(f"Embeddings cached to {cache_file}")
        
        # Build FAISS index
        self._build_index()
    
    def _build_index(self):
        """Build the FAISS index for similarity search."""
        dim = self.embeddings.shape[1]
        self.index = faiss.IndexFlatL2(dim)
        
        # Add embeddings to index
        embeddings_array = np.array(self.embeddings).astype('float32')
        self.index.add(embeddings_array)
        
        print(f"Built FAISS index with {self.index.ntotal} vectors")
    
    def search(self, query, k=3):
        """
        Search for relevant documents given a query.
        
        Args:
            query (str): Search query
            k (int): Number of top results to return
            
        Returns:
            list: List of dictionaries with search results
        """
        if not hasattr(self, 'model'):
            self.model = SentenceTransformer(self.model_name)
        
        # Encode query
        q_emb = self.model.encode([query])
        q_emb = np.array(q_emb).astype('float32')
        
        # Search
        D, I = self.index.search(q_emb, k)
        
        results = []
        for idx, distance in zip(I[0], D[0]):
            if idx < len(self.documents):
                results.append({
                    "source": self.sources[idx],
                    "text": self.texts[idx][:1000],  # Limit text length for readability
                    "score": float(distance),
                    "full_text": self.texts[idx]
                })
        
        return results
    
    def get_document_by_source(self, source):
        """Get a specific document by its source filename."""
        for i, doc_source in enumerate(self.sources):
            if doc_source == source:
                return {
                    "source": doc_source,
                    "text": self.texts[i]
                }
        return None

if __name__ == "__main__":
    # Test the retriever
    from data_loader import load_regulatory_docs
    
    print("Loading documents...")
    docs = load_regulatory_docs()
    
    if docs:
        print(f"Initializing retriever with {len(docs)} documents...")
        retriever = RegulatoryRetriever(docs)
        
        # Test search
        test_query = "What are the components of CET1 capital?"
        results = retriever.search(test_query, k=2)
        
        print(f"\nSearch results for: '{test_query}'")
        for i, result in enumerate(results, 1):
            print(f"\n{i}. {result['source']} (score: {result['score']:.4f})")
            print(f"   {result['text'][:200]}...")
    else:
        print("No documents found. Please add regulatory documents to the reg_docs folder.")
