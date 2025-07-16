import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from config.settings import settings
from src.services.openproject_client import OpenProjectClient, OpenProjectAPIError
from src.pipelines.generation import generation_pipeline
import asyncio
import json
import concurrent.futures
import re

logger = logging.getLogger(__name__)

@dataclass
class Candidate:
    project_id: Any
    name: str
    score: Optional[float]
    reason: str

class SuggestionPipeline:
    """Pipeline for suggesting suitable sub-projects for a portfolio project."""
    def __init__(self, openproject_client: OpenProjectClient):
        self.openproject_client = openproject_client

    def suggest(self, project_id: str) -> Dict[str, Any]:
        """Main entry point: Suggest suitable sub-projects for a portfolio project."""
        try:
            portfolio_project = asyncio.run(self.openproject_client.get_project_info(project_id))
            logger.info(f"Fetched portfolio project: {portfolio_project.get('name', project_id)}")

            if portfolio_project.get("projectType") != "portfolio":
                logger.warning("Project is not a portfolio. Returning message.")
                return {
                    "portfolio": portfolio_project.get("name"),
                    "candidates": [],
                    "text": "The selected project is not a portfolio project."
                }

            sub_projects = self._get_sub_projects_parallel_with_fallback(project_id)
            logger.info(f"Fetched {len(sub_projects)} sub-projects for portfolio {project_id}")

            if not portfolio_project or not sub_projects:
                logger.warning("No portfolio or sub-project info available. Returning empty candidates.")
                return {
                    "portfolio": portfolio_project.get("name") if portfolio_project else None,
                    "candidates": [],
                    "text": "No portfolio or sub-project info available."
                }

            candidates, llm_response = self._llm_score_candidates(portfolio_project, sub_projects)
            candidate_list = [self._candidate_to_dict(c) for c in candidates]

            return {
                "portfolio": portfolio_project.get("name"),
                "candidates": candidate_list,
                "text": llm_response
            }
        except OpenProjectAPIError as e:
            logger.error(f"OpenProject API error: {e.message}")
            raise
        except Exception as e:
            logger.error(f"Suggestion pipeline error: {e}")
            raise

    def _get_sub_projects_parallel_with_fallback(self, project_id: str) -> List[Dict[str, Any]]:
        """Recursively traverse all descendants of the portfolio, skipping Teilportfolio but traversing through them to reach programs and projects. Collect all programs and projects under the portfolio, regardless of depth, but exclude any with 'Teilportfolio' in the name from the results (but not from traversal)."""
        all_projects = asyncio.run(self.openproject_client.get_all_projects())
        for p in all_projects:
            logger.debug(f"Project {p.get('id')}: _links = {p.get('_links')}")
        id_to_project = {str(p.get('id')): p for p in all_projects}
        # Build parent->children map
        parent_to_children = {}
        for p in all_projects:
            parent_href = p.get('_links', {}).get('parent', {}).get('href')
            if parent_href:
                parent_id = parent_href.rstrip('/').split('/')[-1]
                parent_to_children.setdefault(parent_id, []).append(p)
        # Recursive traversal
        def collect_candidates(current_id):
            candidates = []
            children = parent_to_children.get(str(current_id), [])
            for child in children:
                name = child.get('name') or ''
                project_type = child.get('projectType')
                if 'Teilportfolio' in name:
                    # Skip as candidate, but traverse its children
                    candidates.extend(collect_candidates(child.get('id')))
                elif project_type in ('program', 'project'):
                    candidates.append(child)
                    # Also traverse children in case of nested programs
                    candidates.extend(collect_candidates(child.get('id')))
                else:
                    # Traverse children for any other type
                    candidates.extend(collect_candidates(child.get('id')))
            return candidates
        return collect_candidates(project_id)

    def _extract_custom_fields(self, project_info: dict) -> dict:
        """Extract custom fields from a project info dict, using only the 'raw' value if present."""
        result = {}
        for k, v in project_info.items():
            if k.startswith('customField'):
                if isinstance(v, dict) and 'raw' in v:
                    result[k] = v['raw']
                else:
                    result[k] = v
        return result

    def _get_work_package_names(self, project_id: str) -> List[str]:
        """Fetch work package names for a project synchronously."""
        if not project_id:
            return []
        try:
            work_packages = asyncio.run(self.openproject_client.get_work_packages(str(project_id)))
            return [wp.subject for wp in work_packages if hasattr(wp, 'subject')]
        except Exception as e:
            logger.warning(f"Failed to fetch work packages for project {project_id}: {e}")
            return []

    def _build_suggestion_prompt(self, portfolio_info: dict, sub_projects: List[dict]) -> str:
        """Build the LLM prompt with all relevant info."""
        portfolio_custom_fields = self._extract_custom_fields(portfolio_info)
        portfolio_wp_names = self._get_work_package_names(str(portfolio_info.get('id', '')))
        prompt = [
            "You are an expert project portfolio advisor.",
            "Portfolio project info:",
            f"Name: {portfolio_info.get('name')}",
            f"Description: {portfolio_info.get('description', {}).get('raw', '')}"
        ]
        if portfolio_custom_fields:
            prompt.append("Custom fields:")
            prompt.extend([f"  {k}: {v}" for k, v in portfolio_custom_fields.items()])
        if portfolio_wp_names:
            prompt.append("Work packages:")
            prompt.extend([f"  - {wp_name}" for wp_name in portfolio_wp_names])
        prompt.append("\nSub-projects:")
        for i, sp in enumerate(sub_projects, 1):
            sp_custom_fields = self._extract_custom_fields(sp)
            sp_wp_names = self._get_work_package_names(str(sp.get('id', '')))
            prompt.append(f"{i}. Name: {sp.get('name')}")
            prompt.append(f"   Description: {sp.get('description', {}).get('raw', '')}")
            prompt.append(f"   ID: {sp.get('id')}")
            if sp_custom_fields:
                prompt.append("   Custom fields:")
                prompt.extend([f"     {k}: {v}" for k, v in sp_custom_fields.items()])
            if sp_wp_names:
                prompt.append("   Work packages:")
                prompt.extend([f"     - {wp_name}" for wp_name in sp_wp_names])
        prompt.append(
            "For all projects and programs, rate its suitability as a portfolio candidate for the above portfolio "
            "on a scale from 0 to 100 (integer), and briefly explain your reasoning (1-2 sentences). "
            "Only return projects that have a value above 70. "
            "Return a JSON list of objects with fields: project_id, score, reason"
        )
        return '\n'.join(prompt)

    def _llm_score_candidates(self, portfolio_project: dict, sub_projects: List[dict]) -> tuple[list[Candidate], str]:
        """Call the LLM and parse the response into Candidate objects. Only keep candidates with score > 70."""
        prompt = self._build_suggestion_prompt(portfolio_project, sub_projects)
        logger.info(f"LLM prompt for suggestion pipeline:\n{prompt}")
        try:
            llm_response = generation_pipeline.generate(prompt)
        except TypeError:
            llm_response = generation_pipeline.generate(prompt)
        try:
            # Try parsing as a JSON array first
            raw_candidates = json.loads(llm_response)
            if isinstance(raw_candidates, dict):
                raw_candidates = [raw_candidates]
        except Exception:
            # Try parsing as multiple JSON objects separated by newlines
            raw_candidates = []
            for line in llm_response.splitlines():
                line = line.strip()
                if line:
                    try:
                        obj = json.loads(line)
                        raw_candidates.append(obj)
                    except Exception:
                        continue
            if not raw_candidates:
                logger.error(f"Failed to parse LLM response as JSON: {llm_response}")
                candidates = self._parse_candidates_from_text(llm_response, sub_projects)
                candidates = [c for c in candidates if c.score is not None and c.score > 70]
                return candidates, llm_response
        candidates = [self._dict_to_candidate(c, sub_projects) for c in raw_candidates]
        candidates = [c for c in candidates if c.score is not None and c.score > 70]
        return candidates, llm_response

    def _dict_to_candidate(self, c: dict, sub_projects: List[dict]) -> Candidate:
        """Convert a dict (from LLM JSON) to a Candidate object, matching project_id to sub-projects."""
        sp = next((sp for sp in sub_projects if str(sp.get("id")) == str(c.get("id", c.get("project_id")))), None)
        project_id_out = str(sp.get("id")) if sp and sp.get("id") is not None else str(c.get("id", c.get("project_id", "")))
        name = str(sp.get("name")) if sp and sp.get("name") is not None else f"ID {project_id_out}"
        score = None
        score_val = c.get("score")
        if score_val is not None:
            try:
                score_val_str = str(score_val).strip()
                if score_val_str and score_val_str.lower() != 'none':
                    score = float(score_val_str)
            except Exception:
                score = None
        reason = str(c.get("reason", ""))
        return Candidate(project_id=project_id_out, name=name, score=score, reason=reason)

    def _parse_candidates_from_text(self, text: str, sub_projects: List[dict]) -> List[Candidate]:
        """Attempt to extract candidate info from a text block if LLM did not return JSON."""
        candidates = []
        pattern = re.compile(r"(?P<idx>\d+)\.\s*(?P<name>[^\n]+)\n\s*- project_id: (?P<project_id>\d+)\n\s*- score: (?P<score>[\d\.]+)\n\s*- reason: (?P<reason>.+?)(?=\n\d+\.|$)", re.DOTALL)
        for match in pattern.finditer(text):
            project_id = str(match.group("project_id")) if match.group("project_id") is not None else ""
            parsed_name = str(match.group("name")).strip() if match.group("name") is not None else "Unknown"
            sp = next((sp for sp in sub_projects if str(sp.get("id")) == project_id), None)
            if sp and sp.get("name") is not None:
                name = str(sp.get("name"))
                project_id_out = str(sp.get("id"))
            else:
                # Try fuzzy match by name if project_id fails
                name = None
                project_id_out = project_id
                for s in sub_projects:
                    s_name = str(s.get("name", ""))
                    if parsed_name.lower() in s_name.lower() or s_name.lower() in parsed_name.lower():
                        name = s_name
                        project_id_out = str(s.get("id", ""))
                        break
                if not name:
                    name = parsed_name
                logger.warning(f"No sub-project found for project_id {project_id}. Using parsed name '{parsed_name}'.")
            score_val = match.group("score")
            score = None
            try:
                if isinstance(score_val, (int, float)):
                    score = float(score_val)
                elif isinstance(score_val, str):
                    score_val_str = score_val.strip()
                    if score_val_str and score_val_str.lower() != 'none':
                        score = float(score_val_str)
                elif score_val is not None:
                    score_val_str = str(score_val).strip()
                    if score_val_str and score_val_str.lower() != 'none':
                        score = float(score_val_str)
            except Exception:
                score = None
            reason_val = match.group("reason")
            reason = str(reason_val).strip() if reason_val is not None else ""
            candidates.append(Candidate(project_id=project_id_out, name=name, score=score, reason=reason))
        candidates.sort(key=lambda x: (x.score is not None, x.score), reverse=True)
        return candidates

    def _candidate_to_dict(self, c: Candidate) -> dict:
        """Convert a Candidate dataclass to a dict for API response. Include name, project_id, score, and reason."""
        return {
            "name": c.name,
            "score": c.score,
            "project_id": c.project_id,
            "reason": c.reason
        }

# Global pipeline instance for import convenience
pipeline = SuggestionPipeline(OpenProjectClient(settings.OPENPROJECT_BASE_URL, settings.OPENPROJECT_API_KEY))
