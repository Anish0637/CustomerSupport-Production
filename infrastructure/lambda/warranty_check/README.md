# Deploy this Lambda to AWS:
# 1. zip handler.py as warranty_lambda.zip
# 2. aws lambda create-function \
#      --function-name workshop-warranty-check \
#      --runtime python3.12 \
#      --role <execution-role-arn> \
#      --handler handler.handler \
#      --zip-file fileb://warranty_lambda.zip \
#      --region us-east-1
