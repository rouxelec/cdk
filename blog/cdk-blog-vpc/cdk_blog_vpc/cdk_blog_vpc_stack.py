from aws_cdk import core
import aws_cdk.aws_ec2 as ec2
from botocore.exceptions import ClientError
import boto3
import json
import ipaddress

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

        print('NEXT CIDR:')
        print(next_cidr_range)
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
                'id': vpc_name,
                'vpc': next_cidr_range
            }
        )
        
        response_last_cidr_range_table = last_cidr_range_table.put_item(
           Item={
                'id': 'last_cidr_range',
                'value': next_cidr_range
            }
        )
        
        
def increment_cidr_range(current_cidr_range):
    startIp=current_cidr_range.split("/")[0]
    newip = ipaddress.IPv4Address(startIp)+65536
    return str(newip)+"/16"
        