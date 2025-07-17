"""Vector store service for RAG system using FAISS."""

import os
import pickle
import logging
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import faiss
from src.services.ollama_embeddings import OllamaEmbeddingService
from src.services.document_processor import DocumentChunk
from config.settings import settings

logger = logging.getLogger(__name__)


class VectorStore:
    """FAISS-based vector store for document embeddings."""
    
    def __init__(self, embedding_model: str = None, vector_store_path: str = None):
        """Initialize vector store.
        
        Args:
            embedding_model: Name of the embedding model
            vector_store_path: Path to store vector index and metadata
        """
        self.embedding_model_name = embedding_model or settings.EMBEDDING_MODEL
        self.vector_store_path = vector_store_path or settings.VECTOR_STORE_PATH
        
        # Initialize Ollama embedding service
        logger.info(f"Loading embedding model: {self.embedding_model_name}")
        self.embedding_model = OllamaEmbeddingService(
            ollama_url=settings.OLLAMA_EMBEDDING_URL,
            model_name=self.embedding_model_name
        )
        self.embedding_dim = self.embedding_model.get_sentence_embedding_dimension()
        
        # Initialize FAISS index
        self.index = None
        self.document_metadata = []  # Store metadata for each document chunk
        self.chunk_id_to_index = {}  # Map chunk IDs to index positions
        
        # Create vector store directory
        os.makedirs(self.vector_store_path, exist_ok=True)
        
        # Load existing index if available
        self._load_index()
    
    def add_documents(self, chunks: List[DocumentChunk]) -> None:
        """Add document chunks to the vector store.
        
        Args:
            chunks: List of DocumentChunk objects to add
        """
        if not chunks:
            logger.warning("No chunks provided to add to vector store")
            return
        
        logger.info(f"Adding {len(chunks)} chunks to vector store")
        
        # Extract texts for embedding
        texts = [chunk.text for chunk in chunks]
        
        # Generate embeddings
        logger.info("Generating embeddings...")
        embeddings = self.embedding_model.encode(texts, show_progress_bar=True)
        
        # Initialize index if it doesn't exist
        if self.index is None:
            self.index = faiss.IndexFlatIP(self.embedding_dim)  # Inner product for cosine similarity
        
        # Normalize embeddings for cosine similarity
        faiss.normalize_L2(embeddings)
        
        # Add embeddings to index
        start_index = self.index.ntotal
        self.index.add(embeddings.astype(np.float32))
        
        # Store metadata
        for i, chunk in enumerate(chunks):
            index_position = start_index + i
            self.document_metadata.append({
                'chunk_id': chunk.chunk_id,
                'text': chunk.text,
                'metadata': chunk.metadata,
                'source_file': chunk.source_file,
                'page_number': chunk.page_number,
                'created_at': chunk.created_at
            })
            self.chunk_id_to_index[chunk.chunk_id] = index_position
        
        logger.info(f"Added {len(chunks)} chunks. Total chunks in store: {self.index.ntotal}")
        
        # Save updated index
        self._save_index()
    
    def search(self, query: str, k: int = 5, score_threshold: float = 0.0) -> List[Dict[str, Any]]:
        """Search for similar documents.
        
        Args:
            query: Search query text
            k: Number of results to return
            score_threshold: Minimum similarity score threshold
            
        Returns:
            List of search results with metadata and scores
        """
        if self.index is None or self.index.ntotal == 0:
            logger.warning("Vector store is empty")
            return []
        
        # Generate query embedding
        query_embedding = self.embedding_model.encode([query])
        faiss.normalize_L2(query_embedding)
        
        # Search
        scores, indices = self.index.search(query_embedding.astype(np.float32), k)
        
        # Format results
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:  # FAISS returns -1 for invalid indices
                continue
            
            if score < score_threshold:
                continue
            
            if idx < len(self.document_metadata):
                result = self.document_metadata[idx].copy()
                result['similarity_score'] = float(score)
                results.append(result)
        
        logger.info(f"Found {len(results)} results for query: {query[:50]}...")
        return results
    
    def get_chunk_by_id(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific chunk by its ID.
        
        Args:
            chunk_id: ID of the chunk to retrieve
            
        Returns:
            Chunk data or None if not found
        """
        if chunk_id in self.chunk_id_to_index:
            index_position = self.chunk_id_to_index[chunk_id]
            if index_position < len(self.document_metadata):
                return self.document_metadata[index_position]
        
        return None
    
    def remove_documents_by_source(self, source_file: str) -> int:
        """Remove all chunks from a specific source file.
        
        Args:
            source_file: Path to the source file
            
        Returns:
            Number of chunks removed
        """
        if self.index is None:
            return 0
        
        # Find indices to remove
        indices_to_remove = []
        for i, metadata in enumerate(self.document_metadata):
            if metadata['source_file'] == source_file:
                indices_to_remove.append(i)
        
        if not indices_to_remove:
            logger.info(f"No chunks found for source file: {source_file}")
            return 0
        
        # FAISS doesn't support removing individual vectors efficiently
        # We need to rebuild the index without the removed documents
        logger.info(f"Rebuilding index to remove {len(indices_to_remove)} chunks from {source_file}")
        
        # Collect remaining chunks
        remaining_chunks = []
        for i, metadata in enumerate(self.document_metadata):
            if i not in indices_to_remove:
                # Create a DocumentChunk object from metadata
                chunk = DocumentChunk(
                    text=metadata['text'],
                    metadata=metadata['metadata'],
                    chunk_id=metadata['chunk_id'],
                    source_file=metadata['source_file'],
                    page_number=metadata['page_number']
                )
                remaining_chunks.append(chunk)
        
        # Clear current index and metadata
        self.index = None
        self.document_metadata = []
        self.chunk_id_to_index = {}
        
        # Re-add remaining chunks
        if remaining_chunks:
            self.add_documents(remaining_chunks)
        
        logger.info(f"Removed {len(indices_to_remove)} chunks from {source_file}")
        return len(indices_to_remove)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector store.
        
        Returns:
            Dictionary with store statistics
        """
        if self.index is None:
            return {
                'total_chunks': 0,
                'embedding_dimension': self.embedding_dim,
                'model_name': self.embedding_model_name,
                'source_files': []
            }
        
        # Count chunks by source file
        source_files = {}
        for metadata in self.document_metadata:
            source = metadata['source_file']
            source_files[source] = source_files.get(source, 0) + 1
        
        return {
            'total_chunks': self.index.ntotal,
            'embedding_dimension': self.embedding_dim,
            'model_name': self.embedding_model_name,
            'source_files': source_files,
            'index_size_mb': self._get_index_size_mb()
        }
    
    def clear(self) -> None:
        """Clear all data from the vector store."""
        logger.info("Clearing vector store")
        self.index = None
        self.document_metadata = []
        self.chunk_id_to_index = {}
        
        # Remove saved files
        index_path = os.path.join(self.vector_store_path, 'faiss_index.bin')
        metadata_path = os.path.join(self.vector_store_path, 'metadata.pkl')
        
        for path in [index_path, metadata_path]:
            if os.path.exists(path):
                os.remove(path)
                logger.info(f"Removed {path}")
    
    def _save_index(self) -> None:
        """Save the FAISS index and metadata to disk."""
        if self.index is None:
            return
        
        try:
            # Save FAISS index
            index_path = os.path.join(self.vector_store_path, 'faiss_index.bin')
            faiss.write_index(self.index, index_path)
            
            # Save metadata
            metadata_path = os.path.join(self.vector_store_path, 'metadata.pkl')
            with open(metadata_path, 'wb') as f:
                pickle.dump({
                    'document_metadata': self.document_metadata,
                    'chunk_id_to_index': self.chunk_id_to_index,
                    'embedding_model_name': self.embedding_model_name,
                    'embedding_dim': self.embedding_dim
                }, f)
            
            logger.debug(f"Saved vector store to {self.vector_store_path}")
            
        except Exception as e:
            logger.error(f"Error saving vector store: {e}")
    
    def _load_index(self) -> None:
        """Load the FAISS index and metadata from disk."""
        index_path = os.path.join(self.vector_store_path, 'faiss_index.bin')
        metadata_path = os.path.join(self.vector_store_path, 'metadata.pkl')
        
        if not (os.path.exists(index_path) and os.path.exists(metadata_path)):
            logger.info("No existing vector store found, starting fresh")
            return
        
        try:
            # Load FAISS index
            self.index = faiss.read_index(index_path)
            
            # Load metadata
            with open(metadata_path, 'rb') as f:
                data = pickle.load(f)
                self.document_metadata = data['document_metadata']
                self.chunk_id_to_index = data['chunk_id_to_index']
                
                # Verify model compatibility
                saved_model = data.get('embedding_model_name')
                if saved_model and saved_model != self.embedding_model_name:
                    logger.warning(
                        f"Embedding model mismatch: saved={saved_model}, "
                        f"current={self.embedding_model_name}. Consider rebuilding index."
                    )
            
            logger.info(f"Loaded vector store with {self.index.ntotal} chunks")
            
        except Exception as e:
            logger.error(f"Error loading vector store: {e}")
            logger.info("Starting with empty vector store")
            self.index = None
            self.document_metadata = []
            self.chunk_id_to_index = {}
    
    def _get_index_size_mb(self) -> float:
        """Get the size of the index files in MB."""
        total_size = 0
        
        for filename in ['faiss_index.bin', 'metadata.pkl']:
            path = os.path.join(self.vector_store_path, filename)
            if os.path.exists(path):
                total_size += os.path.getsize(path)
        
        return total_size / (1024 * 1024)  # Convert to MB


class RAGRetriever:
    """High-level interface for RAG document retrieval."""
    
    def __init__(self, vector_store: VectorStore = None):
        """Initialize RAG retriever.
        
        Args:
            vector_store: VectorStore instance to use
        """
        self.vector_store = vector_store or VectorStore()
    
    def retrieve_context(
        self, 
        query: str, 
        max_chunks: int = None, 
        score_threshold: float = 0.1
    ) -> str:
        """Retrieve relevant context for a query.
        
        Args:
            query: Search query
            max_chunks: Maximum number of chunks to retrieve
            score_threshold: Minimum similarity score
            
        Returns:
            Combined context text from relevant chunks
        """
        max_chunks = max_chunks or settings.MAX_RETRIEVED_DOCS
        
        # Search for relevant chunks
        results = self.vector_store.search(
            query=query,
            k=max_chunks,
            score_threshold=score_threshold
        )
        
        if not results:
            logger.info(f"No relevant context found for query: {query[:50]}...")
            return ""
        
        # Combine context from chunks
        context_parts = []
        for result in results:
            # Add source information
            source_info = f"[Source: {result['metadata'].get('source_file', 'Unknown')}"
            if result.get('page_number'):
                source_info += f", Page {result['page_number']}"
            source_info += f", Score: {result['similarity_score']:.3f}]"
            
            context_parts.append(f"{source_info}\n{result['text']}")
        
        context = "\n\n---\n\n".join(context_parts)
        
        logger.info(f"Retrieved {len(results)} chunks for context (total chars: {len(context)})")
        return context
    
    def get_relevant_templates(self, project_type: str = None, query: str = None) -> str:
        """Get relevant PMFlex templates and guidelines.
        
        Args:
            project_type: Type of project (e.g., 'portfolio', 'program', 'project')
            query: Specific query for template retrieval
            
        Returns:
            Relevant template context
        """
        # Build search query
        search_terms = []
        if project_type:
            search_terms.append(f"project type {project_type}")
        if query:
            search_terms.append(query)
        
        # Add PMFlex-specific terms
        search_terms.extend([
            "PMFlex methodology",
            "project management template",
            "status report template",
            "German federal government"
        ])
        
        search_query = " ".join(search_terms)
        
        return self.retrieve_context(
            query=search_query,
            max_chunks=settings.MAX_RETRIEVED_DOCS,
            score_threshold=0.05  # Lower threshold for template matching
        )
