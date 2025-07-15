
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

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from haystack_integrations.components.generators.ollama import OllamaGenerator

app = FastAPI()

class Prompt(BaseModel):
    prompt: str

generator = OllamaGenerator(
    model="mistral:latest",
    url="http://ollama:11434",
    generation_kwargs={"num_predict": 1000, "temperature": 0.7}
)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/generate")
def generate(data: Prompt):
    try:
        result = generator.run(data.prompt)
        return {"response": result["replies"][0]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
