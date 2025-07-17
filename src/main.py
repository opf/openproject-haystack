#-- copyright
# OpenProject is an open source project management software.
# Copyright (C) the OpenProject GmbH
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License version 3.
#
# OpenProject is a fork of ChiliProject, which is a fork of Redmine. The copyright follows:
# Copyright (C) 2006-2013 Jean-Philippe Lang
# Copyright (C) 2010-2013 the ChiliProject Team
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
# See COPYRIGHT and LICENSE files for more details.
#++

"""Main FastAPI application for OpenProject Haystack."""

import logging
from fastapi import FastAPI
from src.api.routes import router
from src.utils.logging_config import setup_logging
from config.settings import settings

# Initialize logging before anything else
setup_logging(log_level=settings.LOG_LEVEL, log_format=settings.LOG_FORMAT)

# Get logger for this module
logger = logging.getLogger(__name__)

app = FastAPI(
    title="OpenProject Haystack",
    description="AI-powered application using Haystack and Ollama",
    version="1.0.0",
    root_path="/haystack"
)

@app.on_event("startup")
async def startup_event():
    """Log application startup and initialize RAG system."""
    logger.info("OpenProject Haystack application starting up...")
    logger.info(f"Log level set to: {settings.LOG_LEVEL}")
    logger.info(f"Ollama URL: {settings.OLLAMA_URL}")
    logger.info(f"Ollama Model: {settings.OLLAMA_MODEL}")
    
    # Initialize RAG system with timeout and error handling
    try:
        from src.pipelines.rag_pipeline import rag_pipeline
        logger.info("Initializing RAG system...")
        
        # Add timeout handling for RAG initialization
        import signal
        
        def timeout_handler(signum, frame):
            raise TimeoutError("RAG initialization timed out")
        
        # Set timeout for RAG initialization (60 seconds)
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(60)
        
        try:
            result = rag_pipeline.initialize()
            signal.alarm(0)  # Cancel timeout
            
            if result['status'] == 'success':
                logger.info("RAG system initialized successfully")
                init_result = result.get('initialization_result', {})
                if init_result.get('documents_processed', 0) > 0:
                    logger.info(f"Processed {init_result['documents_processed']} PMFlex documents")
                    logger.info(f"Created {init_result['chunks_created']} text chunks")
                else:
                    logger.warning("No PMFlex documents found - RAG system running without context")
            else:
                logger.warning(f"RAG system initialization had issues: {result.get('message', 'Unknown error')}")
                
        except TimeoutError:
            signal.alarm(0)  # Cancel timeout
            logger.error("RAG system initialization timed out after 60 seconds")
            logger.info("Application will continue without RAG enhancement")
            
    except Exception as e:
        logger.error(f"Failed to initialize RAG system: {e}")
        logger.info("Application will continue without RAG enhancement")

# Include API routes
app.include_router(router)
