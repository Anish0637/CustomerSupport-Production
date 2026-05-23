from strands.models.bedrock import BedrockModel

# Using Amazon Nova Pro — no Anthropic use-case form required.
# Switch back to "global.anthropic.claude-sonnet-4-5-20250929-v1:0" once
# Anthropic model access is approved in the Bedrock console.
MODEL_ID = "amazon.nova-pro-v1:0"


def load_model() -> BedrockModel:
    """Get Bedrock model client using IAM credentials."""
    return BedrockModel(model_id=MODEL_ID)
