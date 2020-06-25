import boto3
import time
import json
import logging as log
#import cfnresponse

from botocore.vendored import requests

SUCCESS = "SUCCESS"
FAILED = "FAILED"

log.getLogger().setLevel(log.INFO)

physical_id = 'TheOnlyCustomResource2'

ec2 = boto3.resource('ec2', region_name='ca-central-1')
client = boto3.client('ec2', region_name='ca-central-1')
dynamodb = boto3.resource('dynamodb', region_name='ca-central-1')
cidr_range_table = dynamodb.Table('cidr_range_table')

def send(event, context, responseStatus, responseData, physicalResourceId=None, noEcho=False):
    responseUrl = event['ResponseURL']
 
    print(responseUrl)
 
    responseBody = {}
    responseBody['Status'] = responseStatus
    responseBody['Reason'] = 'See the details in CloudWatch Log Stream: ' + context.log_stream_name
    responseBody['PhysicalResourceId'] = physicalResourceId or context.log_stream_name
    responseBody['StackId'] = event['StackId']
    responseBody['RequestId'] = event['RequestId']
    responseBody['LogicalResourceId'] = event['LogicalResourceId']
    responseBody['NoEcho'] = noEcho
    responseBody['Data'] = responseData
 
    json_responseBody = json.dumps(responseBody)
 
    print("Response body:\n" + json_responseBody)
 
    headers = {
        'content-type' : '',
        'content-length' : str(len(json_responseBody))
    }
 
    try:
        response = requests.put(responseUrl,
                                data=json_responseBody,
                                headers=headers)
        print("Status code: " + response.reason)
    except Exception as e:
        print("send(..) failed executing requests.put(..): " + str(e))

def lambda_handler(event, context):
    try:
        log.info('Input event: %s', event)
        if event['RequestType'] == 'Create' and event['ResourceProperties'].get('FailCreate', False):
            raise RuntimeError('Create failure requested')

        message = event['ResourceProperties']['Message']
        attributes = {
            'Response': 'You said "%s"' % message
        }
        if event['RequestType'] == 'Create':
            update_dynamo()
            
        send(event, context, SUCCESS,
                         attributes, physical_id)
    except Exception as e:
        log.exception(e)
        send(event, context, FAILED, {}, physical_id)

def update_dynamo():
    vpcs_and_ec2ips={}
    vpc_peering_connections={}
    filters = [{"Name":"tag-value","Values":["*vpc-dev*","*vpc-staging*"]}]
    vpcs = list(ec2.vpcs.filter(Filters=filters))
    for vpc in vpcs:
        response = client.describe_vpcs(
        VpcIds=[vpc.id]
        )
        
        for subnet in vpc.subnets.all():
            subnet_name=''
            if not subnet.tags==None:
                for tag in subnet.tags:
                    if tag['Key']=="Name":
                        subnet_name=tag['Value']
                        cidr_range_table.put_item(
                            Item={
                                'id': subnet_name,
                                'cidr_range': subnet.cidr_block,
                                'vpc_id' : subnet.vpc_id,
                                'component_type' : "Subnet",
                                'subnet_id': subnet.subnet_id
                        })          
        priv_ip_add='unknown'
        for instance in vpc.instances.all():
            priv_ip_add=instance.private_ip_address
    
        vpc_name=''
        vpc_resp=response['Vpcs'][0]
        vpc_id=vpc_resp['VpcId']
        vpc_and_ec2ip=[]
        vpc_resp=response['Vpcs'][0]
        if not vpc_resp.get('Tags') is None:
            for tag in vpc_resp.get('Tags'):
                if tag['Key']=='Name':  
                    vpc_name=tag['Value']
                    if "vpc-dev" in vpc_name:
                        vpc_and_ec2ip.append(vpc_id)
                        vpc_and_ec2ip.append(priv_ip_add)
                        vpcs_and_ec2ips[vpc_id]=vpc_and_ec2ip
                    cidr_range_table.put_item(
                    Item={
                        'id': vpc_name,
                        'cidr_range': vpc_resp['CidrBlock'],
                        'vpc_id' : vpc_resp['VpcId'],
                        'component_type' : "VPC",
                        'ec2_ip_address' : priv_ip_add
                        }
                    )
        response = client.describe_vpc_peering_connections(
            Filters=[]
        )
        
        
        vpc_peering_ids={}    
        vpcPeeringCs=response['VpcPeeringConnections']
        for vpcPeeringConn in vpcPeeringCs:
            cidr_accepter=vpcPeeringConn.get('AccepterVpcInfo').get('CidrBlock')
            cidr_requester=vpcPeeringConn.get('RequesterVpcInfo').get('CidrBlock')
            vpcPConnId=vpcPeeringConn.get('VpcPeeringConnectionId')
            
            if vpcPeeringConn.get('Status').get("Code")=="active":
                for route_table in vpc.route_tables.all():
                    for asso_att in route_table.associations_attribute:
                        if not asso_att.get('Main'):
                            vpc_peering_ids[vpc_name]=vpcPConnId
                            if vpc.cidr_block==cidr_accepter:
                                route_table.create_route(
                                    DestinationCidrBlock=cidr_requester,
                                    VpcPeeringConnectionId=vpcPConnId
                                )
                            if vpc.cidr_block==cidr_requester:
                                route_table.create_route(
                                    DestinationCidrBlock=cidr_accepter,
                                    VpcPeeringConnectionId=vpcPConnId
                                )    
                ################ WARNING #########################
                # creating specific route to show no transitivity
                # not required            
                if "vpc-dev" in vpc_name and vpc.cidr_block==cidr_requester:
                    vpc_peering_connections[vpc_id]=vpcPConnId
                ###################################################
                    
    ################ WARNING #########################    
    # creating specific route to show no transitivity
    # not required
    filters = [{"Name":"tag-value","Values":["*dev*"]}]
    vpcs = list(ec2.vpcs.filter(Filters=filters))
    for vpc in vpcs:
        for vpc_id,vpc_and_ec2ip in vpcs_and_ec2ips.items():
            ec2_ip=vpc_and_ec2ip[1]
            if not vpc.id==vpc_and_ec2ip[0]:
                vpc_peering_id=vpc_peering_connections[vpc.id]
                for route_table in vpc.route_tables.all():
                    for asso_att in route_table.associations_attribute:
                        if not asso_att.get('Main'):
                            print(ec2_ip+"/32")
                            print(vpc_peering_id)
                            route_table.create_route(
                                DestinationCidrBlock=ec2_ip+"/32",
                                VpcPeeringConnectionId=vpc_peering_id
                            )


    ###################################################