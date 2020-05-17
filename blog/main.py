import boto3
import time

waiting_interval=10
client = boto3.client('cloudformation', region_name="ca-central-1")

response = client.describe_stacks(
    StackName='cdk-blog-dynamodb'
)
print(response)

print(response['Stacks'][0]['StackStatus'])
# 10min timeout
timeout=600
while(response['Stacks'][0]['StackStatus']!='CREATE_COMPLETE' and timeout > 0):
           timeout-=waiting_interval
           time.sleep(waiting_interval)
           print('Waiting for CFN to complete...')
           response = client.describe_stacks(
               StackName='cdk-blog-dynamodb'
           )
           