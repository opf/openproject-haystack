"""Report templates for project status report generation."""

from typing import List, Dict, Any, Tuple
from src.models.schemas import WorkPackage
from datetime import datetime, timedelta, timezone
import json
import logging

logger = logging.getLogger(__name__)


class ProjectReportAnalyzer:
    """Analyzer for work package data to extract insights."""
    
    @staticmethod
    def analyze_work_packages(work_packages: List[WorkPackage]) -> Dict[str, Any]:
        """Analyze work packages and extract key metrics.
        
        Args:
            work_packages: List of work packages to analyze
            
        Returns:
            Dictionary containing analysis results
        """
        if not work_packages:
            return {
                "total_count": 0,
                "status_distribution": {},
                "priority_distribution": {},
                "completion_stats": {},
                "assignee_workload": {},
                "timeline_insights": {},
                "key_metrics": {}
            }
        
        # Basic counts
        total_count = len(work_packages)
        
        # Status distribution
        status_distribution = {}
        for wp in work_packages:
            status_name = wp.status.get("name", "Unknown") if wp.status else "Unknown"
            status_distribution[status_name] = status_distribution.get(status_name, 0) + 1
        
        # Priority distribution
        priority_distribution = {}
        for wp in work_packages:
            priority_name = wp.priority.get("name", "No Priority") if wp.priority else "No Priority"
            priority_distribution[priority_name] = priority_distribution.get(priority_name, 0) + 1
        
        # Completion statistics
        completion_ratios = [wp.done_ratio for wp in work_packages if wp.done_ratio is not None]
        avg_completion = sum(completion_ratios) / len(completion_ratios) if completion_ratios else 0
        completed_count = sum(1 for wp in work_packages if wp.done_ratio == 100)
        in_progress_count = sum(1 for wp in work_packages if wp.done_ratio and 0 < wp.done_ratio < 100)
        not_started_count = sum(1 for wp in work_packages if not wp.done_ratio or wp.done_ratio == 0)
        
        completion_stats = {
            "average_completion": round(avg_completion, 1),
            "completed": completed_count,
            "in_progress": in_progress_count,
            "not_started": not_started_count
        }
        
        # Assignee workload
        assignee_workload = {}
        for wp in work_packages:
            assignee_name = wp.assignee.get("name", "Unassigned") if wp.assignee else "Unassigned"
            if assignee_name not in assignee_workload:
                assignee_workload[assignee_name] = {"total": 0, "completed": 0, "in_progress": 0}
            
            assignee_workload[assignee_name]["total"] += 1
            if wp.done_ratio == 100:
                assignee_workload[assignee_name]["completed"] += 1
            elif wp.done_ratio and wp.done_ratio > 0:
                assignee_workload[assignee_name]["in_progress"] += 1
        
        # Timeline insights
        now = datetime.now()
        overdue_count = 0
        upcoming_deadlines = 0
        
        for wp in work_packages:
            if wp.due_date:
                try:
                    due_date = datetime.fromisoformat(wp.due_date.replace('Z', '+00:00'))
                    if due_date < now and wp.done_ratio != 100:
                        overdue_count += 1
                    elif due_date <= now + timedelta(days=7) and wp.done_ratio != 100:
                        upcoming_deadlines += 1
                except (ValueError, TypeError):
                    continue
        
        timeline_insights = {
            "overdue_items": overdue_count,
            "upcoming_deadlines_7_days": upcoming_deadlines
        }
        
        # Key metrics
        key_metrics = {
            "completion_rate": round((completed_count / total_count) * 100, 1) if total_count > 0 else 0,
            "active_work_ratio": round(((in_progress_count + completed_count) / total_count) * 100, 1) if total_count > 0 else 0,
            "team_members": len([k for k in assignee_workload.keys() if k != "Unassigned"])
        }
        
        return {
            "total_count": total_count,
            "status_distribution": status_distribution,
            "priority_distribution": priority_distribution,
            "completion_stats": completion_stats,
            "assignee_workload": assignee_workload,
            "timeline_insights": timeline_insights,
            "key_metrics": key_metrics
        }


class ProjectManagementAnalyzer:
    """Analyzer that implements the 10 automated project management checks."""
    
    def __init__(self):
        """Initialize the analyzer."""
        self.checks_performed = 0
    
    async def perform_all_checks(
        self,
        work_packages: List[WorkPackage],
        relations: List[Dict[str, Any]] = None,
        time_entries: List[Dict[str, Any]] = None,
        users: List[Dict[str, Any]] = None,
        journals_data: Dict[int, List[Dict[str, Any]]] = None,
        attachments_data: Dict[int, List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Perform all 10 automated checks and return results.
        
        Args:
            work_packages: List of work packages
            relations: List of work package relations
            time_entries: List of time entries
            users: List of users
            journals_data: Dictionary mapping work package ID to journals
            attachments_data: Dictionary mapping work package ID to attachments
            
        Returns:
            Dictionary containing all check results
        """
        logger.info("Performing all 10 project management checks")
        
        results = {}
        self.checks_performed = 0
        
        # 1. Deadline Health
        results["deadline_health"] = self._check_deadline_health(work_packages)
        self.checks_performed += 1
        
        # 2. Missing Dates
        results["missing_dates"] = self._check_missing_dates(work_packages)
        self.checks_performed += 1
        
        # 3. Progress vs Plan Drift
        results["progress_drift"] = self._check_progress_drift(work_packages)
        self.checks_performed += 1
        
        # 4. Resource Load Balance
        results["resource_balance"] = self._check_resource_balance(work_packages, users or [])
        self.checks_performed += 1
        
        # 5. Dependency Conflicts
        results["dependency_conflicts"] = self._check_dependency_conflicts(work_packages, relations or [])
        self.checks_performed += 1
        
        # 6. Budget vs Actuals
        results["budget_actuals"] = self._check_budget_actuals(work_packages, time_entries or [])
        self.checks_performed += 1
        
        # 7. Unaddressed Risks & Issues
        results["risks_issues"] = self._check_risks_issues(work_packages)
        self.checks_performed += 1
        
        # 8. Stakeholder Responsiveness
        results["stakeholder_responsiveness"] = self._check_stakeholder_responsiveness(work_packages, journals_data or {})
        self.checks_performed += 1
        
        # 9. Scope Creep Monitor
        results["scope_creep"] = self._check_scope_creep(work_packages)
        self.checks_performed += 1
        
        # 10. Documentation Completeness
        results["documentation_completeness"] = self._check_documentation_completeness(work_packages, attachments_data or {})
        self.checks_performed += 1
        
        logger.info(f"Completed {self.checks_performed} project management checks")
        return results
    
    def _check_deadline_health(self, work_packages: List[WorkPackage]) -> Dict[str, Any]:
        """Check 1: Deadline Health - Flags overdue work packages."""
        now = datetime.now(timezone.utc)
        overdue_items = []
        upcoming_deadlines = []
        
        for wp in work_packages:
            if wp.due_date and wp.done_ratio != 100:
                try:
                    due_date = datetime.fromisoformat(wp.due_date.replace('Z', '+00:00'))
                    if due_date < now:
                        overdue_items.append({
                            "id": wp.id,
                            "subject": wp.subject,
                            "due_date": wp.due_date,
                            "assignee": wp.assignee.get("name") if wp.assignee else "Unassigned",
                            "days_overdue": (now - due_date).days
                        })
                    elif due_date <= now + timedelta(days=7):
                        upcoming_deadlines.append({
                            "id": wp.id,
                            "subject": wp.subject,
                            "due_date": wp.due_date,
                            "assignee": wp.assignee.get("name") if wp.assignee else "Unassigned",
                            "days_until_due": (due_date - now).days
                        })
                except (ValueError, TypeError):
                    continue
        
        return {
            "overdue_count": len(overdue_items),
            "overdue_items": overdue_items,
            "upcoming_deadlines_count": len(upcoming_deadlines),
            "upcoming_deadlines": upcoming_deadlines,
            "severity": "critical" if len(overdue_items) > 0 else "warning" if len(upcoming_deadlines) > 0 else "ok"
        }
    
    def _check_missing_dates(self, work_packages: List[WorkPackage]) -> Dict[str, Any]:
        """Check 2: Missing Dates - Lists items without start/due dates."""
        missing_dates = []
        
        for wp in work_packages:
            issues = []
            if not wp.due_date:
                issues.append("missing_due_date")
            # Note: OpenProject API doesn't always expose startDate in basic work package data
            # This would need to be enhanced if start dates are available
            
            if issues:
                missing_dates.append({
                    "id": wp.id,
                    "subject": wp.subject,
                    "type": wp.status.get("name") if wp.status else "Unknown",
                    "assignee": wp.assignee.get("name") if wp.assignee else "Unassigned",
                    "issues": issues
                })
        
        return {
            "missing_dates_count": len(missing_dates),
            "missing_dates_items": missing_dates,
            "severity": "warning" if len(missing_dates) > 0 else "ok"
        }
    
    def _check_progress_drift(self, work_packages: List[WorkPackage]) -> Dict[str, Any]:
        """Check 3: Progress vs Plan Drift - Compares actual vs planned progress."""
        drift_items = []
        total_packages = len(work_packages)
        
        if total_packages == 0:
            return {"drift_count": 0, "drift_items": [], "severity": "ok"}
        
        # Calculate expected progress based on time elapsed
        now = datetime.now(timezone.utc)
        
        for wp in work_packages:
            if wp.due_date and wp.created_at:
                try:
                    created_date = datetime.fromisoformat(wp.created_at.replace('Z', '+00:00'))
                    due_date = datetime.fromisoformat(wp.due_date.replace('Z', '+00:00'))
                    
                    total_duration = (due_date - created_date).total_seconds()
                    elapsed_duration = (now - created_date).total_seconds()
                    
                    if total_duration > 0:
                        expected_progress = min(100, (elapsed_duration / total_duration) * 100)
                        actual_progress = wp.done_ratio or 0
                        drift = expected_progress - actual_progress
                        
                        if drift > 20:  # More than 20% behind expected progress
                            drift_items.append({
                                "id": wp.id,
                                "subject": wp.subject,
                                "expected_progress": round(expected_progress, 1),
                                "actual_progress": actual_progress,
                                "drift_percentage": round(drift, 1),
                                "assignee": wp.assignee.get("name") if wp.assignee else "Unassigned"
                            })
                except (ValueError, TypeError):
                    continue
        
        return {
            "drift_count": len(drift_items),
            "drift_items": drift_items,
            "severity": "critical" if len(drift_items) > total_packages * 0.3 else "warning" if len(drift_items) > 0 else "ok"
        }
    
    def _check_resource_balance(self, work_packages: List[WorkPackage], users: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Check 4: Resource Load Balance - Checks user workload distribution."""
        user_workload = {}
        unassigned_count = 0
        
        for wp in work_packages:
            if wp.assignee:
                user_id = wp.assignee.get("id")
                user_name = wp.assignee.get("name")
                
                if user_id not in user_workload:
                    user_workload[user_id] = {
                        "name": user_name,
                        "total_tasks": 0,
                        "completed_tasks": 0,
                        "in_progress_tasks": 0,
                        "overdue_tasks": 0
                    }
                
                user_workload[user_id]["total_tasks"] += 1
                
                if wp.done_ratio == 100:
                    user_workload[user_id]["completed_tasks"] += 1
                elif wp.done_ratio and wp.done_ratio > 0:
                    user_workload[user_id]["in_progress_tasks"] += 1
                
                # Check if overdue
                if wp.due_date and wp.done_ratio != 100:
                    try:
                        due_date = datetime.fromisoformat(wp.due_date.replace('Z', '+00:00'))
                        if due_date < datetime.now(timezone.utc):
                            user_workload[user_id]["overdue_tasks"] += 1
                    except (ValueError, TypeError):
                        pass
            else:
                unassigned_count += 1
        
        # Identify overloaded users (more than 10 active tasks)
        overloaded_users = []
        for user_id, workload in user_workload.items():
            active_tasks = workload["total_tasks"] - workload["completed_tasks"]
            if active_tasks > 10:
                overloaded_users.append({
                    "user_id": user_id,
                    "name": workload["name"],
                    "active_tasks": active_tasks,
                    "overdue_tasks": workload["overdue_tasks"]
                })
        
        return {
            "user_workload": user_workload,
            "unassigned_count": unassigned_count,
            "overloaded_users": overloaded_users,
            "severity": "warning" if len(overloaded_users) > 0 or unassigned_count > 5 else "ok"
        }
    
    def _check_dependency_conflicts(self, work_packages: List[WorkPackage], relations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Check 5: Dependency Conflicts - Looks for relation conflicts."""
        conflicts = []
        
        # Create a map of work packages for quick lookup
        wp_map = {wp.id: wp for wp in work_packages}
        
        for relation in relations:
            try:
                relation_type = relation.get("type")
                from_id = relation.get("from", {}).get("id") if relation.get("from") else None
                to_id = relation.get("to", {}).get("id") if relation.get("to") else None
                
                if not from_id or not to_id or relation_type != "precedes":
                    continue
                
                from_wp = wp_map.get(from_id)
                to_wp = wp_map.get(to_id)
                
                if not from_wp or not to_wp:
                    continue
                
                # Check if follower starts before predecessor finishes
                if from_wp.due_date and to_wp.created_at:
                    try:
                        from_due = datetime.fromisoformat(from_wp.due_date.replace('Z', '+00:00'))
                        to_start = datetime.fromisoformat(to_wp.created_at.replace('Z', '+00:00'))
                        
                        if to_start < from_due and from_wp.done_ratio != 100:
                            conflicts.append({
                                "predecessor_id": from_id,
                                "predecessor_subject": from_wp.subject,
                                "follower_id": to_id,
                                "follower_subject": to_wp.subject,
                                "conflict_type": "start_before_predecessor_finish"
                            })
                    except (ValueError, TypeError):
                        continue
                        
            except Exception as e:
                logger.warning(f"Error processing relation: {e}")
                continue
        
        return {
            "conflicts_count": len(conflicts),
            "conflicts": conflicts,
            "severity": "critical" if len(conflicts) > 0 else "ok"
        }
    
    def _check_budget_actuals(self, work_packages: List[WorkPackage], time_entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Check 6: Budget vs Actuals - Compares spent vs estimated time."""
        budget_issues = []
        total_estimated = 0
        total_spent = 0
        
        # Calculate spent time per work package
        spent_by_wp = {}
        for entry in time_entries:
            wp_id = entry.get("workPackage", {}).get("id") if entry.get("workPackage") else None
            hours = entry.get("hours", 0)
            
            if wp_id:
                spent_by_wp[wp_id] = spent_by_wp.get(wp_id, 0) + hours
        
        for wp in work_packages:
            estimated_time = wp.done_ratio  # This would need to be enhanced with actual estimated time field
            spent_time = spent_by_wp.get(wp.id, 0)
            
            if estimated_time and spent_time > estimated_time * 1.2:  # 20% over budget
                budget_issues.append({
                    "id": wp.id,
                    "subject": wp.subject,
                    "estimated_hours": estimated_time,
                    "spent_hours": spent_time,
                    "over_budget_percentage": round(((spent_time - estimated_time) / estimated_time) * 100, 1),
                    "assignee": wp.assignee.get("name") if wp.assignee else "Unassigned"
                })
            
            total_estimated += estimated_time or 0
            total_spent += spent_time
        
        return {
            "budget_issues_count": len(budget_issues),
            "budget_issues": budget_issues,
            "total_estimated_hours": total_estimated,
            "total_spent_hours": total_spent,
            "overall_budget_status": "over" if total_spent > total_estimated * 1.1 else "on_track",
            "severity": "critical" if len(budget_issues) > 0 else "ok"
        }
    
    def _check_risks_issues(self, work_packages: List[WorkPackage]) -> Dict[str, Any]:
        """Check 7: Unaddressed Risks & Issues - Finds open risks/bugs past due date."""
        unaddressed_items = []
        
        for wp in work_packages:
            wp_type = wp.status.get("name", "").lower() if wp.status else ""
            
            # Check if it's a risk or bug type work package
            if any(keyword in wp_type for keyword in ["risk", "bug", "issue", "problem"]):
                # Check if it's still open and past due date
                if wp.done_ratio != 100:
                    is_overdue = False
                    if wp.due_date:
                        try:
                            due_date = datetime.fromisoformat(wp.due_date.replace('Z', '+00:00'))
                            is_overdue = due_date < datetime.now(timezone.utc)
                        except (ValueError, TypeError):
                            pass
                    
                    # Include if overdue or has no assignee
                    if is_overdue or not wp.assignee:
                        unaddressed_items.append({
                            "id": wp.id,
                            "subject": wp.subject,
                            "type": wp_type,
                            "due_date": wp.due_date,
                            "assignee": wp.assignee.get("name") if wp.assignee else "Unassigned",
                            "issue_type": "overdue" if is_overdue else "no_assignee"
                        })
        
        return {
            "unaddressed_count": len(unaddressed_items),
            "unaddressed_items": unaddressed_items,
            "severity": "critical" if len(unaddressed_items) > 0 else "ok"
        }
    
    def _check_stakeholder_responsiveness(self, work_packages: List[WorkPackage], journals_data: Dict[int, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """Check 8: Stakeholder Responsiveness - Highlights stale discussions."""
        stale_discussions = []
        threshold_days = 7
        now = datetime.now(timezone.utc)
        
        for wp in work_packages:
            journals = journals_data.get(wp.id, [])
            
            if journals:
                # Find the most recent journal entry
                latest_activity = None
                for journal in journals:
                    try:
                        created_at = datetime.fromisoformat(journal.get("createdAt", "").replace('Z', '+00:00'))
                        if not latest_activity or created_at > latest_activity:
                            latest_activity = created_at
                    except (ValueError, TypeError):
                        continue
                
                if latest_activity:
                    days_since_activity = (now - latest_activity).days
                    if days_since_activity > threshold_days and wp.done_ratio != 100:
                        stale_discussions.append({
                            "id": wp.id,
                            "subject": wp.subject,
                            "last_activity": latest_activity.isoformat(),
                            "days_since_activity": days_since_activity,
                            "assignee": wp.assignee.get("name") if wp.assignee else "Unassigned"
                        })
            else:
                # No activity at all - also concerning for active work packages
                if wp.done_ratio != 100:
                    stale_discussions.append({
                        "id": wp.id,
                        "subject": wp.subject,
                        "last_activity": None,
                        "days_since_activity": None,
                        "assignee": wp.assignee.get("name") if wp.assignee else "Unassigned"
                    })
        
        return {
            "stale_count": len(stale_discussions),
            "stale_discussions": stale_discussions,
            "severity": "warning" if len(stale_discussions) > 0 else "ok"
        }
    
    def _check_scope_creep(self, work_packages: List[WorkPackage]) -> Dict[str, Any]:
        """Check 9: Scope Creep Monitor - Detects increases in estimated effort."""
        scope_creep_items = []
        recent_additions = []
        
        # Check for recently created work packages (potential scope creep)
        now = datetime.now(timezone.utc)
        baseline_date = now - timedelta(days=30)  # Consider last 30 days as recent
        
        for wp in work_packages:
            try:
                created_date = datetime.fromisoformat(wp.created_at.replace('Z', '+00:00'))
                if created_date > baseline_date:
                    recent_additions.append({
                        "id": wp.id,
                        "subject": wp.subject,
                        "created_date": wp.created_at,
                        "assignee": wp.assignee.get("name") if wp.assignee else "Unassigned"
                    })
            except (ValueError, TypeError):
                continue
        
        # Note: Detecting actual scope creep would require historical data
        # This is a simplified version that flags recent additions
        
        return {
            "recent_additions_count": len(recent_additions),
            "recent_additions": recent_additions,
            "scope_creep_items": scope_creep_items,
            "severity": "warning" if len(recent_additions) > 5 else "ok"
        }
    
    def _check_documentation_completeness(self, work_packages: List[WorkPackage], attachments_data: Dict[int, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """Check 10: Documentation Completeness - Lists tasks lacking description or attachments."""
        incomplete_docs = []
        
        for wp in work_packages:
            issues = []
            
            # Check for missing or empty description
            if not wp.description or not wp.description.get("raw", "").strip():
                issues.append("missing_description")
            
            # Check for missing attachments (for certain types of work packages)
            attachments = attachments_data.get(wp.id, [])
            if len(attachments) == 0:
                # Only flag as issue for certain types that typically need attachments
                wp_type = wp.status.get("name", "").lower() if wp.status else ""
                if any(keyword in wp_type for keyword in ["design", "specification", "requirement", "documentation"]):
                    issues.append("missing_attachments")
            
            if issues:
                incomplete_docs.append({
                    "id": wp.id,
                    "subject": wp.subject,
                    "type": wp.status.get("name") if wp.status else "Unknown",
                    "assignee": wp.assignee.get("name") if wp.assignee else "Unassigned",
                    "issues": issues,
                    "attachments_count": len(attachments)
                })
        
        return {
            "incomplete_count": len(incomplete_docs),
            "incomplete_items": incomplete_docs,
            "severity": "warning" if len(incomplete_docs) > 0 else "ok"
        }


class ProjectStatusReportTemplate:
    """Template for generating project status reports."""
    
    @staticmethod
    def get_default_template() -> str:
        """Get the default project status report template.
        
        Returns:
            Template string for LLM prompt
        """
        return """
Sie sind ein Experte für Projektmanagement und erstellen einen umfassenden Projektstatusbericht basierend auf Arbeitspaket-Daten aus OpenProject.

Basierend auf den folgenden Projektdaten und Analysen, erstellen Sie einen professionellen Projektstatusbericht:

PROJEKTINFORMATIONEN:
- Projekt-ID: {project_id}
- OpenProject URL: {openproject_base_url}
- Bericht erstellt: {generated_at}
- Analysierte Arbeitspakete gesamt: {total_work_packages}

ARBEITSPAKET-ANALYSE:
{analysis_data}

ARBEITSPAKET-DETAILS:
{work_packages_summary}

Bitte erstellen Sie einen umfassenden Projektstatusbericht, der folgende Punkte enthält:

1. **Zusammenfassung**
   - Gesamtbewertung der Projektgesundheit
   - Wichtige Erfolge und Fortschrittshighlights
   - Kritische Probleme oder identifizierte Risiken

2. **Arbeitspaket-Statistiken**
   - Gesamtzahl der Arbeitspakete und deren Verteilung nach Status
   - Fertigstellungsgrad und Fortschrittsmetriken
   - Prioritätsaufschlüsselung und Schwerpunktbereiche

3. **Teamleistung**
   - Arbeitsbelastungsverteilung unter den Teammitgliedern
   - Individuelle und Team-Produktivitätseinblicke
   - Beobachtungen zur Ressourcenzuteilung

4. **Zeitplan und Fristen**
   - Überfällige Punkte und deren Auswirkungen
   - Anstehende Fristen und Prioritäten
   - Bewertung der Termintreue

5. **Empfehlungen**
   - Umsetzbare Schritte zur Verbesserung der Projektgesundheit
   - Risikominderungsstrategien
   - Vorschläge zur Ressourcenumverteilung falls erforderlich

6. **Nächste Schritte**
   - Sofort erforderliche Maßnahmen
   - Mittelfristige Planungsüberlegungen
   - Zu überwachende Erfolgsmetriken

Formatieren Sie den Bericht professionell, klar und umsetzbar. Verwenden Sie Aufzählungspunkte und strukturierte Abschnitte für eine einfache Lesbarkeit. Konzentrieren Sie sich auf Erkenntnisse, die für Projektmanager und Stakeholder wertvoll wären.

**WICHTIG: Antworten Sie vollständig auf Deutsch und verwenden Sie deutsche Projektmanagement-Terminologie.**
"""
    
    @staticmethod
    def format_work_packages_summary(work_packages: List[WorkPackage], limit: int = 10) -> str:
        """Format work packages into a summary for the report.
        
        Args:
            work_packages: List of work packages
            limit: Maximum number of work packages to include in detail
            
        Returns:
            Formatted string summary
        """
        if not work_packages:
            return "No work packages found for this project."
        
        summary_lines = []
        
        # Show top work packages (by priority or recent updates)
        sorted_packages = sorted(
            work_packages, 
            key=lambda wp: (
                wp.priority.get("id", 0) if wp.priority else 0,
                wp.updated_at
            ), 
            reverse=True
        )
        
        summary_lines.append(f"Top {min(limit, len(work_packages))} Work Packages:")
        
        for i, wp in enumerate(sorted_packages[:limit], 1):
            status_name = wp.status.get("name", "Unknown") if wp.status else "Unknown"
            priority_name = wp.priority.get("name", "Normal") if wp.priority else "Normal"
            assignee_name = wp.assignee.get("name", "Unassigned") if wp.assignee else "Unassigned"
            completion = wp.done_ratio if wp.done_ratio is not None else 0
            
            summary_lines.append(
                f"{i}. [{wp.id}] {wp.subject}\n"
                f"   Status: {status_name} | Priority: {priority_name} | "
                f"Assignee: {assignee_name} | Progress: {completion}%"
            )
            
            if wp.due_date:
                summary_lines.append(f"   Due Date: {wp.due_date}")
        
        if len(work_packages) > limit:
            summary_lines.append(f"\n... and {len(work_packages) - limit} more work packages")
        
        return "\n".join(summary_lines)
    
    @staticmethod
    def create_report_prompt(
        project_id: str,
        openproject_base_url: str,
        work_packages: List[WorkPackage],
        analysis: Dict[str, Any]
    ) -> str:
        """Create the complete prompt for LLM report generation.
        
        Args:
            project_id: Project identifier
            openproject_base_url: Base URL of OpenProject instance
            work_packages: List of work packages
            analysis: Analysis results from ProjectReportAnalyzer
            
        Returns:
            Complete formatted prompt string
        """
        template = ProjectStatusReportTemplate.get_default_template()
        
        # Format analysis data as JSON for better structure
        analysis_json = json.dumps(analysis, indent=2, default=str)
        
        # Create work packages summary
        work_packages_summary = ProjectStatusReportTemplate.format_work_packages_summary(work_packages)
        
        return template.format(
            project_id=project_id,
            openproject_base_url=openproject_base_url,
            generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"),
            total_work_packages=len(work_packages),
            analysis_data=analysis_json,
            work_packages_summary=work_packages_summary
        )
    
    @staticmethod
    def create_enhanced_report_prompt(
        project_id: str,
        project_type: str,
        openproject_base_url: str,
        work_packages: List[WorkPackage],
        analysis: Dict[str, Any],
        pmflex_context: str
    ) -> str:
        """Create an enhanced prompt with PMFlex RAG context.
        
        Args:
            project_id: Project identifier
            project_type: Type of project (portfolio, program, project)
            openproject_base_url: Base URL of OpenProject instance
            work_packages: List of work packages
            analysis: Analysis results from ProjectReportAnalyzer
            pmflex_context: PMFlex context from RAG system
            
        Returns:
            Complete formatted prompt string with RAG enhancement
        """
        template = ProjectStatusReportTemplate.get_enhanced_template()
        
        # Format analysis data as JSON for better structure
        analysis_json = json.dumps(analysis, indent=2, default=str)
        
        # Create work packages summary
        work_packages_summary = ProjectStatusReportTemplate.format_work_packages_summary(work_packages)
        
        return template.format(
            project_id=project_id,
            project_type=project_type,
            openproject_base_url=openproject_base_url,
            generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"),
            total_work_packages=len(work_packages),
            analysis_data=analysis_json,
            work_packages_summary=work_packages_summary,
            pmflex_context=pmflex_context or "No PMFlex context available."
        )
    
    @staticmethod
    def get_enhanced_template() -> str:
        """Get the enhanced project status report template with PMFlex context.
        
        Returns:
            Template string for LLM prompt with RAG enhancement
        """
        return """
Sie sind ein Experte für Projektmanagement mit Spezialisierung auf die PMFlex-Methodik der deutschen Bundesverwaltung. Ihre Aufgabe ist es, einen umfassenden Projektstatusbericht (Projektstatusbericht) basierend auf Arbeitspaket-Daten aus OpenProject zu erstellen und dabei die offizielle deutsche PMFlex-Vorlage zu befolgen.

PROJEKTINFORMATIONEN:
- Projekt-ID: {project_id}
- Projekttyp: {project_type}
- OpenProject URL: {openproject_base_url}
- Bericht erstellt: {generated_at}
- Analysierte Arbeitspakete gesamt: {total_work_packages}

ARBEITSPAKET-ANALYSE:
{analysis_data}

ARBEITSPAKET-DETAILS:
{work_packages_summary}

PMFLEX-KONTEXT UND VORLAGEN:
{pmflex_context}

Basierend auf den Projektdaten, der Analyse und dem PMFlex-Methodikkontext oben, erstellen Sie einen Projektstatusbericht (Projektstatusbericht), der der offiziellen deutschen PMFlex-Vorlage folg und genau in dieser Reihenfolget erstellt wird:

### 1. **Zusammenfassung**
Beginnen Sie mit einem umfassenden Zusammenfassungsabsatz, der Folgendes enthält:
- Kurze Beschreibung des aktuellen Projektstatus
- Gesamtbewertung der Projektgesundheit nach PMFlex-Kriterien
- Wichtige Erfolge und Fortschrittshighlights aus der Berichtsperiode
- Kritische Probleme oder Risiken, die Aufmerksamkeit erfordern
- Gesamtentwicklung und Ausblick für das Projekt

### 2. **Statusübersicht**
Geben Sie eine Statusbewertung mit dem PMFlex-Ampelsystem an:
- **Gesamtstatus**: Bewerten Sie als "Im Plan" (Grün), "Teilweise kritisch" (Gelb) oder "Kritisch" (Rot)
- **Zeit (Zeitplan)**: Bewertung der Termintreue
- **Kosten**: Budget- und Kostenstatus (falls aus Arbeitspaket-Daten verfügbar)
- **Risiko**: Risikobewertung basierend auf der Arbeitspaket-Analyse

Geben Sie die Berichtsperiode basierend auf dem Zeitrahmen der Arbeitspaket-Daten an.

### 3. **Abgeschlossene Aktivitäten und Meilensteine**
Listen Sie abgeschlossene Arbeitspakete und Erfolge auf:
- Arbeitspakete, die während der Berichtsperiode abgeschlossen wurden (mit Fertigstellungsgrad = 100%)
- Erreichte wichtige Meilensteine
- Abgeschlossene bedeutende Liefergegenstände
- Durchlaufene Qualitätstore
- Verwenden Sie Aufzählungspunkte mit spezifischen Arbeitspaket-IDs und Titeln, wo verfügbar

### 4. **Nächste Aktivitäten und Meilensteine**
Skizzieren Sie anstehende Arbeiten und Prioritäten:
- Arbeitspakete, die für die nächste Periode geplant sind
- Anstehende Meilensteine und Fristen
- Aktivitäten auf dem kritischen Pfad
- Abhängigkeiten, die Aufmerksamkeit benötigen
- Ressourcenanforderungen für anstehende Aktivitäten
- Verwenden Sie Aufzählungspunkte mit spezifischen Arbeitspaket-IDs und Fälligkeitsterminen, wo verfügbar

### 5. **Entscheidungsbedarf**
Identifizieren Sie Probleme, die Entscheidungen oder Eskalation erfordern:
- Blockierte Arbeitspakete, die Management-Intervention benötigen
- Ressourcenkonflikte oder Kapazitätsprobleme
- Umfangsänderungen oder Anforderungsklärungen erforderlich
- Risikominderungsentscheidungen erforderlich
- Budget- oder Zeitplananpassungen erforderlich
- Ausstehende Stakeholder-Entscheidungen
- Verwenden Sie Aufzählungspunkte mit klaren Handlungspunkten und verantwortlichen Parteien

## Formatierungsanforderungen:
- Verwenden Sie durchgehend deutsche PMFlex-Terminologie
- Strukturieren Sie mit klaren Überschriften und Aufzählungspunkten
- Beziehen Sie spezifische Arbeitspaket-Referenzen ein, wo relevant
- Behalten Sie einen professionellen Ton bei, der für deutsche Bundesverwaltungsstandards geeignet ist
- Konzentrieren Sie sich auf umsetzbare Erkenntnisse und klare Statuskommunikation
- Stellen Sie die Einhaltung der PMFlex-Dokumentationsstandards sicher

Der Bericht sollte PMFlex-Prinzipien der Transparenz, Verantwortlichkeit und des systematischen Projektmanagement-Ansatzes widerspiegeln, der in der deutschen Bundesverwaltung verwendet wird. Priorisieren Sie Klarheit und umsetzbare Informationen für Projekt-Stakeholder und Governance-Gremien.

**WICHTIG: Antworten Sie vollständig auf Deutsch und verwenden Sie deutsche PMFlex-Terminologie und -Standards. Der gesamte Bericht muss in deutscher Sprache verfasst werden.**
"""
    
    @staticmethod
    def get_custom_template(template_name: str) -> str:
        """Get a custom report template by name.
        
        This method can be extended to support multiple report templates
        for different use cases or organizations.
        
        Args:
            template_name: Name of the template to retrieve
            
        Returns:
            Template string
            
        Raises:
            ValueError: If template name is not found
        """
        templates = {
            "default": ProjectStatusReportTemplate.get_default_template(),
            "executive": ProjectStatusReportTemplate._get_executive_template(),
            "detailed": ProjectStatusReportTemplate._get_detailed_template()
        }
        
        if template_name not in templates:
            raise ValueError(f"Template '{template_name}' not found. Available templates: {list(templates.keys())}")
        
        return templates[template_name]
    
    @staticmethod
    def _get_executive_template() -> str:
        """Executive-focused template with high-level insights."""
        return """
Erstellen Sie einen Projektstatusbericht auf Führungsebene mit Fokus auf strategische Erkenntnisse und Entscheidungen.

PROJEKTDATEN:
- Projekt-ID: {project_id}
- Arbeitspakete gesamt: {total_work_packages}
- Analyse: {analysis_data}

Schwerpunkt auf:
1. Strategische Projektgesundheitsbewertung
2. Wichtige Leistungsindikatoren
3. Effizienz der Ressourcenzuteilung
4. Risikobewertung und -minderung
5. Strategische Empfehlungen

Halten Sie den Bericht prägnant und fokussiert auf entscheidungsrelevante Erkenntnisse.

**WICHTIG: Antworten Sie vollständig auf Deutsch und verwenden Sie deutsche Projektmanagement-Terminologie.**
"""
    
    @staticmethod
    def _get_detailed_template() -> str:
        """Detailed template for comprehensive analysis."""
        return """
Erstellen Sie einen detaillierten Projektstatusbericht mit umfassender Analyse aller Aspekte.

PROJEKTDATEN:
- Projekt-ID: {project_id}
- Analyse: {analysis_data}
- Arbeitspakete: {work_packages_summary}

Fügen Sie detaillierte Abschnitte ein zu:
1. Umfassende Arbeitspaket-Analyse
2. Individuelle Teammitglieder-Leistung
3. Detaillierte Zeitplan-Analyse
4. Qualitätsmetriken und Trends
5. Detaillierte Risikobewertung
6. Umfassende Empfehlungen mit Umsetzungsschritten

Bieten Sie tiefgreifende Erkenntnisse, die für Projektmanager und Teamleiter geeignet sind.

**WICHTIG: Antworten Sie vollständig auf Deutsch und verwenden Sie deutsche Projektmanagement-Terminologie.**
"""


class ProjectManagementHintsTemplate:
    """Template for generating German project management hints."""
    
    @staticmethod
    def create_hints_prompt(
        project_id: str,
        project_type: str,
        openproject_base_url: str,
        checks_results: Dict[str, Any],
        pmflex_context: str
    ) -> str:
        """Create prompt for generating German project management hints.
        
        Args:
            project_id: Project identifier
            project_type: Type of project
            openproject_base_url: Base URL of OpenProject instance
            checks_results: Results from the 10 automated checks
            pmflex_context: PMFlex context from RAG system
            
        Returns:
            Complete formatted prompt string
        """
        template = ProjectManagementHintsTemplate.get_hints_template()
        
        # Format checks results as JSON for better structure
        checks_json = json.dumps(checks_results, indent=2, default=str)
        
        return template.format(
            project_id=project_id,
            project_type=project_type,
            openproject_base_url=openproject_base_url,
            generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"),
            checks_results=checks_json,
            pmflex_context=pmflex_context or "Kein PMFlex-Kontext verfügbar."
        )
    
    @staticmethod
    def get_hints_template() -> str:
        """Get the German project management hints template.
        
        Returns:
            Template string for LLM prompt
        """
        return """
Sie sind ein Experte für Projektmanagement mit Spezialisierung auf die PMFlex-Methodik der deutschen Bundesverwaltung. Ihre Aufgabe ist es, basierend auf den Ergebnissen von 10 automatisierten Projektprüfungen konkrete, umsetzbare Hinweise in deutscher Sprache zu generieren.

PROJEKTINFORMATIONEN:
- Projekt-ID: {project_id}
- Projekttyp: {project_type}
- OpenProject URL: {openproject_base_url}
- Generiert am: {generated_at}

ERGEBNISSE DER 10 AUTOMATISIERTEN PRÜFUNGEN:
{checks_results}

PMFLEX-KONTEXT UND METHODIK:
{pmflex_context}

Basierend auf den Prüfungsergebnissen und dem PMFlex-Kontext, generieren Sie konkrete Handlungsempfehlungen (Hinweise) für Projektmanager. Jeder Hinweis soll:

1. **Spezifisch und umsetzbar** sein
2. **PMFlex-Methodik** berücksichtigen
3. **Deutsche Bundesverwaltungsstandards** einhalten
4. **Priorität und Dringlichkeit** widerspiegeln

## HINWEISE-KATEGORIEN:

### KRITISCHE HINWEISE (Sofortiger Handlungsbedarf)
Für Ergebnisse mit "severity": "critical":
- Überfällige Arbeitspakete
- Abhängigkeitskonflikte
- Budgetüberschreitungen
- Unbearbeitete Risiken

### WARNHINWEISE (Kurzfristige Aufmerksamkeit erforderlich)
Für Ergebnisse mit "severity": "warning":
- Fehlende Termine
- Ressourcenungleichgewicht
- Veraltete Diskussionen
- Unvollständige Dokumentation

### OPTIMIERUNGSHINWEISE (Kontinuierliche Verbesserung)
Für Ergebnisse mit "severity": "ok" aber Verbesserungspotential:
- Prozessoptimierungen
- Präventive Maßnahmen
- Best-Practice-Empfehlungen

## AUSGABEFORMAT:

Generieren Sie die Hinweise im folgenden JSON-Format:

```json
{
  "hints": [
    {
      "checked": false,
      "title": "Überfällige Arbeitspakete priorisieren",
      "description": "Es wurden X überfällige Arbeitspakete identifiziert. Führen Sie umgehend Gespräche mit den Verantwortlichen und definieren Sie realistische neue Termine. Prüfen Sie, ob Arbeitspakete aufgeteilt werden müssen."
    },
    {
      "checked": false,
      "title": "Fehlende Fälligkeitstermine ergänzen",
      "description": "Y Arbeitspakete haben keine Fälligkeitstermine. Planen Sie diese zeitlich ein oder verschieben Sie sie in den Backlog, falls der Zeitpunkt unbekannt ist."
    }
  ],
  "summary": "Das Projekt zeigt insgesamt einen [Status] mit [Anzahl] kritischen und [Anzahl] Warnhinweisen. Schwerpunkt sollte auf der Terminplanung und Ressourcenverteilung liegen."
}
```

## SPEZIFISCHE ANWEISUNGEN:

1. **Titel**: Kurz und prägnant (max. 60 Zeichen)
2. **Beschreibung**: Konkrete Handlungsschritte mit Bezug zu den Prüfungsergebnissen
3. **PMFlex-Terminologie**: Verwenden Sie offizielle PMFlex-Begriffe
4. **Zahlen einbeziehen**: Referenzieren Sie spezifische Zahlen aus den Prüfungen
5. **Verantwortlichkeiten**: Nennen Sie, wer handeln sollte
6. **Zeitrahmen**: Geben Sie Dringlichkeit an (sofort, kurzfristig, mittelfristig)

## PRIORISIERUNG:
1. Kritische Sicherheits- und Compliance-Probleme
2. Terminrisiken und überfällige Aufgaben
3. Ressourcen- und Budgetprobleme
4. Kommunikations- und Dokumentationslücken
5. Prozessoptimierungen

Generieren Sie maximal 10 Hinweise, priorisiert nach Wichtigkeit und Dringlichkeit. Die Zusammenfassung soll den Gesamtzustand des Projekts widerspiegeln und die wichtigsten Handlungsfelder benennen.

## WICHTIGE AUSGABE-ANWEISUNGEN:

1. **NUR JSON**: Antworten Sie ausschließlich mit gültigem JSON
2. **KEINE ZUSÄTZLICHEN TEXTE**: Keine Erklärungen vor oder nach dem JSON
3. **VOLLSTÄNDIGE STRUKTUR**: Stellen Sie sicher, dass das JSON vollständig ist
4. **GÜLTIGE SYNTAX**: Verwenden Sie korrekte JSON-Syntax mit geschweiften Klammern

BEISPIEL DER ERWARTETEN AUSGABE:
```json
{
  "hints": [
    {
      "checked": false,
      "title": "Beispiel-Hinweis",
      "description": "Dies ist eine Beispielbeschreibung für einen Hinweis."
    }
  ],
  "summary": "Beispiel-Zusammenfassung des Projektstatus."
}
```

Beginnen Sie Ihre Antwort direkt mit { und enden Sie mit }. Keine anderen Zeichen oder Texte.
"""
