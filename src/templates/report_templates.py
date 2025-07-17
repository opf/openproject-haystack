"""Report templates for project status report generation."""

from typing import List, Dict, Any
from src.api.schemas import WorkPackage
from datetime import datetime, timedelta
import json


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


class ProjectStatusReportTemplate:
    """Template for generating project status reports."""

    @staticmethod
    def get_default_template() -> str:
        """Get the default project status report template.

        Returns:
            Template string for LLM prompt
        """
        return """
You are a project management expert tasked with generating a comprehensive project status report based on work package data from OpenProject.

Based on the following project data and analysis, generate a professional project status report:

PROJECT INFORMATION:
- Project ID: {project_id}
- OpenProject URL: {openproject_base_url}
- Report Generated: {generated_at}
- Total Work Packages Analyzed: {total_work_packages}

WORK PACKAGE ANALYSIS:
{analysis_data}

WORK PACKAGE DETAILS:
{work_packages_summary}

Please generate a comprehensive project status report that includes:

1. **Executive Summary**
   - Overall project health assessment
   - Key achievements and progress highlights
   - Critical issues or risks identified

2. **Work Package Statistics**
   - Total work packages and their distribution by status
   - Completion rate and progress metrics
   - Priority breakdown and focus areas

3. **Team Performance**
   - Workload distribution among team members
   - Individual and team productivity insights
   - Resource allocation observations

4. **Timeline and Deadlines**
   - Overdue items and their impact
   - Upcoming deadlines and priorities
   - Schedule adherence assessment

5. **Recommendations**
   - Actionable steps to improve project health
   - Risk mitigation strategies
   - Resource reallocation suggestions if needed

6. **Next Steps**
   - Immediate actions required
   - Medium-term planning considerations
   - Success metrics to monitor

Format the report in a professional, clear, and actionable manner. Use bullet points and structured sections for easy readability. Focus on insights that would be valuable for project managers and stakeholders.
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
You are a project management expert specializing in the PMFlex methodology used by the German federal government. You are tasked with generating a comprehensive project status report (Projektstatusbericht) based on work package data from OpenProject, following the official German PMFlex template structure.

PROJECT INFORMATION:
- Project ID: {project_id}
- Project Type: {project_type}
- OpenProject URL: {openproject_base_url}
- Report Generated: {generated_at}
- Total Work Packages Analyzed: {total_work_packages}

WORK PACKAGE ANALYSIS:
{analysis_data}

WORK PACKAGE DETAILS:
{work_packages_summary}

PMFLEX CONTEXT AND TEMPLATES:
{pmflex_context}

Based on the project data, analysis, and PMFlex methodology context above, generate a project status report (Projektstatusbericht) that follows the official German PMFlex template structure:

## REPORT STRUCTURE (Generate in this exact order):

### 1. **ZUSAMMENFASSUNG (Summary)**
Start with a comprehensive summary paragraph that provides:
- Brief description of the current project status (Kurze Beschreibung des aktuellen Status des Projekts)
- Overall project health assessment according to PMFlex criteria
- Key achievements and progress highlights from the reporting period
- Critical issues or risks that require attention
- Overall trajectory and outlook for the project

### 2. **STATUSÜBERSICHT (Status Overview)**
Provide a status assessment using the PMFlex traffic light system:
- **Gesamtstatus (Overall Status)**: Assess as "Im Plan" (Green), "Teilweise kritisch" (Yellow), or "Kritisch" (Red)
- **Zeit (Time/Schedule)**: Schedule adherence assessment
- **Kosten (Costs)**: Budget and cost status (if available from work package data)
- **Risiko (Risk)**: Risk level assessment based on work package analysis

Include the reporting period (Berichtsperiode) based on the work package data timeframe.

### 3. **ABGESCHLOSSENE AKTIVITÄTEN UND MEILENSTEINE (Completed Activities and Milestones)**
List completed work packages and achievements:
- Work packages completed during the reporting period (with completion percentage = 100%)
- Key milestones reached
- Significant deliverables completed
- Quality gates passed
- Use bullet points with specific work package IDs and titles where available

### 4. **NÄCHSTE AKTIVITÄTEN UND MEILENSTEINE (Next Activities and Milestones)**
Outline upcoming work and priorities:
- Work packages scheduled for the next period
- Upcoming milestones and deadlines
- Critical path activities
- Dependencies that need attention
- Resource requirements for upcoming activities
- Use bullet points with specific work package IDs and due dates where available

### 5. **ENTSCHEIDUNGSBEDARF (Decision Requirements)**
Identify issues requiring decisions or escalation:
- Blocked work packages requiring management intervention
- Resource conflicts or capacity issues
- Scope changes or requirement clarifications needed
- Risk mitigation decisions required
- Budget or timeline adjustments needed
- Stakeholder decisions pending
- Use bullet points with clear action items and responsible parties

## FORMATTING REQUIREMENTS:
- Use German PMFlex terminology throughout
- Structure with clear headings and bullet points
- Include specific work package references where relevant
- Maintain professional tone suitable for German federal government standards
- Focus on actionable insights and clear status communication
- Ensure compliance with PMFlex documentation standards

The report should reflect PMFlex principles of transparency, accountability, and systematic project management approach used in German federal administration. Prioritize clarity and actionable information for project stakeholders and governance bodies.
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
Generate an executive-level project status report focusing on high-level insights and strategic decisions.

PROJECT DATA:
- Project ID: {project_id}
- Total Work Packages: {total_work_packages}
- Analysis: {analysis_data}

Focus on:
1. Strategic project health assessment
2. Key performance indicators
3. Resource allocation efficiency
4. Risk assessment and mitigation
5. Strategic recommendations

Keep the report concise and focused on decision-making insights.
"""

    @staticmethod
    def _get_detailed_template() -> str:
        """Detailed template for comprehensive analysis."""
        return """
Generate a detailed project status report with comprehensive analysis of all aspects.

PROJECT DATA:
- Project ID: {project_id}
- Analysis: {analysis_data}
- Work Packages: {work_packages_summary}

Include detailed sections on:
1. Comprehensive work package analysis
2. Individual team member performance
3. Detailed timeline analysis
4. Quality metrics and trends
5. Detailed risk assessment
6. Comprehensive recommendations with implementation steps

Provide in-depth insights suitable for project managers and team leads.
"""
