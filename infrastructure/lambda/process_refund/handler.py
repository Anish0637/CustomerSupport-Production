import json
import random
import string


def handler(event, context):
    """
    Simulates processing a customer refund.
    AgentCore Gateway passes tool parameters directly in the Lambda event.
    """
    order_id = event.get("order_id", "").upper()
    amount = event.get("amount")
    reason = event.get("reason", "")

    if not order_id:
        return {"statusCode": 400, "body": json.dumps({"error": "order_id is required"})}
    if amount is None or not isinstance(amount, int) or amount <= 0:
        return {"statusCode": 400, "body": json.dumps({"error": "amount must be a positive integer"})}

    # Simulate refund processing
    confirmation_id = "REF-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
    return {
        "statusCode": 200,
        "body": json.dumps({
            "confirmation_id": confirmation_id,
            "order_id": order_id,
            "refunded_amount": amount,
            "reason": reason,
            "status": "processed",
            "message": f"Refund of ${amount} for order {order_id} has been successfully processed. Confirmation: {confirmation_id}"
        })
    }
