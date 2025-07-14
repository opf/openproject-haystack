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
    version="1.0.0"
)

@app.on_event("startup")
async def startup_event():
    """Log application startup."""
    logger.info("OpenProject Haystack application starting up...")
    logger.info(f"Log level set to: {settings.LOG_LEVEL}")
    logger.info(f"Ollama URL: {settings.OLLAMA_URL}")
    logger.info(f"Ollama Model: {settings.OLLAMA_MODEL}")

# Include API routes
app.include_router(router)
