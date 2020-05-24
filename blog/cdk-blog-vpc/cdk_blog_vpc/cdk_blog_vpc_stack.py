import datetime
import uuid
from aws_cdk import core
import aws_cdk.aws_ec2 as ec2
import aws_cdk.aws_s3 as s3
import aws_cdk.aws_lambda as aws_lambda
import aws_cdk.aws_events as aws_events
import aws_cdk.aws_events_targets as aws_events_targets
import aws_cdk.aws_iam as iam
import aws_cdk.aws_cloudformation as cfn

from botocore.exceptions import ClientError
import boto3
import json
import ipaddress


#VPC informations
vpc_size="/16"
default_vpc_cidr_range="10.0.0.0"+vpc_size
max_vpc_cidr_range="10.255.0.0"+vpc_size
vpc_nb_ips=65536


class VPCPeeringConnection(ec2.CfnVPCPeeringConnection):
    def __init__(self,scope, id, **kwargs):
        super().__init__(scope, id, **kwargs)
        

class CdkBlogVpcStack(core.Stack):

    def get_next_cidr_range(self,vpc_name,**kwargs):
        # The code that defines your stack goes here
        dynamodb = boto3.resource('dynamodb', region_name=kwargs['env'].region)

        # check if same vpc has been deployed once
        last_cidr_range_table = dynamodb.Table('last_cidr_range_table')

        try:
            response = last_cidr_range_table.get_item(
                Key={
                    "id": "last_cidr_range"
                }
            )
        except ClientError as e:
            print(e.response['Error']['Message'])
            next_cidr_range=default_vpc_cidr_range
        else:
            item = response['Item']
            print("GetItem succeeded:")
            print(item)
            last_cidr_range=response['Item']['value']
            next_cidr_range=increment_cidr_range(last_cidr_range);

        response_last_cidr_range_table = last_cidr_range_table.put_item(
           Item={
                'id': 'last_cidr_range',
                'value': next_cidr_range
            }
        )

        return next_cidr_range

    def __init__(self, scope: core.Construct, id: str, vpc_name:str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)
            
        next_cidr_range = self.get_next_cidr_range(vpc_name,**kwargs)
        #Provisioning VPC
        self.vpc = ec2.Vpc(self, vpc_name,
            cidr=next_cidr_range,
            max_azs=3,

            subnet_configuration=[ec2.SubnetConfiguration(
                subnet_type=ec2.SubnetType.PUBLIC,
                name="Ingress",
                cidr_mask=24
            ), ec2.SubnetConfiguration(
                cidr_mask=24,
                name="Application",
                subnet_type=ec2.SubnetType.PRIVATE
            )
            ]
        )
        

class CdkBlogMyCustomResourceStack(core.Stack):
    def __init__(self, scope: core.App, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        resource = CdkBlogMyCustomResource(
            self, "DemoResource",
            message="CustomResource says hello",
        )

        # Publish the custom resource output
        core.CfnOutput(
            self, "ResponseMessage",
            description="The message that came back from the Custom Resource",
            value=resource.response,
        )


class CdkBlogMyCustomResource(core.Construct):
    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id)

        print('reading code source...')
        with open("./cdk_blog_vpc/lambda/lambda_function.py", encoding="utf-8") as fp:
            code_body = fp.read()
        print('code source ok...')

        my_lambda_role = iam.Role(self, "Role",assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"))
        
        my_lambda_role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            resources=["*"],
            actions=["ec2:DescribeVpcs",
                    "dynamodb:PutItem","ec2:DescribeSubnets"]
        ))
        
        _uuid=uuid.uuid1()
        print(str(_uuid))
        resource = cfn.CustomResource(
            self, "Resource",
            provider=cfn.CustomResourceProvider.lambda_(
                aws_lambda.SingletonFunction(
                    self, "Singleton",
                    uuid=str(_uuid),
                    code=aws_lambda.InlineCode(code_body),
                    handler="index.lambda_handler",
                    timeout=core.Duration.seconds(300),
                    runtime=aws_lambda.Runtime.PYTHON_3_7,
                    role=my_lambda_role
                )
            ),
            properties=kwargs,
        )

        self.response = resource.get_att("Response").to_string()
        
class CdkBlogMyLambdaStack(core.Stack):
    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)
        
    
        my_lambda_role = iam.Role(self, "Role",assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"))
        
        my_lambda_role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            resources=["*"],
            actions=["ec2:DescribeVpcs",
                    "dynamodb:PutItem","ec2:DescribeSubnets"]
        ))
        
        
        lambda_code_bucket = s3.Bucket.from_bucket_attributes(
            self, 'LambdaCodeBucket',
            bucket_name='cdk-blog-vpc'
        )
        
        my_lambda = aws_lambda.Function(self, "my_lambda_function",
                                      runtime=aws_lambda.Runtime.PYTHON_3_6,
                                      handler="lambda_function.lambda_handler",
                                      #code=aws_lambda.Code.from_asset("./cdk_blog_vpc/lambda/"))
                                      code=aws_lambda.S3Code(
                                            bucket=lambda_code_bucket,
                                            key='lambda_function.zip'
                                        ),
                                        role=my_lambda_role)
                                        
        # now + time to complete previous stacks
        #now = datetime.datetime.now(timezone('US/Eastern')) + datetime.timedelta(minutes=15)
        now = datetime.datetime.now()
        one_time_rule = aws_events.Rule(
            self, "one_time_rule",
            schedule=aws_events.Schedule.cron(minute=str(now.minute),hour=str(now.hour),day=str(now.day),month=str(now.month),year=str(now.year))
        )

        # Add target to Cloudwatch Event
        one_time_rule.add_target(aws_events_targets.LambdaFunction(my_lambda))   

        
class CdkBlogVpcPeeringStack(core.Stack):
    def __init__(self, scope: core.Construct, id: str, vpc:ec2.Vpc,peer_vpc:ec2.Vpc, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)
        vpc_peer=VPCPeeringConnection(self,'test', vpc_id=vpc.vpc_id, peer_vpc_id=peer_vpc.vpc_id)
        
        
def increment_cidr_range(current_cidr_range):
    startIp=current_cidr_range.split("/")[0]
    newip = ipaddress.IPv4Address(startIp)+vpc_nb_ips
    new_cidr_range=str(newip)+vpc_size
    #check if we used all available cidr_range
    if max_vpc_cidr_range == new_cidr_range:
        new_cidr_range=default_vpc_cidr_range
    print(new_cidr_range)
    return new_cidr_range
        