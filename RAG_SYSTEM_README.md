# RAG System Implementation for OpenProject Haystack

This document describes the Retrieval-Augmented Generation (RAG) system implementation that enhances project status reports with PMFlex methodology context and templates.

## Overview

The RAG system integrates PMFlex (German Federal Government Project Management) documents into the report generation process, providing context-aware, methodology-compliant project status reports.

## Architecture

### Core Components

1. **Document Processor** (`src/services/document_processor.py`)
   - Processes PDF, DOCX, PPTX, and TXT files
   - Extracts text with metadata preservation
   - Chunks documents with configurable overlap
   - Supports multiple document formats

2. **Vector Store** (`src/services/vector_store.py`)
   - FAISS-based vector storage for embeddings
   - Sentence-transformers for text embeddings
   - Similarity search with configurable thresholds
   - Persistent storage with metadata

3. **Document Manager** (`src/services/document_manager.py`)
   - Manages document lifecycle and indexing
   - Handles document updates and refresh
   - Provides statistics and validation
   - Maintains document metadata index

4. **RAG Pipeline** (`src/pipelines/rag_pipeline.py`)
   - High-level RAG orchestration
   - Context enhancement for reports
   - Template and methodology retrieval
   - Integration with generation pipeline

### Integration Points

- **Generation Pipeline**: Enhanced with RAG context retrieval
- **Report Templates**: PMFlex-aware templates with context integration
- **API Endpoints**: RAG management and status endpoints
- **Startup Process**: Automatic RAG system initialization

## Document Structure

```
documents/
├── pmflex/
│   ├── templates/
│   │   ├── pmflex_status_report_template.txt
│   │   └── [other templates]
│   ├── handbooks/
│   │   ├── pmflex_methodology_guide.txt
│   │   └── [other handbooks]
│   └── metadata/
│       └── document_index.json
```

### Supported Document Formats

- **PDF**: Full text extraction with page metadata
- **DOCX**: Paragraph-based text extraction
- **PPTX**: Slide-based text extraction
- **TXT**: Plain text processing

## Configuration

### Environment Variables

```bash
# RAG Configuration
DOCUMENTS_PATH=documents
VECTOR_STORE_PATH=vector_store
EMBEDDING_MODEL=all-MiniLM-L6-v2
CHUNK_SIZE=800
CHUNK_OVERLAP=100
MAX_RETRIEVED_DOCS=5
```

### Settings (`config/settings.py`)

```python
# RAG Configuration
DOCUMENTS_PATH: str = os.getenv("DOCUMENTS_PATH", "documents")
VECTOR_STORE_PATH: str = os.getenv("VECTOR_STORE_PATH", "vector_store")
EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "800"))
CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "100"))
MAX_RETRIEVED_DOCS: int = int(os.getenv("MAX_RETRIEVED_DOCS", "5"))
```

## API Endpoints

### RAG Management

#### Initialize RAG System
```http
POST /rag/initialize
```
Initializes the RAG system by loading and processing all PMFlex documents.

#### Get RAG Status
```http
GET /rag/status
```
Returns current RAG system status, statistics, and validation results.

#### Refresh Documents
```http
POST /rag/refresh
```
Refreshes the document index by checking for updates and reprocessing changed files.

#### Search Documents
```http
POST /rag/search?query=<search_query>&max_results=5
```
Searches RAG documents for specific information.

### Enhanced Report Generation

The existing `/generate-project-status-report` endpoint now automatically includes PMFlex context when available.

## Usage Examples

### Basic RAG System Setup

1. **Add PMFlex Documents**
   ```bash
   # Place documents in the appropriate directories
   documents/pmflex/templates/
   documents/pmflex/handbooks/
   ```

2. **Initialize System**
   ```bash
   curl -X POST http://localhost:8000/rag/initialize
   ```

3. **Check Status**
   ```bash
   curl http://localhost:8000/rag/status
   ```

### Enhanced Report Generation

```bash
curl -X POST http://localhost:8000/generate-project-status-report \
  -H "Content-Type: application/json" \
  -d '{
    "project": {
      "id": 123,
      "type": "project"
    },
    "openproject": {
      "base_url": "https://openproject.example.com",
      "user_token": "your-api-token"
    }
  }'
```

The generated report will now include:
- PMFlex methodology guidance
- Relevant templates and best practices
- Compliance requirements
- German federal government standards

## Document Processing Workflow

1. **Document Discovery**: Scans `documents/pmflex/` for supported files
2. **Text Extraction**: Extracts text based on file format
3. **Chunking**: Splits text into overlapping chunks
4. **Embedding**: Generates vector embeddings using sentence-transformers
5. **Indexing**: Stores embeddings and metadata in FAISS index
6. **Persistence**: Saves index and metadata to disk

## Context Enhancement Process

1. **Query Analysis**: Analyzes project type and work package data
2. **Template Retrieval**: Searches for relevant PMFlex templates
3. **Methodology Context**: Retrieves applicable methodology guidance
4. **Governance Context**: Finds compliance and governance requirements
5. **Context Combination**: Merges contexts for report generation
6. **Report Enhancement**: Integrates context into LLM prompt

## Performance Considerations

### Embedding Model
- Default: `all-MiniLM-L6-v2` (384 dimensions)
- Fast inference with good quality
- Suitable for German and English text

### Vector Store
- FAISS IndexFlatIP for cosine similarity
- In-memory index with disk persistence
- Efficient for small to medium document collections

### Chunking Strategy
- 800 characters per chunk with 100 character overlap
- Preserves context across chunk boundaries
- Balances retrieval granularity and context

## Monitoring and Maintenance

### Health Checks
- RAG system status endpoint
- Document index validation
- Vector store statistics
- Embedding model availability

### Document Management
- Automatic change detection
- Incremental updates
- Document metadata tracking
- Error handling and logging

### Performance Metrics
- Document processing times
- Embedding generation speed
- Search response times
- Context retrieval accuracy

## Troubleshooting

### Common Issues

1. **No Documents Found**
   - Check document directory structure
   - Verify file formats are supported
   - Review file permissions

2. **Embedding Model Loading**
   - Ensure internet connectivity for model download
   - Check available disk space
   - Verify sentence-transformers installation

3. **Vector Store Errors**
   - Check FAISS installation
   - Verify write permissions for vector_store directory
   - Review memory availability

4. **Context Quality Issues**
   - Adjust chunk size and overlap settings
   - Review document content quality
   - Tune similarity thresholds

### Logging

RAG system activities are logged with appropriate levels:
- INFO: Normal operations and status
- WARNING: Non-critical issues
- ERROR: System errors requiring attention

## Future Enhancements

### Planned Features
- Multi-language support for German/English documents
- Advanced retrieval strategies (hybrid search)
- Document versioning and change tracking
- Real-time document updates
- Custom embedding fine-tuning

### Scalability Improvements
- Distributed vector storage
- Async document processing
- Caching layer for frequent queries
- Batch processing capabilities

## Dependencies

### Required Packages
```
PyMuPDF>=1.23.0          # PDF processing
python-docx>=0.8.11      # Word document processing
python-pptx>=0.6.21      # PowerPoint processing
faiss-cpu>=1.7.4         # Vector similarity search
sentence-transformers>=2.2.2  # Text embeddings
nltk>=3.8.1              # Text processing utilities
```

### System Requirements
- Python 3.9+
- 4GB+ RAM (for embedding model)
- 1GB+ disk space (for vector store)
- Internet connectivity (initial model download)

## Security Considerations

- Document access controls
- Sensitive information handling
- API endpoint security
- Data encryption at rest
- Audit logging capabilities

## Contributing

When adding new documents or modifying the RAG system:

1. Follow the established directory structure
2. Test document processing with sample files
3. Validate embedding quality and retrieval accuracy
4. Update documentation and examples
5. Consider performance impact of changes

For questions or support, contact the development team or refer to the main project documentation.
