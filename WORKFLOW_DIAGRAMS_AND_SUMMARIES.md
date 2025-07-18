# OpenProject Haystack Workflow Diagrams and Summaries

## Table of Contents
1. [Generate Report Workflow](#generate-report-workflow)
2. [HintsAPI Workflow](#hintsapi-workflow)
3. [Workflow Diagrams](#workflow-diagrams)

---

## Generate Report Workflow

### Purpose
Generates comprehensive project status reports in German following PMFlex methodology standards for German federal government projects.

### Key Components
- **Endpoint**: `POST /generate-project-status-report`
- **Input**: Project ID, project type, OpenProject credentials
- **Output**: Structured German project status report with PMFlex-compliant sections

### High-Level Process Flow

#### 1. Authentication & Validation
- Validates user token presence
- Initializes OpenProject client with debug parameter
- Handles authentication errors (401/403)

#### 2. Data Collection
- Fetches all work packages for the project via OpenProject API
- Retrieves comprehensive work package data:
  - Status, priority, assignee information
  - Progress percentages (done_ratio)
  - Due dates and timeline data
  - Type classifications

#### 3. Analysis Phase
- **Status Distribution**: Categorizes work packages by status with detailed logging
- **Completion Statistics**: Calculates average completion, completed vs in-progress counts
- **Timeline Insights**: Identifies overdue items and upcoming deadlines
- **Team Workload**: Analyzes assignee distribution and individual workloads
- **Priority Analysis**: Evaluates priority distribution across work packages

#### 4. RAG Enhancement
- Queries PMFlex documentation for relevant project management guidelines
- Retrieves context-specific best practices based on project type
- Enhances report with German federal government standards

#### 5. Report Generation
- Uses LLM (Ollama) to create structured report with PMFlex template
- Generates comprehensive German report with sections:
  - **Zusammenfassung** (Executive Summary)
  - **Statusübersicht** (Status Overview with traffic light system)
  - **Abgeschlossene Aktivitäten** (Completed Activities)
  - **Nächste Aktivitäten** (Next Activities)
  - **Entscheidungsbedarf** (Decision Requirements)

### Error Handling
- **401 Unauthorized**: Invalid API key
- **403 Forbidden**: Insufficient permissions
- **404 Not Found**: Project not found
- **503 Service Unavailable**: OpenProject unavailable
- **500 Internal Error**: LLM generation failures

### Key Features
- PMFlex compliance for German federal projects
- Comprehensive work package analysis
- RAG-enhanced context from PMFlex documentation
- Professional German report formatting
- Detailed logging and error tracking

---

## HintsAPI Workflow

### Purpose
Provides actionable German project management hints based on automated health checks, helping project managers identify and address issues proactively.

### Key Components
- **Endpoint**: `POST /project-management-hints`
- **Input**: Project ID, project type, OpenProject credentials
- **Output**: List of prioritized, actionable hints in German (max 5-10)

### High-Level Process Flow

#### 1. Authentication & Validation
- Same authentication process as report workflow
- Validates user token and initializes OpenProject client

#### 2. Comprehensive Data Collection
- **Work Packages**: All project tasks with full metadata
- **Relations**: Dependencies and relationships between tasks
- **Time Entries**: Actual work logged against tasks
- **Users**: Team member information
- **Journals**: Activity history and communication logs
- **Attachments**: Documentation and file attachments

#### 3. 10 Automated Health Checks
Each check returns structured results with severity levels (ok/warning/critical):

1. **Deadline Health**: Identifies overdue and at-risk items
2. **Missing Dates**: Flags tasks without start/due dates
3. **Progress Drift**: Compares actual vs expected progress based on time elapsed
4. **Resource Balance**: Checks workload distribution and identifies overloaded users
5. **Dependency Conflicts**: Finds scheduling conflicts between related tasks
6. **Budget vs Actuals**: Compares estimated vs spent time
7. **Risks & Issues**: Highlights unaddressed problems and bugs
8. **Stakeholder Responsiveness**: Detects stale discussions (>7 days inactive)
9. **Scope Creep**: Monitors unexpected additions (new tasks in last 30 days)
10. **Documentation Completeness**: Ensures proper task documentation

#### 4. Severity Assessment & Prioritization
- Each check returns detailed findings with specific work package references
- Severity levels: critical (immediate action) > warning (short-term attention) > ok
- Aggregates results for overall project health assessment

#### 5. Hint Generation Process
- **Primary Path**: LLM generates context-aware hints based on check results
- **Fallback Path**: Hint optimizer creates rule-based hints if LLM fails
- **Enhancement**: Incorporates PMFlex context from RAG system
- **Prioritization**: Critical issues prioritized over warnings
- **Limitation**: Maximum 5-10 most important actionable hints

### Quality Assurance Features
- **JSON Validation**: Ensures proper hint structure
- **Fallback Mechanisms**: Multiple layers of reliability
- **Performance Metrics**: Tracks generation success rates
- **German Language**: Validates language and terminology
- **Hint Optimization**: Uses enhanced hint optimizer for better context-aware suggestions

### Error Handling
- Same API error handling as report workflow
- Additional LLM generation failure handling
- Automatic fallback to rule-based hint generation
- Performance monitoring and metrics tracking

---

## Workflow Diagrams

### Generate Report Workflow Diagram

```mermaid
flowchart TD
    A[POST /generate-project-status-report] --> B{Validate User Token}
    B -->|Invalid| C[Return 401 Unauthorized]
    B -->|Valid| D[Initialize OpenProject Client]
    
    D --> E[Fetch Work Packages from OpenProject]
    E -->|API Error| F{Check Error Type}
    F -->|401/403| G[Return Auth Error]
    F -->|404| H[Return Project Not Found]
    F -->|503| I[Return Service Unavailable]
    F -->|Other| J[Return 500 Internal Error]
    
    E -->|Success| K[Analyze Work Packages]
    K --> L[Calculate Status Distribution]
    K --> M[Calculate Completion Stats]
    K --> N[Analyze Timeline Insights]
    K --> O[Evaluate Team Workload]
    
    L --> P[RAG Enhancement]
    M --> P
    N --> P
    O --> P
    
    P --> Q[Query PMFlex Documentation]
    Q --> R[Retrieve Context-Specific Guidelines]
    R --> S[Create Enhanced Report Prompt]
    
    S --> T[Generate Report with LLM]
    T -->|Success| U[Format PMFlex Report]
    T -->|Failure| V[Return Generation Error]
    
    U --> W[Return ProjectStatusReportResponse]
    
    style A fill:#e1f5fe
    style W fill:#c8e6c9
    style C fill:#ffcdd2
    style G fill:#ffcdd2
    style H fill:#ffcdd2
    style I fill:#ffcdd2
    style J fill:#ffcdd2
    style V fill:#ffcdd2
```

### HintsAPI Workflow Diagram

```mermaid
flowchart TD
    A[POST /project-management-hints] --> B{Validate User Token}
    B -->|Invalid| C[Return 401 Unauthorized]
    B -->|Valid| D[Initialize OpenProject Client]
    
    D --> E[Fetch Comprehensive Project Data]
    E --> E1[Get Work Packages]
    E --> E2[Get Relations]
    E --> E3[Get Time Entries]
    E --> E4[Get Users]
    E --> E5[Get Journals]
    E --> E6[Get Attachments]
    
    E1 -->|API Error| F{Handle API Errors}
    F -->|401/403/404/503| G[Return Appropriate Error]
    
    E1 -->|Success| H[Perform 10 Automated Checks]
    E2 --> H
    E3 --> H
    E4 --> H
    E5 --> H
    E6 --> H
    
    H --> H1[1. Deadline Health]
    H --> H2[2. Missing Dates]
    H --> H3[3. Progress Drift]
    H --> H4[4. Resource Balance]
    H --> H5[5. Dependency Conflicts]
    H --> H6[6. Budget vs Actuals]
    H --> H7[7. Risks & Issues]
    H --> H8[8. Stakeholder Responsiveness]
    H --> H9[9. Scope Creep]
    H --> H10[10. Documentation Completeness]
    
    H1 --> I[Aggregate Check Results]
    H2 --> I
    H3 --> I
    H4 --> I
    H5 --> I
    H6 --> I
    H7 --> I
    H8 --> I
    H9 --> I
    H10 --> I
    
    I --> J[Assess Severity Levels]
    J --> K[Generate Baseline Hints with Optimizer]
    
    K --> L[Query PMFlex Context from RAG]
    L --> M[Enhance with LLM Generation]
    
    M -->|Success| N[Parse and Validate Hints]
    M -->|Failure| O[Use Baseline Hints]
    
    N -->|Valid| P[Merge Enhanced + Baseline Hints]
    N -->|Invalid| O
    
    P --> Q[Prioritize and Limit to 5-10 Hints]
    O --> Q
    
    Q --> R[Return ProjectManagementHintsResponse]
    
    style A fill:#e1f5fe
    style R fill:#c8e6c9
    style C fill:#ffcdd2
    style G fill:#ffcdd2
    style H fill:#fff3e0
    style I fill:#f3e5f5
    style K fill:#e8f5e8
    style O fill:#ffe0b2
```

### Key Differences Between Workflows

| Aspect | Generate Report | HintsAPI |
|--------|----------------|----------|
| **Data Scope** | Work packages only | Comprehensive project data |
| **Analysis Type** | Statistical analysis | Health checks + rule-based analysis |
| **Output Format** | Structured German report | Actionable hint list |
| **LLM Usage** | Primary generation path | Enhanced generation with fallback |
| **Error Handling** | Standard API errors | Enhanced with fallback mechanisms |
| **Performance** | Single analysis pass | Multiple parallel checks |
| **Complexity** | Medium | High |

### Technical Implementation Notes

#### Generate Report Workflow
- Uses `ProjectReportAnalyzer` for statistical analysis
- Implements PMFlex template with RAG enhancement
- Single-pass data processing for efficiency
- Comprehensive German report generation

#### HintsAPI Workflow
- Uses `ProjectManagementAnalyzer` for health checks
- Implements dual-path generation (LLM + fallback)
- Parallel processing of multiple data sources
- Enhanced reliability with hint optimizer
- Performance monitoring and metrics tracking

Both workflows follow the same authentication and error handling patterns but differ significantly in their analysis depth and output format.
