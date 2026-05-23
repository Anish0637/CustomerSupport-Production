# Amazon Bedrock AgentCore CLI — Lab 1 Reference

Step-by-step CLI commands from the AWS Workshop Studio tutorial:
**Getting Started with Amazon Bedrock AgentCore CLI — Lab 1: Building the Agent Prototype**

---

## Prerequisites

Ensure the following are installed:

- Python 3.10+
- Node.js 18+
- `git`
- `uv` (Python package manager)
- AWS CLI configured with valid credentials

---

## Step 0: Install the AgentCore CLI

There are two AgentCore CLIs. Install the **npm (recommended)** one:

```bash
npm install -g @aws/agentcore
```

Verify:

```bash
agentcore --version
```

The Python toolkit is also available (used internally by some commands):

```bash
pip3 install bedrock-agentcore-starter-toolkit
```

---

## Step 1: Create the Project

Scaffold a new CustomerSupport agent project using Strands Agents SDK with Amazon Bedrock:

```bash
# Interactive mode (follows prompts)
agentcore create

# Non-interactive with defaults
agentcore create \
  --project-name CustomerSupport \
  --agent-framework Strands \
  --model-provider Bedrock \
  --non-interactive
```

Expected output:

```
Agent initializing...
    • Template copied.
    • Venv created and installed.
✓ Agent initialized.
```

Navigate into the project:

```bash
cd CustomerSupport
```

---

## Step 2: Project Structure

```
CustomerSupport/
├── .bedrock_agentcore.yaml     # Main project config
├── .gitignore
├── README.md
├── pyproject.toml              # Python dependencies
├── uv.lock
├── src/
│   ├── main.py                 # Agent entry point  ← edit this
│   ├── mcp_client/
│   │   └── client.py           # Exa AI MCP client (web search)
│   └── model/
│       └── load.py             # Model configuration (Claude Sonnet 4.5)
└── test/
```

Key files:

| File | Purpose |
|------|---------|
| `src/main.py` | Agent entry point — tools, system prompt, handler |
| `src/model/load.py` | Bedrock model config (Claude Sonnet 4.5) |
| `src/mcp_client/client.py` | Exa AI MCP client for web search |
| `.bedrock_agentcore.yaml` | AgentCore project configuration |

---

## Step 3: Customize `src/main.py`

Replace the default `add_numbers` sample with customer support tools.

The updated `main.py` adds:

- `get_return_policy(product_category)` — returns policy for electronics / accessories / audio
- `get_product_info(query)` — looks up products by name, ID, or keyword
- Exa AI MCP client — web search for troubleshooting
- Customer support system prompt

See [`src/main.py`](src/main.py) for the full implementation.

---

## Step 4: Start the Local Dev Server

```bash
# Interactive TUI (chat interface in terminal)
agentcore dev

# Non-interactive mode (shows logs, use for split-terminal testing)
agentcore dev --logs
```

The dev server starts on **port 8080** with hot reload enabled.

---

## Step 5: Test the Agent (Interactive)

Inside the `agentcore dev` TUI, try:

```
What's the return policy for electronics?
```
```
Tell me about the Wireless Headphones
```
```
Search for common Bluetooth headphone troubleshooting tips
```
```
I bought a Smart Watch (PROD-002) and want to return it. What's the policy?
```

Press `Esc` to exit the TUI.

---

## Step 6: Test via CLI (Non-Interactive)

In a second terminal, invoke the agent while `agentcore dev --logs` runs in the first:

```bash
agentcore dev "What can you do?" --stream
```

Output is streamed directly to the terminal — useful for scripting and CI/CD.

---

## Step 7: Deploy to AWS

Deploy your agent to Amazon Bedrock AgentCore Runtime (fully managed, scalable):

```bash
agentcore deploy
```

Check deployment status:

```bash
agentcore status
```

Invoke the deployed cloud agent:

```bash
agentcore invoke "What can you do?"
```

To tear down all deployed resources:

```bash
agentcore destroy
```

---

## What Each Command Does

| Command | What it does |
|---------|-------------|
| `agentcore create` | Scaffolds project directory, venv, and starter agent code |
| `agentcore dev` | Runs local dev server with hot reload on port 8080 |
| `agentcore dev --logs` | Same but non-interactive; shows raw logs |
| `agentcore dev "prompt" --stream` | Sends a one-shot prompt and streams the response |
| `agentcore deploy` | Packages code, provisions IAM + runtime via CDK, deploys to cloud |
| `agentcore status` | Shows runtime status, endpoint, and config |
| `agentcore invoke "prompt"` | Invokes the deployed cloud agent |
| `agentcore destroy` | Tears down all AWS resources for this agent |

---

## Tools Built in Lab 1

| Tool | Description |
|------|-------------|
| `get_return_policy(category)` | Returns return window, conditions, and refund type for a product category |
| `get_product_info(query)` | Searches products by name, ID (e.g. `PROD-001`), or keyword |
| Exa AI MCP (web search) | Live web search via [mcp.exa.ai](https://mcp.exa.ai/mcp) |

---

## Next Steps

- **Lab 2**: Add persistent memory for personalized conversations ✅ (see below)
- **Lab 3**: Gateway for centralized, secure tool management
- **Lab 4**: Production observability and session management
- **Lab 5**: Continuous quality evaluation
- **Lab 6**: Customer-facing chat interface
- **Lab 7**: Governing agent actions with policies

---

---

# Lab 2: Add Memory to Your Agent

**Estimated time: ~20 minutes**

Adds persistent memory so the agent remembers customers across sessions using SEMANTIC (facts) and SUMMARIZATION (conversation history) strategies.

---

## Step 1: Add Memory Resource

```bash
agentcore add memory \
  --name SharedMemory \
  --strategies SEMANTIC,SUMMARIZATION \
  --expiry 30
```

Expected output:
```
Added memory 'SharedMemory'
```

This updates `agentcore/agentcore.json` with the memory configuration (SEMANTIC + SUMMARIZATION namespaces).

---

## Step 2: Create the Memory Session Manager

```bash
mkdir -p app/CustomerSupport/memory
touch app/CustomerSupport/memory/__init__.py
touch app/CustomerSupport/memory/session.py
```

Contents of `app/CustomerSupport/memory/session.py`:

```python
import os
from typing import Optional
from bedrock_agentcore.memory.integrations.strands.config import AgentCoreMemoryConfig, RetrievalConfig
from bedrock_agentcore.memory.integrations.strands.session_manager import AgentCoreMemorySessionManager

MEMORY_ID = os.getenv("MEMORY_SHAREDMEMORY_ID")
REGION = os.getenv("AWS_REGION")

def get_memory_session_manager(session_id: str, actor_id: str) -> Optional[AgentCoreMemorySessionManager]:
    if not MEMORY_ID:
        return None

    retrieval_config = {
        f"/users/{actor_id}/facts": RetrievalConfig(top_k=3, relevance_score=0.3),
        f"/summaries/{actor_id}/{session_id}": RetrievalConfig(top_k=3, relevance_score=0.3)
    }

    return AgentCoreMemorySessionManager(
        AgentCoreMemoryConfig(
            memory_id=MEMORY_ID,
            session_id=session_id,
            actor_id=actor_id,
            retrieval_config=retrieval_config,
        ),
        REGION
    )
```

---

## Step 3: Update `agentcore.json` — Add Header Allowlist

Add `requestHeaderAllowlist` to the runtime config in `agentcore/agentcore.json`:

```json
"requestHeaderAllowlist": [
    "X-Amzn-Bedrock-AgentCore-Runtime-Custom-User-Id"
]
```

---

## Step 4: Key Changes in `main.py`

- Import `get_memory_session_manager` from `memory.session`
- Pass `session_manager` to the `Agent` constructor
- Extract `session_id` and `user_id` from runtime context in `invoke()`

```python
from memory.session import get_memory_session_manager

def get_or_create_agent(session_id: str, user_id: str):
    ...
    _agent = Agent(
        model=load_model(),
        session_manager=get_memory_session_manager(session_id, user_id),
        ...
    )

@app.entrypoint
async def invoke(payload, context):
    session_id = context.session_id
    user_id = context.request_headers.get('x-amzn-bedrock-agentcore-runtime-custom-user-id', 'default-user')
    agent = get_or_create_agent(session_id, user_id)
    ...
```

---

## Step 5: Deploy (Memory requires cloud deployment)

```bash
agentcore deploy -y -v
```

---

## Step 6: Test Memory Across Sessions

```bash
# Session A — teach the agent about the user
SESSION_A=$(python3 -c 'import uuid; print(uuid.uuid4())')
agentcore invoke "My name is Sarah and I prefer email updates. I recently bought a Smart Watch." \
  --session-id $SESSION_A \
  -H "X-Amzn-Bedrock-AgentCore-Runtime-Custom-User-Id: Sarah" --stream

# Wait 1-2 minutes for async memory extraction
sleep 2m

# Session B — new session, same user — agent should remember
SESSION_B=$(python3 -c 'import uuid; print(uuid.uuid4())')
agentcore invoke "Do you know anything about me?" \
  --session-id $SESSION_B \
  -H "X-Amzn-Bedrock-AgentCore-Runtime-Custom-User-Id: Sarah" --stream
```

Expected response from Session B:
```
Yes! I know a few things about you, Sarah:
1. Your name is Sarah
2. You prefer email updates
3. You recently purchased a Smart Watch
```

---

## Memory Strategies

| Strategy | What it captures | Namespace |
|----------|-----------------|-----------|
| SEMANTIC | Facts: names, preferences, order details | `/users/{actorId}/facts` |
| SUMMARIZATION | Compressed conversation history | `/summaries/{actorId}/{sessionId}` |

> Memory extraction is **asynchronous** — wait ~1-2 minutes between sessions.

---

## What Each New Command Does

| Command | What it does |
|---------|-------------|
| `agentcore add memory` | Adds memory config to `agentcore.json` |
| `agentcore deploy -y -v` | Re-deploys updating stack with memory resource |
| `agentcore invoke ... --session-id ... -H ...` | Invokes with session ID and custom user header |

---

---

## Lab 3: AgentCore Gateway

AgentCore Gateway exposes backend tools (Lambda functions) to your agent as MCP tools, so the agent can call them at runtime without embedding the logic locally.

### 3.1 Deploy the Warranty Check Lambda

```bash
# Create IAM execution role for Lambda
aws iam create-role \
  --role-name warranty-check-lambda-role \
  --assume-role-policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":"sts:AssumeRole","Principal":{"Service":"lambda.amazonaws.com"}}]}' \
  --profile anish0637

aws iam attach-role-policy \
  --role-name warranty-check-lambda-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole \
  --profile anish0637

# Package and deploy Lambda
cd infrastructure/lambda/warranty_check
zip warranty_lambda.zip handler.py

aws lambda create-function \
  --function-name workshop-warranty-check \
  --runtime python3.12 \
  --role arn:aws:iam::582766763952:role/warranty-check-lambda-role \
  --handler handler.handler \
  --zip-file fileb://warranty_lambda.zip \
  --region us-east-1 \
  --profile anish0637

cd ../../..
```

Lambda ARN: `arn:aws:lambda:us-east-1:582766763952:function/workshop-warranty-check`

### 3.2 Add Gateway and Target via CLI

Run from `/Users/anishkumar/CustomerSupport`:

```bash
export AWS_PROFILE=anish0637
export AWS_DEFAULT_REGION=us-east-1

WARRANTY_LAMBDA_ARN="arn:aws:lambda:us-east-1:582766763952:function:workshop-warranty-check"

# Add gateway configuration to agentcore.json
agentcore add gateway --name my-gateway --runtimes CustomerSupport

# Register Lambda as a gateway target with tool schema
agentcore add gateway-target \
  --type lambda-function-arn \
  --name WarrantyCheck \
  --lambda-arn $WARRANTY_LAMBDA_ARN \
  --tool-schema-file app/CustomerSupport/tool/warranty_schema.json \
  --gateway my-gateway
```

These commands update `agentcore/agentcore.json` with gateway and target config.

### 3.3 Tool Schema

`app/CustomerSupport/tool/warranty_schema.json` defines the `check_warranty` tool exposed to the agent:

```json
[{
  "name": "check_warranty",
  "description": "Check the warranty status of a product by its product ID (e.g. PROD-001).",
  "inputSchema": {
    "type": "object",
    "properties": {
      "product_id": {"type": "string", "description": "The product ID (e.g. PROD-001)"}
    },
    "required": ["product_id"]
  }
}]
```

> `inputSchema` uses `"type": "object"` directly — no nested `"json"` wrapper.

### 3.4 Code Changes

**`app/CustomerSupport/mcp_client/client.py`** — added `get_gateway_mcp_client()`:

```python
def get_gateway_mcp_client() -> MCPClient | None:
    url = os.environ.get("AGENTCORE_GATEWAY_MY_GATEWAY_URL")
    if not url:
        return None   # graceful local degradation
    return MCPClient(lambda: streamablehttp_client(url))
```

**`app/CustomerSupport/main.py`** — key changes:
- Import `get_gateway_mcp_client` from `mcp_client.client`
- Add gateway client to `mcp_clients` list
- Remove `warranty_months` from `PRODUCTS` (now served by Lambda via Gateway)
- `get_product_info` no longer returns warranty months

### 3.5 Deploy

```bash
cd /Users/anishkumar/CustomerSupport
export AWS_PROFILE=anish0637
export AWS_DEFAULT_REGION=us-east-1
agentcore deploy -y -v
```

### 3.6 Test Gateway

```bash
export AWS_PROFILE=anish0637
export AWS_DEFAULT_REGION=us-east-1
cd /Users/anishkumar/CustomerSupport

SESSION_C=$(python3 -c "import uuid; print(uuid.uuid4())")

# Test warranty check via Gateway
agentcore invoke "Check the warranty for product PROD-003" \
  --session-id $SESSION_C \
  -H "X-Amzn-Bedrock-AgentCore-Runtime-Custom-User-Id: Sarah" \
  --stream

# Combined query
agentcore invoke "What is the price of PROD-001 and is it still under warranty?" \
  --session-id $SESSION_C \
  -H "X-Amzn-Bedrock-AgentCore-Runtime-Custom-User-Id: Sarah" \
  --stream
```

### How Lab 3 Works

```
User prompt
    ↓
Agent (Strands)
    ↓
AgentCore Gateway MCP URL (env: AGENTCORE_GATEWAY_MY_GATEWAY_URL)
    ↓
AgentCore Gateway → invokes Lambda function
    ↓
workshop-warranty-check Lambda
    ↓
Returns warranty status back to agent
```

The env var `AGENTCORE_GATEWAY_MY_GATEWAY_URL` is injected automatically at runtime when deployed — not needed locally.

---

## What Each Lab 3 Command Does

| Command | What it does |
|---------|-------------|
| `agentcore add gateway` | Adds gateway config to `agentcore.json`, associates with runtime |
| `agentcore add gateway-target` | Registers Lambda ARN + tool schema as a callable tool |
| `agentcore deploy -y -v` | Provisions gateway infra and wires env var into runtime container |

---

## Lab 4: Securing and Observing in Production

### 4.1 Create Cognito User Pool (self-paced — not Workshop Studio event)

```bash
export AWS_PROFILE=anish0637 && export AWS_DEFAULT_REGION=us-east-1

# User Pool
POOL_ID=$(aws cognito-idp create-user-pool \
  --pool-name CustomerSupportUserPool \
  --auto-verified-attributes email \
  --username-attributes email \
  --policies '{"PasswordPolicy":{"MinimumLength":8,"RequireUppercase":true,"RequireLowercase":true,"RequireNumbers":true,"RequireSymbols":false}}' \
  --query 'UserPool.Id' --output text)

# Resource server
aws cognito-idp create-resource-server \
  --user-pool-id $POOL_ID \
  --identifier "customersupport-api" \
  --name "CustomerSupportAPI" \
  --scopes '[{"ScopeName":"invoke","ScopeDescription":"Invoke agent"}]'

# Machine client (client_credentials)
CLIENT_ID=$(aws cognito-idp create-user-pool-client \
  --user-pool-id $POOL_ID \
  --client-name CustomerSupportMachineClient \
  --generate-secret \
  --allowed-o-auth-flows client_credentials \
  --allowed-o-auth-scopes "customersupport-api/invoke" \
  --allowed-o-auth-flows-user-pool-client \
  --query 'UserPoolClient.ClientId' --output text)

# Web client (USER_PASSWORD_AUTH)
WEB_CLIENT_ID=$(aws cognito-idp create-user-pool-client \
  --user-pool-id $POOL_ID \
  --client-name CustomerSupportWebClient \
  --no-generate-secret \
  --explicit-auth-flows ALLOW_USER_PASSWORD_AUTH ALLOW_REFRESH_TOKEN_AUTH \
  --query 'UserPoolClient.ClientId' --output text)

DISCOVERY_URL="https://cognito-idp.us-east-1.amazonaws.com/${POOL_ID}/.well-known/openid-configuration"

# Store in SSM
aws ssm put-parameter --name /app/customersupport/agentcore/pool_id --value $POOL_ID --type String --overwrite
aws ssm put-parameter --name /app/customersupport/agentcore/client_id --value $CLIENT_ID --type String --overwrite
aws ssm put-parameter --name /app/customersupport/agentcore/web_client_id --value $WEB_CLIENT_ID --type String --overwrite
aws ssm put-parameter --name /app/customersupport/agentcore/cognito_discovery_url --value $DISCOVERY_URL --type String --overwrite
```

Values used in this project:
- Pool ID: `us-east-1_5uhOWVywH`
- Client ID (machine): `2g49s2piup5jppvd7tg7jlfhvl`
- Web Client ID: `4hqbuvfji23kgdeqqn2cujs5p4`
- Discovery URL: `https://cognito-idp.us-east-1.amazonaws.com/us-east-1_5uhOWVywH/.well-known/openid-configuration`

### 4.2 Retrieve Cognito Config from SSM

```bash
COGNITO_DISCOVERY_URL=$(aws ssm get-parameter --name /app/customersupport/agentcore/cognito_discovery_url --query 'Parameter.Value' --output text)
COGNITO_CLIENT_ID=$(aws ssm get-parameter --name /app/customersupport/agentcore/client_id --query 'Parameter.Value' --output text)
COGNITO_POOL_ID=$(aws ssm get-parameter --name /app/customersupport/agentcore/pool_id --query 'Parameter.Value' --output text)
COGNITO_WEB_CLIENT_ID=$(aws ssm get-parameter --name /app/customersupport/agentcore/web_client_id --query 'Parameter.Value' --output text)
```

### 4.3 Update agentcore.json Runtime with JWT Authorizer

In `agentcore/agentcore.json`, add to the `CustomerSupport` runtime entry:
```json
"requestHeaderAllowlist": [
  "X-Amzn-Bedrock-AgentCore-Runtime-Custom-User-Id",
  "Authorization"
],
"authorizerType": "CUSTOM_JWT",
"authorizerConfiguration": {
  "customJwtAuthorizer": {
    "discoveryUrl": "<COGNITO_DISCOVERY_URL>",
    "allowedClients": ["<CLIENT_ID>", "<WEB_CLIENT_ID>"]
  }
}
```

### 4.4 Recreate Gateway with JWT Auth

Gateway authorizer config can't be updated in-place — must remove and recreate:

```bash
cd /Users/anishkumar/CustomerSupport
export AWS_PROFILE=anish0637 && export AWS_DEFAULT_REGION=us-east-1

# Remove old unsecured gateway
agentcore remove gateway --name my-gateway -y

# Create secured gateway
agentcore add gateway --name my-gateway-secure \
  --runtimes CustomerSupport \
  --authorizer-type CUSTOM_JWT \
  --discovery-url $COGNITO_DISCOVERY_URL \
  --allowed-clients $COGNITO_CLIENT_ID,$COGNITO_WEB_CLIENT_ID

# Re-add warranty Lambda target
WARRANTY_LAMBDA_ARN="arn:aws:lambda:us-east-1:582766763952:function:workshop-warranty-check"
agentcore add gateway-target \
  --type lambda-function-arn \
  --name WarrantyCheck \
  --lambda-arn $WARRANTY_LAMBDA_ARN \
  --tool-schema-file app/CustomerSupport/tool/warranty_schema.json \
  --gateway my-gateway-secure
```

> The env var injected at runtime changes: `AGENTCORE_GATEWAY_MY_GATEWAY_URL` → `AGENTCORE_GATEWAY_MY_GATEWAY_SECURE_URL`

### 4.5 Code Changes

**`app/CustomerSupport/mcp_client/client.py`** — reads new env var and passes `Authorization` header:
```python
def get_gateway_mcp_client(auth_header: str) -> MCPClient | None:
    url = os.environ.get("AGENTCORE_GATEWAY_MY_GATEWAY_SECURE_URL")
    if not url:
        return None
    return MCPClient(lambda: streamablehttp_client(url=url, headers={"Authorization": auth_header}))
```

**`app/CustomerSupport/main.py`** — key changes:
- `import jwt` added
- `extract_user_id(auth_header)` extracts `username` claim from JWT, falls back to custom header for local dev
- `get_or_create_agent(session_id, user_id, auth_header)` — gateway MCP client created per-request with auth
- `invoke()` extracts `Authorization` header and passes to agent factory

**`pyproject.toml`** — added `PyJWT >= 2.0.0`

### 4.6 Validate and Deploy

```bash
cd /Users/anishkumar/CustomerSupport
export AWS_PROFILE=anish0637 && export AWS_DEFAULT_REGION=us-east-1
agentcore validate
agentcore deploy -y -v
```

### 4.7 Create Test User and Get Token

```bash
# Create user
aws cognito-idp admin-create-user \
  --user-pool-id $COGNITO_POOL_ID \
  --username workshopuser@example.com \
  --temporary-password 'TempPass1!' \
  --user-attributes Name=email,Value=workshopuser@example.com Name=email_verified,Value=true \
  --message-action SUPPRESS

aws cognito-idp admin-set-user-password \
  --user-pool-id $COGNITO_POOL_ID \
  --username workshopuser@example.com \
  --password 'WorkshopPass1!' \
  --permanent

# Get access token
TOKEN=$(aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id $COGNITO_WEB_CLIENT_ID \
  --auth-parameters USERNAME=workshopuser@example.com,PASSWORD='WorkshopPass1!' \
  --query 'AuthenticationResult.AccessToken' --output text)
```

### 4.8 Test Authenticated Invocations

```bash
SESSION_3=$(python3 -c 'import uuid; print(uuid.uuid4())')

# Authenticated — should succeed
agentcore invoke "What's the return policy for electronics?" \
  --session-id $SESSION_3 --bearer-token "$TOKEN" --stream

# Unauthenticated — should be rejected
agentcore invoke "What's the return policy for electronics?" \
  --session-id $SESSION_3 --stream

# Test Gateway through secured runtime
SESSION_E=$(python3 -c 'import uuid; print(uuid.uuid4())')
agentcore invoke "Check the warranty for PROD-001" \
  --session-id $SESSION_E --bearer-token "$TOKEN" --stream

# Session continuity test
SESSION_1=$(python3 -c 'import uuid; print(uuid.uuid4())')
agentcore invoke "My name is Carlos and I just bought a Mechanical Keyboard" \
  --session-id $SESSION_1 -H "X-Amzn-Bedrock-AgentCore-Runtime-Custom-User-Id: Carlos" --bearer-token "$TOKEN" --stream

agentcore invoke "What did I just buy?" \
  --session-id $SESSION_1 -H "X-Amzn-Bedrock-AgentCore-Runtime-Custom-User-Id: Carlos" --bearer-token "$TOKEN" --stream
```

### 4.9 Observability CLI Commands

```bash
agentcore status
agentcore traces list --limit 10
agentcore traces get <trace-id> --output trace.json
agentcore logs
agentcore logs --since 1h --level error
agentcore logs --since 1h --query "warranty"
```

### Token Refresh (expires after 60 min)

```bash
TOKEN=$(aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id $COGNITO_WEB_CLIENT_ID \
  --auth-parameters USERNAME=workshopuser@example.com,PASSWORD='WorkshopPass1!' \
  --query 'AuthenticationResult.AccessToken' --output text)
```

---

## What Each Lab 4 Command Does

| Command | What it does |
|---------|-------------|
| `agentcore remove gateway --name X -y` | Removes gateway config from `agentcore.json` |
| `agentcore add gateway --authorizer-type CUSTOM_JWT ...` | Creates gateway with Cognito JWT auth |
| `agentcore validate` | Validates `agentcore.json` before deploy |
| `agentcore status` | Shows all deployed resource statuses |
| `agentcore traces list` | Lists recent OpenTelemetry traces from CloudWatch |
| `agentcore logs --since 1h` | Streams recent logs from the runtime |
| `agentcore invoke --bearer-token` | Invokes runtime with Cognito JWT auth |

---

## Lab 5: Evaluating Agent Quality

### 5.1 Add Online Evaluation Config

```bash
cd /Users/anishkumar/CustomerSupport
export AWS_PROFILE=anish0637 && export AWS_DEFAULT_REGION=us-east-1

agentcore add online-eval \
  --name QualityMonitor \
  --runtime CustomerSupport \
  --evaluator Builtin.GoalSuccessRate Builtin.Correctness Builtin.ToolSelectionAccuracy \
  --sampling-rate 100 \
  --enable-on-create
```

> `--sampling-rate 100` evaluates every interaction. Use 10–20% in production to balance cost and coverage.

### 5.2 Deploy

```bash
agentcore deploy -y -v

# Check status — if QualityMonitor shows DISABLED, enable it:
agentcore status
agentcore resume online-eval QualityMonitor
```

### 5.3 Get Token (if expired)

```bash
export AWS_PROFILE=anish0637 && export AWS_DEFAULT_REGION=us-east-1
COGNITO_WEB_CLIENT_ID=4hqbuvfji23kgdeqqn2cujs5p4

TOKEN=$(aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id $COGNITO_WEB_CLIENT_ID \
  --auth-parameters USERNAME=workshopuser@example.com,PASSWORD='WorkshopPass1!' \
  --query 'AuthenticationResult.AccessToken' --output text)
```

### 5.4 Generate Test Interactions

```bash
cd /Users/anishkumar/CustomerSupport
SESSION_EVAL=$(python3 -c 'import uuid; print(uuid.uuid4())')

/Users/anishkumar/.nvm/versions/node/v24.5.0/bin/agentcore invoke \
  "What can you tell me about the Smart Watch? What's the price and warranty?" \
  --session-id $SESSION_EVAL --bearer-token "$TOKEN" --stream

/Users/anishkumar/.nvm/versions/node/v24.5.0/bin/agentcore invoke \
  "I bought headphones last week but they're not working. What's the return policy for audio products?" \
  --session-id $SESSION_EVAL --bearer-token "$TOKEN" --stream

/Users/anishkumar/.nvm/versions/node/v24.5.0/bin/agentcore invoke \
  "Check the warranty status for product PROD-001" \
  --session-id $SESSION_EVAL --bearer-token "$TOKEN" --stream

/Users/anishkumar/.nvm/versions/node/v24.5.0/bin/agentcore invoke \
  "I want to return my USB-C Hub. What's the policy, and can you check if it's still under warranty?" \
  --session-id $SESSION_EVAL --bearer-token "$TOKEN" --stream

/Users/anishkumar/.nvm/versions/node/v24.5.0/bin/agentcore invoke \
  "What kind of support can you provide? List your capabilities." \
  --session-id $SESSION_EVAL --bearer-token "$TOKEN" --stream
```

### 5.5 Run On-Demand Evaluation

```bash
/Users/anishkumar/.nvm/versions/node/v24.5.0/bin/agentcore run eval \
  --runtime CustomerSupport \
  --evaluator Builtin.GoalSuccessRate Builtin.Correctness \
  --days 1
```

### 5.6 View Results

```bash
# Evaluation history
/Users/anishkumar/.nvm/versions/node/v24.5.0/bin/agentcore evals history \
  --runtime CustomerSupport --limit 5

# Evaluation logs
/Users/anishkumar/.nvm/versions/node/v24.5.0/bin/agentcore logs evals \
  --runtime CustomerSupport --since 30m
```

CloudWatch: GenAI Observability → Bedrock AgentCore → CustomerSupport → DEFAULT endpoint → evaluation scores

### 5.7 Pause / Resume (Optional)

```bash
/Users/anishkumar/.nvm/versions/node/v24.5.0/bin/agentcore pause online-eval QualityMonitor
/Users/anishkumar/.nvm/versions/node/v24.5.0/bin/agentcore resume online-eval QualityMonitor
```

### Score Interpretation

| Score | Interpretation | Action |
|-------|---------------|--------|
| 80–100% | Excellent | Monitor and maintain |
| 60–80% | Good but improvable | Review low-scoring sessions |
| < 60% | Needs attention | Investigate root causes |

---

## What Each Lab 5 Command Does

| Command | What it does |
|---------|-------------|
| `agentcore add online-eval` | Adds evaluation config to `agentcore.json` |
| `agentcore run eval --days 1` | Runs on-demand eval against last N days of traces |
| `agentcore evals history` | Lists past evaluation run results |
| `agentcore logs evals` | Streams evaluation processing logs |
| `agentcore pause/resume online-eval` | Toggles continuous evaluation on/off |

---

## Lab 6: Building the Customer Interface

### 6.1 Install Dependencies

```bash
cd /Users/anishkumar/CustomerSupport/app/CustomerSupport
uv add flask boto3 requests
cd ../..
```

### 6.2 Create Cognito Hosted UI Domain (self-paced)

```bash
export AWS_PROFILE=anish0637 && export AWS_DEFAULT_REGION=us-east-1
POOL_ID=us-east-1_5uhOWVywH
WEB_CLIENT_ID=4hqbuvfji23kgdeqqn2cujs5p4

# Create Cognito hosted UI domain
aws cognito-idp create-user-pool-domain \
  --domain customersupport-workshop \
  --user-pool-id $POOL_ID

# Update web client for authorization code flow
aws cognito-idp update-user-pool-client \
  --user-pool-id $POOL_ID \
  --client-id $WEB_CLIENT_ID \
  --explicit-auth-flows ALLOW_USER_PASSWORD_AUTH ALLOW_REFRESH_TOKEN_AUTH \
  --allowed-o-auth-flows code \
  --allowed-o-auth-scopes openid email profile \
  --callback-urls '["http://localhost:8501/callback"]' \
  --logout-urls '["http://localhost:8501/"]' \
  --supported-identity-providers COGNITO \
  --allowed-o-auth-flows-user-pool-client

aws ssm put-parameter --name /app/customersupport/agentcore/cognito_domain \
  --value "https://customersupport-workshop.auth.us-east-1.amazoncognito.com" \
  --type String --overwrite
```

Cognito domain: `https://customersupport-workshop.auth.us-east-1.amazoncognito.com`

### 6.3 Frontend File Structure

```
app/CustomerSupport/frontend/
  __init__.py
  frontend.py          # Flask backend (auth + chat proxy)
  templates/
    login.html         # Cognito hosted UI redirect page
    index.html         # Chat interface
```

### 6.4 How frontend.py Works

- `get_runtime_arn()` reads `agentcore/.cli/deployed-state.json` for auto-discovery
- `/` → if no session token, redirects to Cognito hosted UI login
- `/callback` → exchanges authorization code for Cognito access token, stores in Flask session
- `/chat` → calls AgentCore REST API with `Authorization: Bearer <token>` (not boto3 — JWT bearer not supported)
- `/logout` → clears session, redirects to Cognito logout endpoint
- SSE streaming response is parsed and `<thinking>...</thinking>` blocks are stripped before returning JSON to the browser

Key config values:
- Cognito domain: `https://customersupport-workshop.auth.us-east-1.amazoncognito.com`
- Web client ID: `4hqbuvfji23kgdeqqn2cujs5p4`
- Redirect URI: `http://localhost:8501/callback`
- Invoke URL: `https://bedrock-agentcore.us-east-1.amazonaws.com/runtimes/{arn_encoded}/invocations`

### 6.5 Run the Frontend

```bash
cd /Users/anishkumar/CustomerSupport/app/CustomerSupport/frontend
uv run python frontend.py
```

Open http://localhost:8501 → click "Sign in with Cognito" → login with:
- Email: `workshopuser@example.com`
- Password: `WorkshopPass1!`

### 6.6 Test the Interface

Quick action buttons are available, or type custom queries:
- `Tell me about the Wireless Headphones` — product info tool
- `What's the return policy for electronics?` — return policy tool
- `Check warranty for PROD-002` — Gateway → Lambda
- `Do you remember me?` — cross-session memory recall
- Click 🔄 New Session → `What's my name?` — verifies session isolation

---

## What Each Lab 6 Component Does

| Component | What it does |
|-----------|-------------|
| `frontend.py /callback` | Exchanges Cognito auth code for access token |
| `frontend.py /chat` | Proxies prompt to AgentCore with user's JWT Bearer token |
| `login.html` | Redirects to Cognito hosted UI |
| `index.html` | Chat UI with session management and quick actions |
| `crypto.randomUUID()` | Generates unique session ID per conversation |

---

## Lab 7: Governing Agent Actions with Policies

### 7.0 Prerequisites (self-paced)

**Create and deploy the refund Lambda:**

```bash
export AWS_PROFILE=anish0637 && export AWS_DEFAULT_REGION=us-east-1

# Create infrastructure/lambda/process_refund/handler.py
# (simulates refund processing — returns confirmation_id, refunded_amount, status)

cd infrastructure/lambda/process_refund
zip -j refund.zip handler.py
aws lambda create-function \
  --function-name workshop-process-refund \
  --runtime python3.13 \
  --handler handler.handler \
  --role arn:aws:iam::582766763952:role/warranty-check-lambda-role \
  --zip-file fileb://refund.zip \
  --timeout 30

REFUND_LAMBDA_ARN=arn:aws:lambda:us-east-1:582766763952:function:workshop-process-refund
aws ssm put-parameter --name /app/customersupport/agentcore/refund_lambda_arn \
  --value "$REFUND_LAMBDA_ARN" --type String --overwrite
aws lambda add-permission \
  --function-name workshop-process-refund \
  --statement-id agentcore-gateway-refund \
  --action lambda:InvokeFunction \
  --principal bedrock-agentcore.amazonaws.com
```

### 7.1 Add the Refund Tool Schema

Create `app/CustomerSupport/tool/refund_schema.json`:

```json
[{
  "name": "process_refund",
  "description": "Process a customer refund for a given order.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "order_id": { "type": "string", "description": "The order ID to refund" },
      "amount":   { "type": "integer", "description": "Refund amount in whole dollars" },
      "reason":   { "type": "string", "description": "Reason for the refund" }
    },
    "required": ["order_id", "amount", "reason"]
  }
}]
```

Note: Use `"type": "integer"` (not `"number"`) — Cedar uses Long for integers, enabling `context.input.amount < 100` comparisons.

### 7.2 Add Refund Target to Gateway + Deploy

```bash
cd /Users/anishkumar/CustomerSupport
export AWS_PROFILE=anish0637 && export AWS_DEFAULT_REGION=us-east-1

agentcore add gateway-target \
  --type lambda-function-arn \
  --name ProcessRefund \
  --lambda-arn arn:aws:lambda:us-east-1:582766763952:function:workshop-process-refund \
  --tool-schema-file app/CustomerSupport/tool/refund_schema.json \
  --gateway my-gateway-secure

agentcore deploy -y -v
```

At this point test that unguarded refunds work (any amount succeeds). Then add governance.

### 7.3 Create Policy Engine + Attach to Gateway

```bash
agentcore add policy-engine \
  --name CustomerSupportPolicyEngine \
  --description "Governs customer support agent tool access — refund limits and tool permissions" \
  --attach-to-gateways my-gateway-secure \
  --attach-mode ENFORCE
```

`ENFORCE` mode blocks denied requests. `LOG_ONLY` mode logs decisions without blocking.

**Fix IAM permissions (self-paced only):**
```bash
# Gateway role needs CheckAuthorizePermissions — add inline policy
aws iam put-role-policy \
  --role-name "AgentCore-CustomerSupport-McpGatewayMyGatewaySecure-O4hRAV5OCj6e" \
  --policy-name "AllowPolicyEngineCheck" \
  --policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":"bedrock-agentcore:CheckAuthorizePermissions","Resource":"*"}]}'
```

### 7.4 Get Gateway ARN for Cedar Policies

```bash
GATEWAY_ID=$(aws bedrock-agentcore-control list-gateways \
  --query "items[?contains(name, 'my-gateway-secure')].gatewayId | [0]" \
  --output text)

GATEWAY_ARN=$(aws bedrock-agentcore-control get-gateway \
  --gateway-identifier $GATEWAY_ID \
  --query "gatewayArn" --output text)

echo "Gateway ARN: $GATEWAY_ARN"
```

### 7.5 Create Cedar Policies

**Policy 1: Refund limit (permit < $100)**

```bash
agentcore add policy \
  --name refund_limit_policy \
  --engine CustomerSupportPolicyEngine \
  --description "Allow refunds under 100 dollars only" \
  --statement "permit(principal, action == AgentCore::Action::\"ProcessRefund___process_refund\", resource == AgentCore::Gateway::\"${GATEWAY_ARN}\") when { context.input.amount < 100 };"
```

Cedar syntax: `TargetName___tool_name` (triple underscores). `context.input.amount` maps to the JSON Schema `integer` field.

**Policy 2: Warranty check (always permit for OAuth users)**

Cedar uses **default deny** — once a Policy Engine is attached in ENFORCE mode, every tool needs an explicit `permit`. This policy preserves the existing warranty tool.

```bash
agentcore add policy \
  --name warranty_check_policy \
  --engine CustomerSupportPolicyEngine \
  --description "Allow all authenticated users to check warranties" \
  --statement "permit(principal, action == AgentCore::Action::\"WarrantyCheck___check_warranty\", resource == AgentCore::Gateway::\"${GATEWAY_ARN}\") when { (principal is AgentCore::OAuthUser) };" \
  --validation-mode IGNORE_ALL_FINDINGS
```

**Deploy:**
```bash
agentcore deploy -y -v
```

### 7.6 Test Policy Enforcement

Login at http://localhost:8501 with `workshopuser@example.com` / `WorkshopPass1!`

| Test | Input | Expected |
|------|-------|----------|
| ✅ Small refund | `Refund $50 for ORD-12345, item was defective` | Processed — amount < 100 |
| ❌ Large refund | `Refund $500 for ORD-67890, full refund` | Blocked — Gateway returns 403 |
| ✅ Warranty check | `Check warranty for PROD-002` | Works — explicit permit policy |

### 7.7 (Bonus) Generate Policy from Natural Language

```bash
agentcore add policy \
  --name refund_reason_policy \
  --engine CustomerSupportPolicyEngine \
  --generate "Forbid refunds when the reason does not contain the word defective" \
  --gateway my-gateway-secure

agentcore deploy -y -v
```

After deploying:

| Test | Input | Expected |
|------|-------|----------|
| ✅ | `Refund $50, item was defective` | Permitted by both policies |
| ❌ | `Refund $50, I changed my mind` | Blocked — reason lacks "defective" |

The generated Cedar uses `forbid ... unless { reason like "*defective*" }`. `forbid` overrides `permit`, so this takes precedence over the amount policy.

### 7.8 What Each Lab 7 Component Does

| Component | What it does |
|-----------|-------------|
| `process_refund` Lambda | Simulates refund processing — returns confirmation ID |
| `ProcessRefund` gateway target | Exposes Lambda as `ProcessRefund___process_refund` MCP tool |
| `CustomerSupportPolicyEngine` | Cedar policy container in ENFORCE mode |
| `refund_limit_policy` | Permits refunds only when `amount < 100` |
| `warranty_check_policy` | Permits warranty checks for all OAuth users (prevents default-deny regression) |
| `refund_reason_policy` (bonus) | Forbids refunds unless reason contains "defective" |

---

*Workshop: [AWS Workshop Studio — Getting Started with Amazon Bedrock AgentCore CLI](https://catalog.us-east-1.prod.workshops.aws/)*
