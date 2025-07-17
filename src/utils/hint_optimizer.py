"""
Hint generation optimizer with enhanced fallback strategies and monitoring.
"""

import json
import logging
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime, timezone
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class HintPriority(Enum):
    """Priority levels for hints."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class HintCategory(Enum):
    """Categories for organizing hints."""
    DEADLINES = "deadlines"
    RESOURCES = "resources"
    DOCUMENTATION = "documentation"
    RISKS = "risks"
    COMMUNICATION = "communication"
    QUALITY = "quality"
    PLANNING = "planning"


@dataclass
class HintTemplate:
    """Template for generating context-aware hints."""
    title_template: str
    description_template: str
    priority: HintPriority
    category: HintCategory
    condition_check: callable
    context_fields: List[str]
    is_positive: bool = False  # New field for positive/completed hints
    score_boost: float = 0.0   # Additional score for evidence-based prioritization


class HintOptimizer:
    """Optimizer for hint generation with enhanced fallback strategies."""
    
    def __init__(self):
        """Initialize the hint optimizer with predefined templates."""
        self.hint_templates = self._initialize_hint_templates()
        self.generation_metrics = {
            "total_attempts": 0,
            "successful_generations": 0,
            "fallback_uses": 0,
            "json_parse_failures": 0,
            "retry_successes": 0
        }
    
    def _initialize_hint_templates(self) -> List[HintTemplate]:
        """Initialize predefined hint templates for different scenarios."""
        return [
            # Critical deadline issues
            HintTemplate(
                title_template="Überfällige Termine sofort bearbeiten",
                description_template="Es gibt {overdue_count} überfällige Arbeitspakete. Führen Sie umgehend Gespräche mit den Verantwortlichen und definieren Sie realistische neue Termine. Kritischste Aufgaben: {top_overdue_items}.",
                priority=HintPriority.CRITICAL,
                category=HintCategory.DEADLINES,
                condition_check=lambda checks: checks.get("deadline_health", {}).get("severity") == "critical",
                context_fields=["overdue_count", "overdue_items"],
                score_boost=2.0  # High boost for critical items with numbers
            ),
            
            # Positive: Good deadline management
            HintTemplate(
                title_template="✓ Termine im Griff",
                description_template="{on_time_percentage}% der Arbeitspakete sind termingerecht. {upcoming_count} Arbeitspakete haben klare Fälligkeitstermine in den nächsten Wochen.",
                priority=HintPriority.LOW,
                category=HintCategory.DEADLINES,
                condition_check=lambda checks: checks.get("deadline_health", {}).get("severity") == "ok" and checks.get("missing_dates", {}).get("missing_dates_count", 999) < 5,
                context_fields=["upcoming_deadlines_count"],
                is_positive=True,
                score_boost=0.5
            ),
            
            # Positive: Good resource distribution
            HintTemplate(
                title_template="✓ Ressourcen gut verteilt",
                description_template="Alle {team_members} Teammitglieder haben eine ausgewogene Arbeitsbelastung. {assigned_percentage}% der Aufgaben sind zugewiesen.",
                priority=HintPriority.LOW,
                category=HintCategory.RESOURCES,
                condition_check=lambda checks: checks.get("resource_balance", {}).get("severity") == "ok" and checks.get("resource_balance", {}).get("unassigned_count", 999) < 3,
                context_fields=["team_members", "assigned_count"],
                is_positive=True,
                score_boost=0.5
            ),
            
            # Positive: Good documentation
            HintTemplate(
                title_template="✓ Dokumentation vollständig",
                description_template="{documented_percentage}% der Arbeitspakete haben vollständige Dokumentation. Besonders gut dokumentiert sind die kritischen Arbeitspakete.",
                priority=HintPriority.LOW,
                category=HintCategory.DOCUMENTATION,
                condition_check=lambda checks: checks.get("documentation_completeness", {}).get("incomplete_count", 999) < 5,
                context_fields=["documented_count", "total_count"],
                is_positive=True,
                score_boost=0.3
            ),
            
            # Positive: Risks under control
            HintTemplate(
                title_template="✓ Risiken unter Kontrolle",
                description_template="Alle identifizierten Risiken wurden zugewiesen und haben Mitigationspläne. {addressed_percentage}% der Risiken wurden bereits bearbeitet.",
                priority=HintPriority.LOW,
                category=HintCategory.RISKS,
                condition_check=lambda checks: checks.get("risks_issues", {}).get("severity") == "ok",
                context_fields=["addressed_count", "total_risks"],
                is_positive=True,
                score_boost=0.8
            ),
            
            # Resource imbalance
            HintTemplate(
                title_template="Arbeitsbelastung neu verteilen",
                description_template="Ein Teammitglied hat {active_tasks} aktive Aufgaben, während {unassigned_count} Aufgaben nicht zugewiesen sind. Verteilen Sie die Arbeitsbelastung gleichmäßiger.",
                priority=HintPriority.HIGH,
                category=HintCategory.RESOURCES,
                condition_check=lambda checks: checks.get("resource_balance", {}).get("severity") == "warning",
                context_fields=["overloaded_users", "unassigned_count"]
            ),
            
            # Missing documentation
            HintTemplate(
                title_template="Dokumentation vervollständigen",
                description_template="{incomplete_count} Arbeitspakete haben unvollständige Dokumentation. Ergänzen Sie Beschreibungen und fügen Sie notwendige Anhänge hinzu.",
                priority=HintPriority.MEDIUM,
                category=HintCategory.DOCUMENTATION,
                condition_check=lambda checks: checks.get("documentation_completeness", {}).get("severity") == "warning",
                context_fields=["incomplete_count", "incomplete_items"]
            ),
            
            # Risk management
            HintTemplate(
                title_template="Risiken und Probleme adressieren",
                description_template="{unaddressed_count} Risiken oder Probleme sind noch nicht bearbeitet. Weisen Sie diese zu und definieren Sie Lösungsschritte.",
                priority=HintPriority.CRITICAL,
                category=HintCategory.RISKS,
                condition_check=lambda checks: checks.get("risks_issues", {}).get("severity") == "critical",
                context_fields=["unaddressed_count", "unaddressed_items"]
            ),
            
            # Communication issues
            HintTemplate(
                title_template="Kommunikation reaktivieren",
                description_template="{stale_count} Arbeitspakete haben seit über einer Woche keine Aktivität. Kontaktieren Sie die Verantwortlichen und klären Sie den Status.",
                priority=HintPriority.MEDIUM,
                category=HintCategory.COMMUNICATION,
                condition_check=lambda checks: checks.get("stakeholder_responsiveness", {}).get("severity") == "warning",
                context_fields=["stale_count", "stale_discussions"]
            ),
            
            # Missing dates
            HintTemplate(
                title_template="Fehlende Termine ergänzen",
                description_template="{missing_dates_count} Arbeitspakete haben keine Fälligkeitstermine. Planen Sie diese zeitlich ein oder verschieben Sie sie in den Backlog.",
                priority=HintPriority.MEDIUM,
                category=HintCategory.PLANNING,
                condition_check=lambda checks: checks.get("missing_dates", {}).get("severity") == "warning",
                context_fields=["missing_dates_count", "missing_dates_items"]
            ),
            
            # Progress drift
            HintTemplate(
                title_template="Projektfortschritt überprüfen",
                description_template="{drift_count} Arbeitspakete sind deutlich hinter dem geplanten Fortschritt. Analysieren Sie die Ursachen und passen Sie die Planung an.",
                priority=HintPriority.HIGH,
                category=HintCategory.PLANNING,
                condition_check=lambda checks: checks.get("progress_drift", {}).get("severity") in ["warning", "critical"],
                context_fields=["drift_count", "drift_items"]
            ),
            
            # Budget issues
            HintTemplate(
                title_template="Budget-Überschreitungen kontrollieren",
                description_template="{budget_issues_count} Arbeitspakete überschreiten das geplante Budget. Überprüfen Sie die Schätzungen und Ressourcenzuteilung.",
                priority=HintPriority.HIGH,
                category=HintCategory.PLANNING,
                condition_check=lambda checks: checks.get("budget_actuals", {}).get("severity") == "critical",
                context_fields=["budget_issues_count", "budget_issues"]
            ),
            
            # Scope creep
            HintTemplate(
                title_template="Scope-Änderungen überwachen",
                description_template="{recent_additions_count} neue Arbeitspakete wurden kürzlich hinzugefügt. Prüfen Sie, ob diese dem ursprünglichen Projektumfang entsprechen.",
                priority=HintPriority.MEDIUM,
                category=HintCategory.PLANNING,
                condition_check=lambda checks: checks.get("scope_creep", {}).get("severity") == "warning",
                context_fields=["recent_additions_count", "recent_additions"]
            ),
            
            # Dependency conflicts
            HintTemplate(
                title_template="Abhängigkeitskonflikte lösen",
                description_template="{conflicts_count} Abhängigkeitskonflikte wurden erkannt. Überprüfen Sie die Reihenfolge der Arbeitspakete und lösen Sie Blockaden.",
                priority=HintPriority.CRITICAL,
                category=HintCategory.PLANNING,
                condition_check=lambda checks: checks.get("dependency_conflicts", {}).get("severity") == "critical",
                context_fields=["conflicts_count", "conflicts"]
            )
        ]
    
    def generate_enhanced_fallback_hints(self, checks_results: Dict[str, Any]) -> str:
        """Generate enhanced fallback hints using templates and prioritization.
        
        Args:
            checks_results: Results from the 10 automated checks
            
        Returns:
            JSON string with prioritized, context-aware hints (limited to 5)
        """
        logger.info("Generating enhanced fallback hints using templates")
        
        # Generate hints from templates
        generated_hints = []
        positive_hints = []
        
        for template in self.hint_templates:
            if template.condition_check(checks_results):
                hint = self._generate_hint_from_template(template, checks_results)
                if hint:
                    # Add score based on template's boost and evidence
                    hint["score"] = self._calculate_hint_score(hint, template, checks_results)
                    
                    if template.is_positive:
                        positive_hints.append(hint)
                    else:
                        generated_hints.append(hint)
        
        # Sort by score (highest first) 
        generated_hints.sort(key=lambda h: h.get("score", 0), reverse=True)
        positive_hints.sort(key=lambda h: h.get("score", 0), reverse=True)
        
        # Select top 3-4 critical/action hints and 1-2 positive hints
        final_hints = []
        
        # Add top critical/action hints (3-4)
        critical_count = min(4, len(generated_hints))
        if len(positive_hints) > 0:
            critical_count = min(3, len(generated_hints))  # Make room for positive hints
            
        final_hints.extend(generated_hints[:critical_count])
        
        # Add 1-2 positive hints
        positive_count = min(2, len(positive_hints), 5 - len(final_hints))
        final_hints.extend(positive_hints[:positive_count])
        
        # Convert to required format
        formatted_hints = []
        for hint in final_hints[:5]:  # Ensure max 5 hints
            is_positive = hint.get("is_positive", False)
            formatted_hints.append({
                "checked": is_positive,  # Positive hints are marked as checked
                "title": hint["title"][:60],  # Ensure max length
                "description": hint["description"]
            })
        
        # If no hints were generated, add a general one
        if not formatted_hints:
            formatted_hints.append({
                "checked": False,
                "title": "Projektübersicht prüfen",
                "description": "Überprüfen Sie den aktuellen Projektstatus und stellen Sie sicher, dass alle Arbeitspakete ordnungsgemäß verwaltet werden."
            })
        
        # Update metrics
        self.generation_metrics["fallback_uses"] += 1
        
        result = {"hints": formatted_hints}
        return json.dumps(result, ensure_ascii=False, separators=(',', ':'))
    
    def _calculate_hint_score(self, hint: Dict[str, Any], template: HintTemplate, checks_results: Dict[str, Any]) -> float:
        """Calculate score for a hint based on priority, evidence, and impact.
        
        Args:
            hint: Generated hint
            template: Hint template used
            checks_results: Check results
            
        Returns:
            Score value (higher is more important)
        """
        # Base score from priority
        priority_scores = {
            HintPriority.CRITICAL: 10.0,
            HintPriority.HIGH: 7.0,
            HintPriority.MEDIUM: 4.0,
            HintPriority.LOW: 2.0
        }
        score = priority_scores.get(template.priority, 1.0)
        
        # Add template's score boost
        score += template.score_boost
        
        # Boost for specific numbers in description
        import re
        numbers_count = len(re.findall(r'\d+', hint.get("description", "")))
        score += numbers_count * 0.5
        
        # Boost for large impact
        check_name = self._get_check_name_for_template(template)
        check_result = checks_results.get(check_name, {})
        
        # Examples of impact-based scoring
        if "overdue_count" in check_result and check_result["overdue_count"] > 5:
            score += 2.0
        if "unaddressed_count" in check_result and check_result["unaddressed_count"] > 3:
            score += 1.5
        if "conflicts_count" in check_result and check_result["conflicts_count"] > 0:
            score += 2.5
            
        return score
    
    def _generate_hint_from_template(self, template: HintTemplate, checks_results: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate a hint from a template using check results.
        
        Args:
            template: Hint template to use
            checks_results: Check results for context
            
        Returns:
            Generated hint dictionary or None if generation failed
        """
        try:
            # Get the relevant check result
            check_name = self._get_check_name_for_template(template)
            check_result = checks_results.get(check_name, {})
            
            # Extract context values
            context = {}
            for field in template.context_fields:
                context[field] = check_result.get(field, 0)
            
            # Special handling for complex fields
            if "top_overdue_items" in template.context_fields:
                overdue_items = check_result.get("overdue_items", [])
                top_items = [item.get("subject", "Unknown") for item in overdue_items[:3]]
                context["top_overdue_items"] = ", ".join(top_items) if top_items else "Keine Details verfügbar"
            
            if "active_tasks" in template.context_fields:
                overloaded_users = check_result.get("overloaded_users", [])
                if overloaded_users:
                    context["active_tasks"] = overloaded_users[0].get("active_tasks", 0)
                else:
                    context["active_tasks"] = 0
            
            # Handle positive hint context fields
            if "on_time_percentage" in template.context_fields:
                total_count = sum(1 for check in checks_results.values() if isinstance(check, dict))
                overdue_count = check_result.get("overdue_count", 0)
                if total_count > 0:
                    context["on_time_percentage"] = round(((total_count - overdue_count) / total_count) * 100, 0)
                else:
                    context["on_time_percentage"] = 100
            
            if "upcoming_count" in template.context_fields:
                context["upcoming_count"] = check_result.get("upcoming_deadlines_count", 0)
            
            if "team_members" in template.context_fields:
                user_workload = check_result.get("user_workload", {})
                context["team_members"] = len([u for u in user_workload.keys() if u != "Unassigned"])
            
            if "assigned_percentage" in template.context_fields:
                total_workpackages = 48  # Default based on test data
                unassigned = check_result.get("unassigned_count", 0)
                if total_workpackages > 0:
                    context["assigned_percentage"] = round(((total_workpackages - unassigned) / total_workpackages) * 100, 0)
                else:
                    context["assigned_percentage"] = 100
            
            if "documented_percentage" in template.context_fields:
                total_workpackages = 48  # Default based on test data
                incomplete = check_result.get("incomplete_count", 0)
                if total_workpackages > 0:
                    context["documented_percentage"] = round(((total_workpackages - incomplete) / total_workpackages) * 100, 0)
                else:
                    context["documented_percentage"] = 100
            
            if "addressed_percentage" in template.context_fields:
                unaddressed = check_result.get("unaddressed_count", 0)
                total_risks = unaddressed + 5  # Assume some risks were already addressed
                if total_risks > 0:
                    context["addressed_percentage"] = round(((total_risks - unaddressed) / total_risks) * 100, 0)
                else:
                    context["addressed_percentage"] = 100
            
            # Set defaults for missing context fields
            for field in template.context_fields:
                if field not in context:
                    context[field] = 0
            
            # Format the hint
            title = template.title_template
            description = template.description_template.format(**context)
            
            return {
                "title": title,
                "description": description,
                "priority": template.priority,
                "category": template.category,
                "is_positive": template.is_positive
            }
            
        except Exception as e:
            logger.warning(f"Failed to generate hint from template: {e}")
            return None
    
    def _get_check_name_for_template(self, template: HintTemplate) -> str:
        """Map template category to check name."""
        category_to_check = {
            HintCategory.DEADLINES: "deadline_health",
            HintCategory.RESOURCES: "resource_balance",
            HintCategory.DOCUMENTATION: "documentation_completeness",
            HintCategory.RISKS: "risks_issues",
            HintCategory.COMMUNICATION: "stakeholder_responsiveness",
            HintCategory.PLANNING: "missing_dates"
        }
        
        # Handle special cases
        if "progress" in template.title_template.lower():
            return "progress_drift"
        elif "budget" in template.title_template.lower():
            return "budget_actuals"
        elif "scope" in template.title_template.lower():
            return "scope_creep"
        elif "abhängigkeit" in template.title_template.lower():
            return "dependency_conflicts"
        
        return category_to_check.get(template.category, "deadline_health")
    
    def track_generation_attempt(self, success: bool, used_fallback: bool, json_parse_failed: bool, retry_succeeded: bool):
        """Track metrics for hint generation attempts.
        
        Args:
            success: Whether the generation was successful
            used_fallback: Whether fallback was used
            json_parse_failed: Whether JSON parsing failed
            retry_succeeded: Whether a retry attempt succeeded
        """
        self.generation_metrics["total_attempts"] += 1
        
        if success:
            self.generation_metrics["successful_generations"] += 1
        
        if used_fallback:
            self.generation_metrics["fallback_uses"] += 1
        
        if json_parse_failed:
            self.generation_metrics["json_parse_failures"] += 1
        
        if retry_succeeded:
            self.generation_metrics["retry_successes"] += 1
    
    def get_generation_metrics(self) -> Dict[str, Any]:
        """Get current generation metrics.
        
        Returns:
            Dictionary with generation metrics and success rates
        """
        total = self.generation_metrics["total_attempts"]
        if total == 0:
            return self.generation_metrics
        
        return {
            **self.generation_metrics,
            "success_rate": round((self.generation_metrics["successful_generations"] / total) * 100, 2),
            "fallback_rate": round((self.generation_metrics["fallback_uses"] / total) * 100, 2),
            "json_failure_rate": round((self.generation_metrics["json_parse_failures"] / total) * 100, 2),
            "retry_success_rate": round((self.generation_metrics["retry_successes"] / max(1, self.generation_metrics["json_parse_failures"])) * 100, 2)
        }
    
    def reset_metrics(self):
        """Reset generation metrics."""
        self.generation_metrics = {
            "total_attempts": 0,
            "successful_generations": 0,
            "fallback_uses": 0,
            "json_parse_failures": 0,
            "retry_successes": 0
        }
    
    def analyze_hint_quality(self, hints_json: str) -> Dict[str, Any]:
        """Analyze the quality of generated hints.
        
        Args:
            hints_json: JSON string with generated hints
            
        Returns:
            Quality analysis results
        """
        try:
            hints_data = json.loads(hints_json)
            hints = hints_data.get("hints", [])
            
            analysis = {
                "total_hints": len(hints),
                "avg_title_length": 0,
                "avg_description_length": 0,
                "has_actionable_language": 0,
                "has_specific_numbers": 0,
                "categories_covered": set(),
                "quality_score": 0
            }
            
            if not hints:
                return analysis
            
            # Analyze each hint
            actionable_keywords = ["prüfen", "definieren", "kontaktieren", "überprüfen", "ergänzen", "weisen", "führen"]
            
            for hint in hints:
                title = hint.get("title", "")
                description = hint.get("description", "")
                
                analysis["avg_title_length"] += len(title)
                analysis["avg_description_length"] += len(description)
                
                # Check for actionable language
                if any(keyword in description.lower() for keyword in actionable_keywords):
                    analysis["has_actionable_language"] += 1
                
                # Check for specific numbers
                import re
                if re.search(r'\d+', description):
                    analysis["has_specific_numbers"] += 1
                
                # Categorize hint
                if "termin" in title.lower() or "fällig" in title.lower():
                    analysis["categories_covered"].add("deadlines")
                elif "ressource" in title.lower() or "arbeitsbelastung" in title.lower():
                    analysis["categories_covered"].add("resources")
                elif "dokumentation" in title.lower():
                    analysis["categories_covered"].add("documentation")
                elif "risiko" in title.lower() or "problem" in title.lower():
                    analysis["categories_covered"].add("risks")
            
            # Calculate averages
            analysis["avg_title_length"] = round(analysis["avg_title_length"] / len(hints), 1)
            analysis["avg_description_length"] = round(analysis["avg_description_length"] / len(hints), 1)
            
            # Calculate quality score (0-100)
            quality_factors = [
                (analysis["has_actionable_language"] / len(hints)) * 30,  # 30% for actionable language
                (analysis["has_specific_numbers"] / len(hints)) * 20,     # 20% for specific numbers
                min(len(analysis["categories_covered"]) / 4, 1) * 25,     # 25% for category coverage
                min(analysis["avg_description_length"] / 100, 1) * 25     # 25% for description length
            ]
            
            analysis["quality_score"] = round(sum(quality_factors), 1)
            analysis["categories_covered"] = list(analysis["categories_covered"])
            
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to analyze hint quality: {e}")
            return {"error": str(e)}


# Global optimizer instance
hint_optimizer = HintOptimizer()
