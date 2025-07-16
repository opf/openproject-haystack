"""RAG pipeline for enhanced report generation."""

import logging
from typing import List, Dict, Any, Optional
from src.services.document_manager import DocumentManager
from src.services.vector_store import RAGRetriever
from src.models.schemas import WorkPackage
from config.settings import settings

logger = logging.getLogger(__name__)


class RAGPipeline:
    """RAG pipeline for document-enhanced report generation."""
    
    def __init__(self, document_manager: DocumentManager = None):
        """Initialize RAG pipeline.
        
        Args:
            document_manager: DocumentManager instance
        """
        self.document_manager = document_manager or DocumentManager()
        self.retriever = RAGRetriever(self.document_manager.vector_store)
        self._initialized = False
    
    def initialize(self) -> Dict[str, Any]:
        """Initialize the RAG pipeline.
        
        Returns:
            Dictionary with initialization results
        """
        if self._initialized:
            logger.info("RAG pipeline already initialized")
            return {'status': 'already_initialized'}
        
        logger.info("Initializing RAG pipeline...")
        
        try:
            # Validate document directory structure
            validation = self.document_manager.validate_documents_directory()
            if not validation['valid']:
                logger.warning(f"Document directory validation issues: {validation['issues']}")
                # Continue with initialization even if there are issues
            
            # Initialize document manager (loads and processes documents)
            result = self.document_manager.initialize_rag_system()
            
            self._initialized = True
            logger.info("RAG pipeline initialized successfully")
            
            return {
                'status': 'success',
                'initialization_result': result,
                'validation_result': validation
            }
            
        except Exception as e:
            logger.error(f"Error initializing RAG pipeline: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def enhance_project_report_context(
        self,
        project_id: str,
        project_type: str,
        work_packages: List[WorkPackage],
        analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Enhance project report context with RAG-retrieved information.
        
        Args:
            project_id: Project identifier
            project_type: Type of project (portfolio, program, project)
            work_packages: List of work packages
            analysis: Work package analysis results
            
        Returns:
            Dictionary with enhanced context
        """
        if not self._initialized:
            logger.warning("RAG pipeline not initialized, initializing now...")
            init_result = self.initialize()
            if init_result['status'] != 'success':
                logger.error("Failed to initialize RAG pipeline")
                return {'pmflex_context': '', 'template_guidance': ''}
        
        logger.info(f"Enhancing report context for project {project_id} (type: {project_type})")
        
        try:
            # Get relevant PMFlex templates and methodology
            template_context = self._get_template_context(project_type, analysis)
            
            # Get methodology guidance
            methodology_context = self._get_methodology_context(project_type, work_packages)
            
            # Get compliance and governance guidance
            governance_context = self._get_governance_context(project_type, analysis)
            
            # Combine all contexts
            enhanced_context = {
                'pmflex_context': self._combine_contexts([
                    template_context,
                    methodology_context,
                    governance_context
                ]),
                'template_guidance': template_context,
                'methodology_guidance': methodology_context,
                'governance_guidance': governance_context,
                'context_sources': self._get_context_sources()
            }
            
            logger.info(f"Enhanced context generated (total chars: {len(enhanced_context['pmflex_context'])})")
            return enhanced_context
            
        except Exception as e:
            logger.error(f"Error enhancing report context: {e}")
            return {
                'pmflex_context': '',
                'template_guidance': '',
                'methodology_guidance': '',
                'governance_guidance': '',
                'error': str(e)
            }
    
    def _get_template_context(self, project_type: str, analysis: Dict[str, Any]) -> str:
        """Get relevant template context from PMFlex documents.
        
        Args:
            project_type: Type of project
            analysis: Work package analysis
            
        Returns:
            Template context string
        """
        # Build query for template retrieval
        query_parts = [
            f"{project_type} project status report template",
            "PMFlex status report format",
            "German federal government project reporting"
        ]
        
        # Add analysis-specific terms
        if analysis.get('key_metrics', {}).get('completion_rate', 0) < 50:
            query_parts.append("project delays reporting template")
        
        if analysis.get('timeline_insights', {}).get('overdue_items', 0) > 0:
            query_parts.append("overdue tasks reporting guidelines")
        
        query = " ".join(query_parts)
        
        return self.retriever.retrieve_context(
            query=query,
            max_chunks=3,
            score_threshold=0.1
        )
    
    def _get_methodology_context(self, project_type: str, work_packages: List[WorkPackage]) -> str:
        """Get PMFlex methodology guidance.
        
        Args:
            project_type: Type of project
            work_packages: List of work packages
            
        Returns:
            Methodology context string
        """
        # Build query for methodology guidance
        query_parts = [
            f"PMFlex {project_type} methodology",
            "project management best practices",
            "German federal government project standards"
        ]
        
        # Add work package specific terms
        if work_packages:
            query_parts.extend([
                "work package management",
                "task tracking methodology",
                "project progress assessment"
            ])
        
        query = " ".join(query_parts)
        
        return self.retriever.retrieve_context(
            query=query,
            max_chunks=3,
            score_threshold=0.1
        )
    
    def _get_governance_context(self, project_type: str, analysis: Dict[str, Any]) -> str:
        """Get governance and compliance guidance.
        
        Args:
            project_type: Type of project
            analysis: Work package analysis
            
        Returns:
            Governance context string
        """
        # Build query for governance guidance
        query_parts = [
            "PMFlex governance framework",
            "project compliance requirements",
            "risk management guidelines",
            "quality assurance standards"
        ]
        
        # Add risk-specific terms if issues detected
        if analysis.get('timeline_insights', {}).get('overdue_items', 0) > 0:
            query_parts.append("project risk mitigation")
        
        if analysis.get('key_metrics', {}).get('completion_rate', 0) < 30:
            query_parts.append("project recovery procedures")
        
        query = " ".join(query_parts)
        
        return self.retriever.retrieve_context(
            query=query,
            max_chunks=2,
            score_threshold=0.1
        )
    
    def _combine_contexts(self, contexts: List[str]) -> str:
        """Combine multiple context strings.
        
        Args:
            contexts: List of context strings
            
        Returns:
            Combined context string
        """
        # Filter out empty contexts
        valid_contexts = [ctx for ctx in contexts if ctx.strip()]
        
        if not valid_contexts:
            return ""
        
        return "\n\n=== PMFlex Context ===\n\n".join(valid_contexts)
    
    def _get_context_sources(self) -> List[str]:
        """Get list of context sources used.
        
        Returns:
            List of source document names
        """
        try:
            stats = self.document_manager.get_document_stats()
            return list(stats.get('vector_store_stats', {}).get('source_files', {}).keys())
        except Exception as e:
            logger.error(f"Error getting context sources: {e}")
            return []
    
    def search_documents(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Search documents for specific information.
        
        Args:
            query: Search query
            max_results: Maximum number of results
            
        Returns:
            List of search results
        """
        if not self._initialized:
            logger.warning("RAG pipeline not initialized")
            return []
        
        try:
            return self.retriever.vector_store.search(
                query=query,
                k=max_results,
                score_threshold=0.1
            )
        except Exception as e:
            logger.error(f"Error searching documents: {e}")
            return []
    
    def get_pipeline_stats(self) -> Dict[str, Any]:
        """Get RAG pipeline statistics.
        
        Returns:
            Dictionary with pipeline statistics
        """
        try:
            doc_stats = self.document_manager.get_document_stats()
            
            return {
                'initialized': self._initialized,
                'document_stats': doc_stats,
                'pipeline_status': 'ready' if self._initialized else 'not_initialized'
            }
            
        except Exception as e:
            logger.error(f"Error getting pipeline stats: {e}")
            return {
                'initialized': self._initialized,
                'error': str(e),
                'pipeline_status': 'error'
            }
    
    def refresh_documents(self) -> Dict[str, Any]:
        """Refresh the document index.
        
        Returns:
            Dictionary with refresh results
        """
        try:
            return self.document_manager.refresh_documents()
        except Exception as e:
            logger.error(f"Error refreshing documents: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def add_document(self, file_path: str) -> Dict[str, Any]:
        """Add a new document to the RAG system.
        
        Args:
            file_path: Path to the document file
            
        Returns:
            Dictionary with processing results
        """
        try:
            return self.document_manager.add_document(file_path)
        except Exception as e:
            logger.error(f"Error adding document {file_path}: {e}")
            return {
                'status': 'error',
                'message': str(e),
                'file_path': file_path
            }
    
    def validate_setup(self) -> Dict[str, Any]:
        """Validate the RAG pipeline setup.
        
        Returns:
            Dictionary with validation results
        """
        try:
            # Validate document directory
            dir_validation = self.document_manager.validate_documents_directory()
            
            # Check vector store
            vector_stats = self.retriever.vector_store.get_stats()
            
            # Check if pipeline is initialized
            pipeline_ready = self._initialized and vector_stats['total_chunks'] > 0
            
            return {
                'pipeline_ready': pipeline_ready,
                'directory_validation': dir_validation,
                'vector_store_stats': vector_stats,
                'recommendations': self._get_setup_recommendations(
                    dir_validation, vector_stats, pipeline_ready
                )
            }
            
        except Exception as e:
            logger.error(f"Error validating RAG setup: {e}")
            return {
                'pipeline_ready': False,
                'error': str(e)
            }
    
    def _get_setup_recommendations(
        self,
        dir_validation: Dict[str, Any],
        vector_stats: Dict[str, Any],
        pipeline_ready: bool
    ) -> List[str]:
        """Get setup recommendations based on validation results.
        
        Args:
            dir_validation: Directory validation results
            vector_stats: Vector store statistics
            pipeline_ready: Whether pipeline is ready
            
        Returns:
            List of recommendation strings
        """
        recommendations = []
        
        if not dir_validation.get('valid', False):
            recommendations.append(
                "Create the required directory structure and add PMFlex documents"
            )
        
        if vector_stats.get('total_chunks', 0) == 0:
            recommendations.append(
                "Add PMFlex templates and handbooks to the documents/pmflex directory"
            )
        
        if not pipeline_ready:
            recommendations.append(
                "Initialize the RAG pipeline by calling the initialization endpoint"
            )
        
        if vector_stats.get('total_chunks', 0) < 10:
            recommendations.append(
                "Add more PMFlex documents for better context retrieval"
            )
        
        return recommendations


# Global RAG pipeline instance
rag_pipeline = RAGPipeline()
