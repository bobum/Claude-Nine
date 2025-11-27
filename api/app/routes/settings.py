"""Settings management endpoints."""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
import os
from pathlib import Path
import httpx
from datetime import datetime

router = APIRouter()


class SettingsSchema(BaseModel):
    """Settings schema for API keys and integration credentials."""
    anthropic_api_key: Optional[str] = None
    azure_devops_url: Optional[str] = None
    azure_devops_token: Optional[str] = None
    azure_devops_organization: Optional[str] = None
    jira_url: Optional[str] = None
    jira_email: Optional[str] = None
    jira_api_token: Optional[str] = None
    github_token: Optional[str] = None
    linear_api_key: Optional[str] = None


class CrewConfigSchema(BaseModel):
    """CrewAI configuration settings."""
    process: str
    verbose: bool


class GitConfigSchema(BaseModel):
    """Git configuration settings."""
    main_branch: str
    auto_merge: bool


class MonitorConfigSchema(BaseModel):
    """Monitor configuration settings."""
    enabled: bool
    check_interval: int


class OrchestratorConfigSchema(BaseModel):
    """
    Orchestrator configuration response schema.

    This schema defines the complete configuration object returned by the
    /api/settings/orchestrator/config endpoint, which is used by orchestrator
    subprocesses to obtain their runtime configuration including API credentials.
    """
    anthropic_api_key: str
    main_branch: str
    check_interval: int
    crew: CrewConfigSchema
    git: GitConfigSchema
    monitor: MonitorConfigSchema


def get_env_path() -> Path:
    """Get path to .env file."""
    return Path(__file__).parent.parent.parent / ".env"


def mask_value(value: Optional[str]) -> Optional[str]:
    """Mask sensitive values for display."""
    if not value or len(value) < 8:
        return value
    return f"{value[:4]}...{value[-4:]}"


def read_env_file() -> dict:
    """Read settings from .env file."""
    env_path = get_env_path()
    settings = {}

    if not env_path.exists():
        return settings

    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                key, value = line.split('=', 1)
                # Strip the \x16 control character that Windows CP1252 encoding may introduce
                settings[key.strip()] = value.strip().lstrip('\x16')

    return settings


def write_env_file(settings: dict) -> None:
    """Write settings to .env file."""
    env_path = get_env_path()

    # Read existing file to preserve comments and structure
    existing_content = []
    if env_path.exists():
        with open(env_path, 'r', encoding='utf-8') as f:
            existing_content = f.readlines()

    # Update or add settings
    updated_keys = set()
    new_lines = []

    for line in existing_content:
        line_stripped = line.strip()
        if not line_stripped or line_stripped.startswith('#'):
            new_lines.append(line)
            continue

        if '=' in line_stripped:
            key = line_stripped.split('=', 1)[0].strip()
            if key in settings:
                new_lines.append(f"{key}={settings[key]}\n")
                updated_keys.add(key)
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)

    # Add new settings that weren't in the file
    for key, value in settings.items():
        if key not in updated_keys and value:
            new_lines.append(f"{key}={value}\n")

    # Write back to file
    with open(env_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)


@router.get("/", response_model=SettingsSchema)
def get_settings():
    """
    Get current settings.

    Returns masked values for security (e.g., sk-ant-...1234).
    """
    env_vars = read_env_file()

    return SettingsSchema(
        anthropic_api_key=mask_value(env_vars.get('ANTHROPIC_API_KEY')),
        azure_devops_url=env_vars.get('AZURE_DEVOPS_URL'),
        azure_devops_token=mask_value(env_vars.get('AZURE_DEVOPS_TOKEN')),
        azure_devops_organization=env_vars.get('AZURE_DEVOPS_ORGANIZATION'),
        jira_url=env_vars.get('JIRA_URL'),
        jira_email=env_vars.get('JIRA_EMAIL'),
        jira_api_token=mask_value(env_vars.get('JIRA_API_TOKEN')),
        github_token=mask_value(env_vars.get('GITHUB_TOKEN')),
        linear_api_key=mask_value(env_vars.get('LINEAR_API_KEY'))
    )


@router.put("/", response_model=SettingsSchema)
def update_settings(settings: SettingsSchema):
    """
    Update settings.

    Only updates non-None values. Masked values are not updated.
    """
    env_vars = read_env_file()
    updates = {}

    # Only update fields that are provided and not masked
    if settings.anthropic_api_key and not settings.anthropic_api_key.startswith('sk-ant-...'):
        updates['ANTHROPIC_API_KEY'] = settings.anthropic_api_key
        os.environ['ANTHROPIC_API_KEY'] = settings.anthropic_api_key

    if settings.azure_devops_url:
        updates['AZURE_DEVOPS_URL'] = settings.azure_devops_url
        os.environ['AZURE_DEVOPS_URL'] = settings.azure_devops_url

    if settings.azure_devops_token and '...' not in settings.azure_devops_token:
        updates['AZURE_DEVOPS_TOKEN'] = settings.azure_devops_token
        os.environ['AZURE_DEVOPS_TOKEN'] = settings.azure_devops_token

    if settings.azure_devops_organization:
        updates['AZURE_DEVOPS_ORGANIZATION'] = settings.azure_devops_organization
        os.environ['AZURE_DEVOPS_ORGANIZATION'] = settings.azure_devops_organization

    if settings.jira_url:
        updates['JIRA_URL'] = settings.jira_url
        os.environ['JIRA_URL'] = settings.jira_url

    if settings.jira_email:
        updates['JIRA_EMAIL'] = settings.jira_email
        os.environ['JIRA_EMAIL'] = settings.jira_email

    if settings.jira_api_token and '...' not in settings.jira_api_token:
        updates['JIRA_API_TOKEN'] = settings.jira_api_token
        os.environ['JIRA_API_TOKEN'] = settings.jira_api_token

    if settings.github_token and '...' not in settings.github_token:
        updates['GITHUB_TOKEN'] = settings.github_token
        os.environ['GITHUB_TOKEN'] = settings.github_token

    if settings.linear_api_key and '...' not in settings.linear_api_key:
        updates['LINEAR_API_KEY'] = settings.linear_api_key
        os.environ['LINEAR_API_KEY'] = settings.linear_api_key

    # Merge with existing settings
    env_vars.update(updates)
    write_env_file(env_vars)

    # Return masked values
    return get_settings()


@router.get(
    "/orchestrator/config",
    response_model=OrchestratorConfigSchema,
    summary="Get Orchestrator Configuration",
    description="""
    Retrieve complete orchestrator configuration for subprocess execution.

    This endpoint provides all runtime configuration needed by orchestrator subprocesses,
    including:
    - Anthropic API credentials (unmasked)
    - Git workflow settings
    - CrewAI process configuration
    - Monitor settings

    **Important Notes:**
    - This endpoint returns unmasked API keys
    - Intended for localhost-only use by orchestrator subprocesses
    - No authentication required (trust localhost access)
    - Solves Windows file encoding issues by serving config via HTTP instead of YAML files

    **Use Case:**
    Orchestrator subprocesses call this endpoint at startup to obtain their configuration,
    avoiding Windows CP1252 encoding issues that corrupt API keys when reading from files.
    """,
    tags=["Settings", "Orchestrator"],
    responses={
        200: {
            "description": "Orchestrator configuration successfully retrieved",
            "content": {
                "application/json": {
                    "example": {
                        "anthropic_api_key": "sk-ant-api03-...",
                        "main_branch": "main",
                        "check_interval": 60,
                        "crew": {
                            "process": "sequential",
                            "verbose": True
                        },
                        "git": {
                            "main_branch": "main",
                            "auto_merge": False
                        },
                        "monitor": {
                            "enabled": True,
                            "check_interval": 30
                        }
                    }
                }
            }
        }
    }
)
def get_orchestrator_config() -> OrchestratorConfigSchema:
    """Get orchestrator configuration for subprocess execution."""
    env_vars = read_env_file()

    return OrchestratorConfigSchema(
        anthropic_api_key=env_vars.get('ANTHROPIC_API_KEY', ''),
        main_branch="main",
        check_interval=60,
        crew=CrewConfigSchema(
            process="sequential",
            verbose=True
        ),
        git=GitConfigSchema(
            main_branch="main",
            auto_merge=False
        ),
        monitor=MonitorConfigSchema(
            enabled=True,
            check_interval=30
        )
    )


@router.post("/test/{integration}")
async def test_connection(integration: str):
    """
    Test connection to an integration.

    Args:
        integration: One of 'anthropic', 'azure-devops', 'jira', 'github', 'linear'

    Returns:
        Status of the connection test.
    """
    env_vars = read_env_file()

    try:
        if integration == "anthropic":
            api_key = env_vars.get('ANTHROPIC_API_KEY')
            if not api_key:
                raise HTTPException(status_code=400, detail="Anthropic API key not configured")

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01"
                    },
                    timeout=10.0
                )
                # A 400 error means the API key is valid but request is invalid (expected)
                # A 401 error means the API key is invalid
                if response.status_code == 401:
                    return {"status": "error", "message": "Invalid API key"}
                else:
                    return {"status": "success", "message": "Connection successful"}

        elif integration == "azure-devops":
            url = env_vars.get('AZURE_DEVOPS_URL')
            token = env_vars.get('AZURE_DEVOPS_TOKEN')
            org = env_vars.get('AZURE_DEVOPS_ORGANIZATION')

            if not all([url, token, org]):
                raise HTTPException(status_code=400, detail="Azure DevOps configuration incomplete")

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{url}/{org}/_apis/projects?api-version=6.0",
                    auth=("", token),
                    timeout=10.0
                )
                if response.status_code == 200:
                    return {"status": "success", "message": "Connection successful"}
                else:
                    return {"status": "error", "message": f"Connection failed: {response.status_code}"}

        elif integration == "jira":
            url = env_vars.get('JIRA_URL')
            email = env_vars.get('JIRA_EMAIL')
            token = env_vars.get('JIRA_API_TOKEN')

            if not all([url, email, token]):
                raise HTTPException(status_code=400, detail="Jira configuration incomplete")

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{url}/rest/api/3/myself",
                    auth=(email, token),
                    timeout=10.0
                )
                if response.status_code == 200:
                    return {"status": "success", "message": "Connection successful"}
                else:
                    return {"status": "error", "message": f"Connection failed: {response.status_code}"}

        elif integration == "github":
            token = env_vars.get('GITHUB_TOKEN')
            if not token:
                raise HTTPException(status_code=400, detail="GitHub token not configured")

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.github.com/user",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=10.0
                )
                if response.status_code == 200:
                    return {"status": "success", "message": "Connection successful"}
                else:
                    return {"status": "error", "message": f"Connection failed: {response.status_code}"}

        elif integration == "linear":
            api_key = env_vars.get('LINEAR_API_KEY')
            if not api_key:
                raise HTTPException(status_code=400, detail="Linear API key not configured")

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.linear.app/graphql",
                    headers={"Authorization": api_key},
                    json={"query": "{ viewer { id } }"},
                    timeout=10.0
                )
                if response.status_code == 200:
                    return {"status": "success", "message": "Connection successful"}
                else:
                    return {"status": "error", "message": f"Connection failed: {response.status_code}"}

        else:
            raise HTTPException(status_code=400, detail=f"Unknown integration: {integration}")

    except httpx.TimeoutException:
        return {"status": "error", "message": "Connection timeout"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
