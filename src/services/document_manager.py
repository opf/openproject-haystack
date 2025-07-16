"""Document manager service for RAG system."""

import os
import json
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime
from src.services.document_processor import DocumentProcessor
from src.services.vector_store import VectorStore
from config.settings import settings

logger = logging.getLogger(__name__)


class DocumentManager:
    """Manages document loading, processing, and indexing for RAG system."""
    
    def __init__(
        self,
        documents_path: str = None,
        document_processor: DocumentProcessor = None,
        vector_store: VectorStore = None
    ):
        """Initialize document manager.
        
        Args:
            documents_path: Path to documents directory
            document_processor: DocumentProcessor instance
            vector_store: VectorStore instance
        """
        self.documents_path = documents_path or settings.DOCUMENTS_PATH
        self.document_processor = document_processor or DocumentProcessor(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP
        )
        self.vector_store = vector_store or VectorStore()
        
        # Ensure documents directory exists
        os.makedirs(self.documents_path, exist_ok=True)
        
        # Path to document index metadata
        self.index_metadata_path = os.path.join(
            self.documents_path, 
            "pmflex", 
            "metadata", 
            "document_index.json"
        )
        
        # Load existing document index
        self.document_index = self._load_document_index()
    
    def initialize_rag_system(self) -> Dict[str, Any]:
        """Initialize the RAG system by loading all documents.
        
        Returns:
            Dictionary with initialization results
        """
        logger.info("Initializing RAG system...")
        
        # Scan for documents
        documents = self._scan_documents()
        
        if not documents:
            logger.warning("No documents found in documents directory")
            return {
                'status': 'success',
                'message': 'RAG system initialized with no documents',
                'documents_processed': 0,
                'chunks_created': 0
            }
        
        # Process new or updated documents
        processed_count = 0
        total_chunks = 0
        
        for doc_path in documents:
            try:
                if self._should_process_document(doc_path):
                    logger.info(f"Processing document: {doc_path}")
                    
                    # Process document into chunks
                    chunks = self.document_processor.process_document(doc_path)
                    
                    if chunks:
                        # Add chunks to vector store
                        self.vector_store.add_documents(chunks)
                        
                        # Update document index
                        self._update_document_index(doc_path, len(chunks))
                        
                        processed_count += 1
                        total_chunks += len(chunks)
                        
                        logger.info(f"Added {len(chunks)} chunks from {doc_path}")
                    else:
                        logger.warning(f"No chunks created from {doc_path}")
                
            except Exception as e:
                logger.error(f"Error processing document {doc_path}: {e}")
                continue
        
        # Save updated document index
        self._save_document_index()
        
        # Get vector store stats
        stats = self.vector_store.get_stats()
        
        result = {
            'status': 'success',
            'message': f'RAG system initialized successfully',
            'documents_found': len(documents),
            'documents_processed': processed_count,
            'chunks_created': total_chunks,
            'total_chunks_in_store': stats['total_chunks'],
            'vector_store_stats': stats
        }
        
        logger.info(f"RAG initialization complete: {result}")
        return result
    
    def add_document(self, file_path: str, force_reprocess: bool = False) -> Dict[str, Any]:
        """Add a single document to the RAG system.
        
        Args:
            file_path: Path to the document file
            force_reprocess: Force reprocessing even if document exists
            
        Returns:
            Dictionary with processing results
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Document not found: {file_path}")
        
        logger.info(f"Adding document to RAG system: {file_path}")
        
        try:
            # Check if document should be processed
            if not force_reprocess and not self._should_process_document(file_path):
                return {
                    'status': 'skipped',
                    'message': 'Document already up to date',
                    'file_path': file_path,
                    'chunks_created': 0
                }
            
            # Remove existing chunks if reprocessing
            if force_reprocess:
                removed_count = self.vector_store.remove_documents_by_source(file_path)
                if removed_count > 0:
                    logger.info(f"Removed {removed_count} existing chunks from {file_path}")
            
            # Process document
            chunks = self.document_processor.process_document(file_path)
            
            if not chunks:
                return {
                    'status': 'error',
                    'message': 'No chunks could be created from document',
                    'file_path': file_path,
                    'chunks_created': 0
                }
            
            # Add to vector store
            self.vector_store.add_documents(chunks)
            
            # Update document index
            self._update_document_index(file_path, len(chunks))
            self._save_document_index()
            
            return {
                'status': 'success',
                'message': f'Document processed successfully',
                'file_path': file_path,
                'chunks_created': len(chunks)
            }
            
        except Exception as e:
            logger.error(f"Error adding document {file_path}: {e}")
            return {
                'status': 'error',
                'message': str(e),
                'file_path': file_path,
                'chunks_created': 0
            }
    
    def remove_document(self, file_path: str) -> Dict[str, Any]:
        """Remove a document from the RAG system.
        
        Args:
            file_path: Path to the document file
            
        Returns:
            Dictionary with removal results
        """
        logger.info(f"Removing document from RAG system: {file_path}")
        
        try:
            # Remove from vector store
            removed_count = self.vector_store.remove_documents_by_source(file_path)
            
            # Remove from document index
            if file_path in self.document_index:
                del self.document_index[file_path]
                self._save_document_index()
            
            return {
                'status': 'success',
                'message': f'Document removed successfully',
                'file_path': file_path,
                'chunks_removed': removed_count
            }
            
        except Exception as e:
            logger.error(f"Error removing document {file_path}: {e}")
            return {
                'status': 'error',
                'message': str(e),
                'file_path': file_path,
                'chunks_removed': 0
            }
    
    def refresh_documents(self) -> Dict[str, Any]:
        """Refresh all documents by checking for updates and reprocessing if needed.
        
        Returns:
            Dictionary with refresh results
        """
        logger.info("Refreshing document index...")
        
        # Scan for all documents
        documents = self._scan_documents()
        
        processed_count = 0
        total_chunks = 0
        errors = []
        
        for doc_path in documents:
            try:
                if self._should_process_document(doc_path):
                    result = self.add_document(doc_path, force_reprocess=True)
                    if result['status'] == 'success':
                        processed_count += 1
                        total_chunks += result['chunks_created']
                    else:
                        errors.append(f"{doc_path}: {result['message']}")
            except Exception as e:
                errors.append(f"{doc_path}: {str(e)}")
        
        # Remove documents that no longer exist
        removed_count = 0
        for indexed_path in list(self.document_index.keys()):
            if not os.path.exists(indexed_path):
                result = self.remove_document(indexed_path)
                if result['status'] == 'success':
                    removed_count += 1
        
        return {
            'status': 'success',
            'message': 'Document refresh completed',
            'documents_found': len(documents),
            'documents_processed': processed_count,
            'documents_removed': removed_count,
            'total_chunks': total_chunks,
            'errors': errors
        }
    
    def get_document_stats(self) -> Dict[str, Any]:
        """Get statistics about indexed documents.
        
        Returns:
            Dictionary with document statistics
        """
        vector_stats = self.vector_store.get_stats()
        
        # Count documents by type
        doc_types = {}
        for doc_path in self.document_index:
            ext = Path(doc_path).suffix.lower()
            doc_types[ext] = doc_types.get(ext, 0) + 1
        
        # Count documents by category (templates vs handbooks)
        categories = {'templates': 0, 'handbooks': 0, 'other': 0}
        for doc_path in self.document_index:
            if 'templates' in doc_path:
                categories['templates'] += 1
            elif 'handbooks' in doc_path:
                categories['handbooks'] += 1
            else:
                categories['other'] += 1
        
        return {
            'total_documents': len(self.document_index),
            'document_types': doc_types,
            'document_categories': categories,
            'vector_store_stats': vector_stats,
            'last_updated': max(
                (info.get('last_processed', '') for info in self.document_index.values()),
                default=''
            )
        }
    
    def _scan_documents(self) -> List[str]:
        """Scan documents directory for supported files.
        
        Returns:
            List of document file paths
        """
        documents = []
        supported_extensions = self.document_processor.supported_formats
        
        # Scan PMFlex directories
        pmflex_path = os.path.join(self.documents_path, "pmflex")
        
        for root, dirs, files in os.walk(pmflex_path):
            # Skip metadata directory
            if 'metadata' in root:
                continue
                
            for file in files:
                file_path = os.path.join(root, file)
                if Path(file_path).suffix.lower() in supported_extensions:
                    documents.append(file_path)
        
        logger.info(f"Found {len(documents)} documents in {pmflex_path}")
        return documents
    
    def _should_process_document(self, file_path: str) -> bool:
        """Check if a document should be processed.
        
        Args:
            file_path: Path to the document
            
        Returns:
            True if document should be processed
        """
        if not os.path.exists(file_path):
            return False
        
        # Check if document is in index
        if file_path not in self.document_index:
            return True
        
        # Check if file has been modified since last processing
        file_mtime = os.path.getmtime(file_path)
        last_processed = self.document_index[file_path].get('last_processed_timestamp', 0)
        
        return file_mtime > last_processed
    
    def _update_document_index(self, file_path: str, chunk_count: int) -> None:
        """Update the document index with processing information.
        
        Args:
            file_path: Path to the processed document
            chunk_count: Number of chunks created
        """
        try:
            metadata = self.document_processor.get_document_metadata(file_path)
            
            self.document_index[file_path] = {
                'filename': metadata['filename'],
                'file_size': metadata['file_size'],
                'file_extension': metadata['file_extension'],
                'chunk_count': chunk_count,
                'last_processed': datetime.now().isoformat(),
                'last_processed_timestamp': os.path.getmtime(file_path),
                'metadata': metadata
            }
            
        except Exception as e:
            logger.error(f"Error updating document index for {file_path}: {e}")
    
    def _load_document_index(self) -> Dict[str, Any]:
        """Load the document index from disk.
        
        Returns:
            Document index dictionary
        """
        if not os.path.exists(self.index_metadata_path):
            logger.info("No existing document index found")
            return {}
        
        try:
            with open(self.index_metadata_path, 'r', encoding='utf-8') as f:
                index = json.load(f)
                logger.info(f"Loaded document index with {len(index)} entries")
                return index
        except Exception as e:
            logger.error(f"Error loading document index: {e}")
            return {}
    
    def _save_document_index(self) -> None:
        """Save the document index to disk."""
        try:
            # Ensure metadata directory exists
            os.makedirs(os.path.dirname(self.index_metadata_path), exist_ok=True)
            
            with open(self.index_metadata_path, 'w', encoding='utf-8') as f:
                json.dump(self.document_index, f, indent=2, ensure_ascii=False)
                
            logger.debug(f"Saved document index with {len(self.document_index)} entries")
            
        except Exception as e:
            logger.error(f"Error saving document index: {e}")
    
    def clear_all_documents(self) -> Dict[str, Any]:
        """Clear all documents from the RAG system.
        
        Returns:
            Dictionary with clearing results
        """
        logger.info("Clearing all documents from RAG system")
        
        try:
            # Clear vector store
            self.vector_store.clear()
            
            # Clear document index
            self.document_index = {}
            self._save_document_index()
            
            return {
                'status': 'success',
                'message': 'All documents cleared from RAG system'
            }
            
        except Exception as e:
            logger.error(f"Error clearing documents: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def validate_documents_directory(self) -> Dict[str, Any]:
        """Validate the documents directory structure.
        
        Returns:
            Dictionary with validation results
        """
        issues = []
        
        # Check if main documents directory exists
        if not os.path.exists(self.documents_path):
            issues.append(f"Documents directory does not exist: {self.documents_path}")
        
        # Check PMFlex directory structure
        pmflex_path = os.path.join(self.documents_path, "pmflex")
        if not os.path.exists(pmflex_path):
            issues.append(f"PMFlex directory does not exist: {pmflex_path}")
        
        # Check subdirectories
        expected_dirs = ["templates", "handbooks", "metadata"]
        for dir_name in expected_dirs:
            dir_path = os.path.join(pmflex_path, dir_name)
            if not os.path.exists(dir_path):
                issues.append(f"Missing directory: {dir_path}")
        
        # Check for documents
        documents = self._scan_documents()
        if not documents:
            issues.append("No supported documents found in PMFlex directories")
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'documents_found': len(documents) if not issues else 0,
            'directory_structure': {
                'documents_path': self.documents_path,
                'pmflex_path': pmflex_path,
                'expected_dirs': expected_dirs
            }
        }
