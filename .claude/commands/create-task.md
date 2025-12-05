# Create Task Definition

Generate a task YAML definition for the orchestrator.

## Task YAML Structure

```yaml
features:
  - name: feature-identifier        # Unique name (no spaces)
    branch: feature/branch-name     # Git branch name
    work_item_id: "uuid-here"       # UUID from database (optional)
    external_id: "TASK-123"         # External tracking ID (optional)
    role: "Software Developer"      # Agent role
    goal: "Short goal statement"    # What to achieve
    description: |                  # Detailed instructions
      Multi-line description...
    expected_output: "Deliverable"  # What agent should produce
```

## Example Task Definitions

### Simple Feature

```yaml
features:
  - name: add-logging
    branch: feature/add-logging
    role: "Senior Software Developer"
    goal: "Add comprehensive logging to the application"
    description: |
      Add logging throughout the application:

      1. Install logging library if needed
      2. Create logger configuration
      3. Add info logs for key operations
      4. Add error logs for exception handling
      5. Add debug logs for troubleshooting

      Requirements:
      - Use structured logging (JSON format)
      - Include timestamps and log levels
      - Don't log sensitive data
    expected_output: "Complete logging implementation with configuration"
```

### Complex Feature

```yaml
features:
  - name: user-authentication
    branch: feature/user-auth
    work_item_id: "550e8400-e29b-41d4-a716-446655440001"
    external_id: "PBI-456"
    role: "Senior Backend Developer"
    goal: "Implement secure user authentication system"
    description: |
      Implement a complete authentication system with the following:

      ## Requirements
      1. User registration endpoint
         - Email validation
         - Password strength requirements
         - Duplicate email check

      2. Login endpoint
         - Email/password authentication
         - JWT token generation
         - Token expiration (24 hours)

      3. Token refresh endpoint
         - Validate existing token
         - Issue new token

      4. Logout endpoint
         - Invalidate token

      5. Password reset flow
         - Request reset email
         - Validate reset token
         - Update password

      ## Technical Specifications
      - Use bcrypt for password hashing
      - Use JWT with RS256 algorithm
      - Store refresh tokens in database
      - Rate limit auth endpoints

      ## Acceptance Criteria
      - All endpoints return proper HTTP status codes
      - Passwords never logged or returned in responses
      - Tokens include user ID and expiration
      - Unit tests for all auth functions
    expected_output: |
      Complete authentication system with:
      - All endpoints implemented
      - Database migrations
      - Unit tests
      - API documentation
```

### Multiple Features

```yaml
features:
  - name: dark-mode
    branch: feature/dark-mode
    role: "Frontend Developer"
    goal: "Implement dark mode toggle"
    description: |
      Add dark mode support:
      1. Create theme context/store
      2. Add toggle component in header
      3. Define dark color palette
      4. Persist preference in localStorage
    expected_output: "Working dark mode with persistence"

  - name: user-profile
    branch: feature/user-profile
    role: "Full Stack Developer"
    goal: "Create user profile page"
    description: |
      Build user profile functionality:
      1. Create profile API endpoint
      2. Build profile page component
      3. Add avatar upload
      4. Allow editing name/email
    expected_output: "Complete profile page with edit capability"

  - name: api-documentation
    branch: feature/api-docs
    role: "Technical Writer"
    goal: "Document all API endpoints"
    description: |
      Create comprehensive API documentation:
      1. Document each endpoint
      2. Include request/response examples
      3. Add authentication instructions
      4. Create getting started guide
    expected_output: "Complete API documentation in markdown"
```

## Create Task File

### Step 1: Create YAML File

```bash
# Create new task file
cat > claude-multi-agent-orchestrator/tasks/my_tasks.yaml << 'EOF'
features:
  - name: my-feature
    branch: feature/my-feature
    role: "Software Developer"
    goal: "Implement my feature"
    description: |
      Detailed description here...
    expected_output: "Working implementation"
EOF
```

### Step 2: Validate YAML

```bash
# Check YAML syntax
python -c "import yaml; yaml.safe_load(open('claude-multi-agent-orchestrator/tasks/my_tasks.yaml'))"
```

### Step 3: Run Orchestrator

```bash
cd /path/to/target/repo

python /c/projects/claude-9-demo/claude-multi-agent-orchestrator/orchestrator.py \
  --tasks /c/projects/claude-9-demo/claude-multi-agent-orchestrator/tasks/my_tasks.yaml \
  --config config.yaml
```

## Task File Location

Store task files in:
```
claude-multi-agent-orchestrator/tasks/
├── example_tasks.yaml      # Reference example
├── auth_tasks.yaml         # Authentication features
├── frontend_tasks.yaml     # Frontend features
└── my_tasks.yaml           # Your custom tasks
```

## Best Practices

### Good Descriptions

- Be specific about what to implement
- Include acceptance criteria
- Mention any constraints or requirements
- Reference existing code patterns if applicable

### Good Goals

- Short and actionable
- Clearly defines success
- One sentence preferred

### Good Expected Output

- Describe deliverables
- Mention tests if required
- Include documentation expectations

## Template

Copy this template for new tasks:

```yaml
features:
  - name: FEATURE_NAME
    branch: feature/BRANCH_NAME
    work_item_id: "UUID_OR_REMOVE"
    external_id: "EXTERNAL_ID_OR_REMOVE"
    role: "ROLE_TITLE"
    goal: "ONE_SENTENCE_GOAL"
    description: |
      ## Overview
      Brief description of what to implement.

      ## Requirements
      1. First requirement
      2. Second requirement
      3. Third requirement

      ## Technical Details
      - Detail 1
      - Detail 2

      ## Acceptance Criteria
      - [ ] Criterion 1
      - [ ] Criterion 2
    expected_output: "DELIVERABLE_DESCRIPTION"
```
