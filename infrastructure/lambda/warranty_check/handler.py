import json

# Warranty database — simulates an enterprise warranty check API
# maintained by another team in your organization.
# This Lambda is MCPified via AgentCore Gateway in Lab 3.
WARRANTIES = {
    "PROD-001": {"product": "Wireless Headphones", "warranty_months": 12, "status": "active", "expires": "2027-03-01"},
    "PROD-002": {"product": "Smart Watch", "warranty_months": 24, "status": "active", "expires": "2028-01-15"},
    "PROD-003": {"product": "Laptop Stand", "warranty_months": 6, "status": "expired", "expires": "2026-01-01"},
    "PROD-004": {"product": "USB-C Hub", "warranty_months": 12, "status": "active", "expires": "2027-06-20"},
}


def handler(event, context):
    """
    AgentCore Gateway passes tool parameters directly in the Lambda event.
    The tool name is in context.client_context.custom["bedrockAgentCoreToolName"].
    """
    product_id = event.get("product_id", "").upper()
    if product_id in WARRANTIES:
        return {"statusCode": 200, "body": json.dumps(WARRANTIES[product_id])}
    return {"statusCode": 404, "body": json.dumps({"error": f"No warranty found for {product_id}"})}
