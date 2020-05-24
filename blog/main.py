import boto3
import time
import json

ec2 = boto3.resource('ec2', region_name='ca-central-1')
client = boto3.client('ec2', region_name='ca-central-1')
dynamodb = boto3.resource('dynamodb', region_name='ca-central-1')


filters = []
vpcs = list(ec2.vpcs.filter(Filters=filters))

for vpc in vpcs:
    response = client.describe_vpcs(
            VpcIds=[
                vpc.id,
            ]
        )
    my_json=json.dumps(response, sort_keys=True, indent=4)    
    cidr_range_table = dynamodb.Table('cidr_range_table')
    subnet_name=''
    for subnet in vpc.subnets.all():
             subnet_name=''
             if not subnet.tags==None:
                 for tag in subnet.tags:
                     if tag['Key']=="Name":
                         subnet_name=tag['Value']
                         print(subnet_name)
                         response_cidr_range_table = cidr_range_table.put_item(
                	            Item={
                                'id': subnet_name,
                                'cidr_range': subnet.cidr_block,
                                'vpc_id' : subnet.vpc_id,
                                'type' : "Subnet",
                                'subnet_id': subnet.subnet_id
                             })
    
    vpc_name=''
    if not response['Vpcs'][0].get('Tags') is None:
        for tag in response['Vpcs'][0].get('Tags'):
            if tag['Key']=='Name':  
                vpc_name=tag['Value']
                response_cidr_range_table = cidr_range_table.put_item(
                Item={
                    'id': vpc_name,
                    'cidr_range': response['Vpcs'][0]['CidrBlock'],
                    'vpc_id' : response['Vpcs'][0]['VpcId'],
                    'type' : "VPC"
                    }
                )
                      
           