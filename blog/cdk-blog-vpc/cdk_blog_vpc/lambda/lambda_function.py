import boto3
import time
import json

ec2 = boto3.resource('ec2', region_name='ca-central-1')
client = boto3.client('ec2', region_name='ca-central-1')
dynamodb = boto3.resource('dynamodb', region_name='ca-central-1')

def lambda_handler(event, context):

    filters = []
    vpcs = list(ec2.vpcs.filter(Filters=filters))
    
    for vpc in vpcs:
               response = client.describe_vpcs(
                       VpcIds=[
                           vpc.id,
                       ]
                   )
               my_json=json.dumps(response, sort_keys=True, indent=4)    
               print(response['Vpcs'])
               cidr_range_table = dynamodb.Table('cidr_range_table')
               
               print(vpc.subnets.all())
               for subnet in vpc.subnets.all():
                          print(subnet.cidr_block)
                          print(subnet.vpc_id)
                          response_cidr_range_table = cidr_range_table.put_item(
               	Item={
                               'id': subnet.subnet_id,
                               'cidr_range': subnet.cidr_block,
                               'vpc_id' : subnet.vpc_id,
                               'type' : "Subnet"
                           })
               
               vpc_name=''
               if not response['Vpcs'][0].get('Tags') is None:
                          if response['Vpcs'][0].get('Tags')[0]['Key']=='Name':                                 
                                     print (response['Vpcs'][0].get('Tags')[0]['Value'])
                                     vpc_name=response['Vpcs'][0].get('Tags')[0]['Value']
               response_cidr_range_table = cidr_range_table.put_item(
    	Item={
                    'id': response['Vpcs'][0]['VpcId'],
                    'cidr_range': response['Vpcs'][0]['CidrBlock'],
                    'vpc_name' : vpc_name,
                    'type' : "VPC"
                }
               )
                      
           