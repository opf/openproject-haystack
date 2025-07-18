# Project Management Hints API

This document describes the new `/project-management-hints` endpoint that provides German project management hints based on automated analysis of OpenProject data using PMFlex methodology.

## Overview

The endpoint performs 10 automated project management checks and generates actionable German hints for project managers, following the PMFlex methodology used by the German federal government.

## Endpoint Details

**URL:** `POST /project-management-hints`

**Content-Type:** `application/json`

## Request Format

```json
{
  "project": {
    "id": 123,
    "type": "project"
  },
  "openproject": {
    "base_url": "https://your-openproject-instance.com",
    "user_token": "your-api-token-here"
  }
}
```

### Request Parameters

- **project.id** (integer, required): OpenProject project ID
- **project.type** (string, required): Project type (`"project"`, `"portfolio"`, or `"program"`)
- **openproject.base_url** (string, required): Base URL of your OpenProject instance
- **openproject.user_token** (string, required): OpenProject API token for authentication

## Response Format

```json
{
  "hints": [
    {
      "checked": false,
      "title": "Überfällige Arbeitspakete priorisieren",
      "description": "Es wurden 3 überfällige Arbeitspakete identifiziert. Führen Sie umgehend Gespräche mit den Verantwortlichen und definieren Sie realistische neue Termine."
    }
  ],
  "summary": "Das Projekt zeigt insgesamt einen kritischen Status mit 2 kritischen und 3 Warnhinweisen. Schwerpunkt sollte auf der Terminplanung liegen.",
  "generated_at": "2025-01-17T01:43:42.123456",
  "project_id": 123,
  "checks_performed": 10,
  "openproject_base_url": "https://your-openproject-instance.com"
}
```

### Response Fields

- **hints** (array): List of project management hints
  - **checked** (boolean): Always `false` (for UI checkbox functionality)
  - **title** (string): German title of the hint (max 60 characters)
  - **description** (string): Detailed German description with actionable steps
- **summary** (string, optional): German summary of overall project status
- **generated_at** (string): ISO timestamp of generation
- **project_id** (integer): Project ID that was analyzed
- **checks_performed** (integer): Number of automated checks completed
- **openproject_base_url** (string): OpenProject instance URL

## The 10 Automated Checks

The endpoint performs these automated project management checks:

### 1. Deadline Health (Termingesundheit)
- **Purpose**: Flags overdue work packages and upcoming deadlines
- **Data Used**: `dueDate`, `status`, `percentageDone`
- **Severity**: Critical if overdue items exist

### 2. Missing Dates (Fehlende Termine)
- **Purpose**: Identifies work packages without due dates
- **Data Used**: `dueDate`, `startDate`
- **Severity**: Warning if missing dates found

### 3. Progress vs Plan Drift (Fortschrittsabweichung)
- **Purpose**: Compares actual vs expected progress based on time elapsed
- **Data Used**: `percentageDone`, `createdAt`, `dueDate`
- **Severity**: Critical if >30% of items significantly behind

### 4. Resource Load Balance (Ressourcenverteilung)
- **Purpose**: Checks workload distribution among team members
- **Data Used**: `assignee`, work package counts, completion status
- **Severity**: Warning if users overloaded or many unassigned items

### 5. Dependency Conflicts (Abhängigkeitskonflikte)
- **Purpose**: Validates work package relations for scheduling conflicts
- **Data Used**: Work package relations, dates
- **Severity**: Critical if dependency conflicts found

### 6. Budget vs Actuals (Budget vs. Ist-Werte)
- **Purpose**: Compares spent time/cost against estimates
- **Data Used**: Time entries, estimated hours
- **Severity**: Critical if significant budget overruns

### 7. Unaddressed Risks & Issues (Unbearbeitete Risiken)
- **Purpose**: Finds open risks/bugs past due date or without assignee
- **Data Used**: Work package type, status, due date, assignee
- **Severity**: Critical if unaddressed risks found

### 8. Stakeholder Responsiveness (Stakeholder-Reaktionsfähigkeit)
- **Purpose**: Highlights work packages with stale discussions
- **Data Used**: Journal entries, last activity timestamps
- **Severity**: Warning if discussions stale >7 days

### 9. Scope Creep Monitor (Scope-Creep-Überwachung)
- **Purpose**: Detects recent additions that might indicate scope creep
- **Data Used**: Work package creation dates
- **Severity**: Warning if >5 items added recently

### 10. Documentation Completeness (Dokumentationsvollständigkeit)
- **Purpose**: Finds tasks lacking descriptions or required attachments
- **Data Used**: Work package descriptions, attachments
- **Severity**: Warning if documentation gaps found

## PMFlex Integration

The endpoint integrates with the PMFlex methodology through:

- **RAG System**: Retrieves relevant PMFlex documentation and best practices
- **German Terminology**: Uses official PMFlex terms and concepts
- **Compliance Standards**: Follows German federal government project standards
- **Structured Approach**: Aligns with PMFlex project management framework

## Error Handling

The endpoint returns appropriate HTTP status codes:

- **200**: Success - hints generated
- **401**: Authentication error - invalid or missing API token
- **403**: Permission error - insufficient access to project
- **404**: Not found - project doesn't exist
- **500**: Internal server error - processing failed
- **503**: Service unavailable - OpenProject instance unreachable

## Usage Examples

### Basic Usage

```bash
curl -X POST http://localhost:8000/project-management-hints \
  -H "Content-Type: application/json" \
  -d '{
    "project": {
      "id": 123,
      "type": "project"
    },
    "openproject": {
      "base_url": "https://demo.openproject.org",
      "user_token": "your-token-here"
    }
  }'
```

### Python Example

```python
import requests

response = requests.post(
    "http://localhost:8000/project-management-hints",
    json={
        "project": {"id": 123, "type": "project"},
        "openproject": {
            "base_url": "https://your-instance.com",
            "user_token": "your-token"
        }
    }
)

if response.status_code == 200:
    hints = response.json()
    for hint in hints['hints']:
        print(f"• {hint['title']}")
        print(f"  {hint['description']}")
```

## Performance Considerations

- **Processing Time**: 30-120 seconds depending on project size
- **API Calls**: Makes multiple OpenProject API calls for comprehensive analysis
- **Memory Usage**: Processes all work packages and related data in memory
- **Rate Limiting**: Respects OpenProject API rate limits

## Prerequisites

1. **RAG System**: Initialize with `POST /rag/initialize`
2. **PMFlex Documents**: Ensure PMFlex handbooks are in `documents/pmflex/`
3. **OpenProject Access**: Valid API token with project read permissions
4. **Ollama Service**: Running with required models for German text generation

## Integration Tips

1. **Caching**: Consider caching results for frequently accessed projects
2. **Scheduling**: Run periodically (daily/weekly) for project health monitoring
3. **Notifications**: Integrate with notification systems for critical hints
4. **Dashboard**: Display hints in project management dashboards
5. **Workflow**: Use hints as input for project review meetings

## Troubleshooting

### Common Issues

1. **Timeout Errors**: Increase timeout for large projects
2. **Authentication Failures**: Verify OpenProject API token
3. **Missing Context**: Ensure RAG system is initialized
4. **German Encoding**: Use UTF-8 encoding for proper German character display

### Debug Information

Enable debug logging to see:
- OpenProject API call details
- Check execution results
- RAG context retrieval
- LLM generation process

## Future Enhancements

Planned improvements include:
- Custom check configurations
- Historical trend analysis
- Integration with more project management tools
- Multi-language support
- Advanced PMFlex compliance scoring
