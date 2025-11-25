# Azure PostgreSQL Setup Guide

## Prerequisites

- Azure CLI installed (`az --version` to check)
- Azure subscription with permissions to create resources
- Logged into Azure CLI (`az login`)

## Quick Setup Commands

### Step 1: Set Variables (Customize These)

```bash
# Configuration variables
RESOURCE_GROUP="claude-nine-rg"
LOCATION="eastus"  # or your preferred region
SERVER_NAME="claude-nine-db"
ADMIN_USER="claude_admin"
ADMIN_PASSWORD="YourSecurePassword123!"  # Change this!
DATABASE_NAME="claude_nine"
```

### Step 2: Create Resource Group (if needed)

```bash
# Check if resource group exists
az group exists --name $RESOURCE_GROUP

# If false, create it
az group create \
  --name $RESOURCE_GROUP \
  --location $LOCATION
```

### Step 3: Create PostgreSQL Flexible Server

```bash
az postgres flexible-server create \
  --name $SERVER_NAME \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --admin-user $ADMIN_USER \
  --admin-password $ADMIN_PASSWORD \
  --version 15 \
  --sku-name Standard_B1ms \
  --tier Burstable \
  --storage-size 32 \
  --public-access 0.0.0.0
```

**Expected output:**
```
Creating PostgreSQL flexible server...
This may take 3-5 minutes...
✓ Server created successfully
```

### Step 4: Create Database

```bash
az postgres flexible-server db create \
  --resource-group $RESOURCE_GROUP \
  --server-name $SERVER_NAME \
  --database-name $DATABASE_NAME
```

### Step 5: Configure Firewall

```bash
# Get your current IP
MY_IP=$(curl -s https://api.ipify.org)
echo "Your IP: $MY_IP"

# Add your IP to firewall
az postgres flexible-server firewall-rule create \
  --resource-group $RESOURCE_GROUP \
  --name $SERVER_NAME \
  --rule-name AllowMyIP \
  --start-ip-address $MY_IP \
  --end-ip-address $MY_IP

# Allow Azure services (for future Azure deployments)
az postgres flexible-server firewall-rule create \
  --resource-group $RESOURCE_GROUP \
  --name $SERVER_NAME \
  --rule-name AllowAzureServices \
  --start-ip-address 0.0.0.0 \
  --end-ip-address 0.0.0.0
```

### Step 6: Get Connection Information

```bash
# Show connection details
az postgres flexible-server show \
  --resource-group $RESOURCE_GROUP \
  --name $SERVER_NAME \
  --query "{FQDN:fullyQualifiedDomainName, State:state, Version:version}" \
  --output table
```

## Connection String

After setup, your connection details:

**Host:** `claude-nine-db.postgres.database.azure.com`
**Port:** `5432`
**Database:** `claude_nine`
**Username:** `claude_admin`
**Password:** `<what you set>`
**SSL Mode:** `require`

**Full Connection String:**
```
postgresql://claude_admin:<password>@claude-nine-db.postgres.database.azure.com:5432/claude_nine?sslmode=require
```

## Save to .env File

Create `.env` in the root of your project:

```bash
# .env
DATABASE_URL=postgresql://claude_admin:<password>@claude-nine-db.postgres.database.azure.com:5432/claude_nine?sslmode=require
ANTHROPIC_API_KEY=<your-anthropic-key>
ADO_PAT=<your-azure-devops-pat>
```

**Important:** Add `.env` to `.gitignore`!

## Test Connection

### Option 1: Using psql (if installed)

```bash
psql "postgresql://claude_admin:<password>@claude-nine-db.postgres.database.azure.com:5432/claude_nine?sslmode=require"
```

### Option 2: Using Python

```bash
pip install psycopg2-binary
```

```python
# test_connection.py
import psycopg2

conn_string = "postgresql://claude_admin:<password>@claude-nine-db.postgres.database.azure.com:5432/claude_nine?sslmode=require"

try:
    conn = psycopg2.connect(conn_string)
    cursor = conn.cursor()
    cursor.execute("SELECT version();")
    version = cursor.fetchone()
    print(f"✅ Connected successfully!")
    print(f"PostgreSQL version: {version[0]}")
    cursor.close()
    conn.close()
except Exception as e:
    print(f"❌ Connection failed: {e}")
```

Run: `python test_connection.py`

## Pricing Estimate

**Development Tier (B1ms):**
- Compute: ~$12/month
- Storage (32 GB): ~$4/month
- **Total: ~$16/month**

## Cleanup (if needed)

To delete everything:

```bash
# Delete just the server
az postgres flexible-server delete \
  --resource-group $RESOURCE_GROUP \
  --name $SERVER_NAME \
  --yes

# Or delete entire resource group
az group delete \
  --name $RESOURCE_GROUP \
  --yes
```

## Troubleshooting

### Connection timeout
- Check firewall rules: `az postgres flexible-server firewall-rule list --resource-group $RESOURCE_GROUP --name $SERVER_NAME`
- Verify your IP is allowed
- Check if SSL is required (it is by default)

### Authentication failed
- Verify username format: `claude_admin` (not `claude_admin@server`)
- Check password is correct
- Ensure you're using SSL mode

### Can't create server (quota exceeded)
- Check Azure subscription limits
- Try different region
- Contact Azure support for quota increase

## Next Steps

1. ✅ Save connection string to `.env`
2. ✅ Test connection
3. ✅ Proceed to Phase 1 development
4. ✅ Create database schema (via Alembic migrations)

## Security Notes

- **Never commit** connection strings or passwords to git
- For production: Use Azure Key Vault for secrets
- For production: Enable Private Endpoint (more secure than public access)
- Regular backups are automatic but verify backup policy
- Monitor with Azure Monitor

## Useful Commands

```bash
# Show server status
az postgres flexible-server show -g $RESOURCE_GROUP -n $SERVER_NAME

# List databases
az postgres flexible-server db list -g $RESOURCE_GROUP -s $SERVER_NAME

# List firewall rules
az postgres flexible-server firewall-rule list -g $RESOURCE_GROUP -n $SERVER_NAME

# Restart server
az postgres flexible-server restart -g $RESOURCE_GROUP -n $SERVER_NAME

# Stop server (to save costs when not in use)
az postgres flexible-server stop -g $RESOURCE_GROUP -n $SERVER_NAME

# Start server
az postgres flexible-server start -g $RESOURCE_GROUP -n $SERVER_NAME
```

---

**Estimated Setup Time:** 5-10 minutes (mostly waiting for provisioning)
