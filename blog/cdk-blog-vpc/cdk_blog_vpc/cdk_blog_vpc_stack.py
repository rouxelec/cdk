from aws_cdk import core
import aws_cdk.aws_ec2 as ec2
from botocore.exceptions import ClientError
import boto3
import json

default_vpc_cidr_range="10.0.0.0/16"

class CdkBlogVpcStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, vpc_name:str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

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

        #Provisioning VPC
        vpc = ec2.Vpc(self, vpc_name,
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
            ), ec2.SubnetConfiguration(
                cidr_mask=28,
                name="Database",
                subnet_type=ec2.SubnetType.ISOLATED,
                reserved=True
            )
            ]
        )
        
        cidr_range_table = dynamodb.Table('cidr_range_table')
        response_cidr_range_table = cidr_range_table.put_item(
           Item={
                'id': next_cidr_range,
                'vpc': vpc_name
            }
        )
        
        
def increment_cidr_range(current_cidr_range):
    tab_cidr=current_cidr_range.split('.')
    return tab_cidr[0]+'.'+tab_cidr[1]+'.'+str(int(tab_cidr[2])+1)+'.'+tab_cidr[3]
        