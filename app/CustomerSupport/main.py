import asyncio
import threading
from typing import Optional

from strands import Agent, tool
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from model.load import load_model
from mcp_client.client import get_streamable_http_mcp_client, get_gateway_mcp_client
from memory.session import get_memory_session_manager
import jwt

app = BedrockAgentCoreApp()
log = app.logger

SYSTEM_PROMPT = """You are a helpful and professional customer support assistant for an e-commerce company.
Your role is to:
- Provide accurate information using the tools available to you
- Be friendly, patient, and understanding with customers
- Always offer additional help after answering questions
- If you can't help with something, direct customers to the appropriate contact

You have access to the following tools:
1. get_return_policy() - For return policy questions
2. get_product_info() - To look up product information and specifications
3. Web search - To search the web for troubleshooting help

Always use the appropriate tool to get accurate, up-to-date information rather than guessing."""

# --- Customer Support Tools ---

RETURN_POLICIES = {
    "electronics": {"window": "30 days", "condition": "Original packaging required, must be unused or defective", "refund": "Full refund to original payment method"},
    "accessories": {"window": "14 days", "condition": "Must be in original packaging, unused", "refund": "Store credit or exchange"},
    "audio": {"window": "30 days", "condition": "Defective items only after 15 days", "refund": "Full refund within 15 days, replacement after"},
}

# warranty_months removed — warranty info now fetched via AgentCore Gateway (check_warranty tool)
PRODUCTS = {
    "PROD-001": {"name": "Wireless Headphones", "price": 79.99, "category": "audio", "description": "Noise-cancelling Bluetooth headphones with 30h battery life"},
    "PROD-002": {"name": "Smart Watch", "price": 249.99, "category": "electronics", "description": "Fitness tracker with heart rate monitor, GPS, and 5-day battery"},
    "PROD-003": {"name": "Laptop Stand", "price": 39.99, "category": "accessories", "description": "Adjustable aluminum laptop stand for ergonomic desk setup"},
    "PROD-004": {"name": "USB-C Hub", "price": 54.99, "category": "accessories", "description": "7-in-1 USB-C hub with HDMI, USB-A, SD card reader, and ethernet"},
    "PROD-005": {"name": "Mechanical Keyboard", "price": 129.99, "category": "electronics", "description": "RGB mechanical keyboard with Cherry MX switches"},
}


@tool
def get_return_policy(product_category: str) -> str:
    """Get return policy information for a specific product category.

    Args:
        product_category: Product category (e.g., 'electronics', 'accessories', 'audio')

    Returns:
        Formatted return policy details including timeframes and conditions
    """
    category = product_category.lower()
    if category in RETURN_POLICIES:
        policy = RETURN_POLICIES[category]
        return f"Return policy for {category}: Window: {policy['window']}, Condition: {policy['condition']}, Refund: {policy['refund']}"
    return f"No specific return policy found for '{product_category}'. Please contact support for details."


@tool
def get_product_info(query: str) -> str:
    """Search for product information by name, ID, or keyword.

    Args:
        query: Product name, ID (e.g., 'PROD-001'), or search keyword

    Returns:
        Product details including name, price, category, and description
    """
    query_lower = query.lower()
    if query.upper() in PRODUCTS:
        p = PRODUCTS[query.upper()]
        return f"{p['name']} ({query.upper()}): ${p['price']}, Category: {p['category']}, {p['description']}"
    results = [
        f"{pid}: {p['name']} - ${p['price']} - {p['description']}"
        for pid, p in PRODUCTS.items()
        if query_lower in p['name'].lower() or query_lower in p['description'].lower() or query_lower in p['category'].lower()
    ]
    if results:
        return "Found products:\n" + "\n".join(results)
    return f"No products found matching '{query}'."


# --- Agent Setup ---
# Per-session agent cache with thread-safe access.
# Each session gets its own Agent instance so session_manager state is isolated.

_agents: dict[str, Agent] = {}
_agents_lock = threading.Lock()
_MAX_CACHED_SESSIONS = 500  # evict oldest when cache grows too large


def _evict_if_needed() -> None:
    """Simple LRU-like eviction: drop first (oldest) entries when over limit."""
    if len(_agents) >= _MAX_CACHED_SESSIONS:
        evict_count = len(_agents) - _MAX_CACHED_SESSIONS + 1
        for key in list(_agents.keys())[:evict_count]:
            del _agents[key]


def get_or_create_agent(session_id: str, user_id: str, auth_header: str) -> Agent:
    with _agents_lock:
        if session_id in _agents:
            return _agents[session_id]

        _evict_if_needed()

        session_manager = get_memory_session_manager(session_id, user_id)
        mcp_clients = [get_streamable_http_mcp_client(), get_gateway_mcp_client(auth_header)]
        tools = [get_return_policy, get_product_info]
        for mcp_client in mcp_clients:
            if mcp_client:
                tools.append(mcp_client)

        agent = Agent(
            model=load_model(),
            session_manager=session_manager,
            system_prompt=SYSTEM_PROMPT,
            tools=tools,
        )
        _agents[session_id] = agent
        return agent


def extract_user_id(auth_header: str) -> str | None:
    """Extract user_id from JWT bearer token (username claim) or fall back to custom header."""
    if auth_header and auth_header.startswith("Bearer "):
        try:
            token = auth_header.split(" ", 1)[1]
            claims = jwt.decode(token, options={"verify_signature": False})
            username = claims.get("username")
            if username:
                return username
        except Exception as e:
            log.warning(f"Failed to decode JWT for user_id: {e}")
    else:
        log.info(f"No Bearer token found. Auth header present: {auth_header is not None}")
    return None


@app.entrypoint
async def invoke(payload, context):
    log.info("Invoking Agent.....")

    session_id = context.session_id
    request_headers = getattr(context, 'request_headers', None) or {}
    auth_header = request_headers.get('Authorization', '') or request_headers.get('authorization', '')

    user_id = extract_user_id(auth_header)

    # Fall back to custom header for local dev
    if not user_id:
        user_id = request_headers.get('x-amzn-bedrock-agentcore-runtime-custom-user-id', 'default-user')

    if not session_id:
        session_id = 'local-session'

    agent = get_or_create_agent(session_id, user_id, auth_header)
    stream = agent.stream_async(payload.get("prompt"))
    async for event in stream:
        if "data" in event and isinstance(event["data"], str):
            yield event["data"]


if __name__ == "__main__":
    app.run()
