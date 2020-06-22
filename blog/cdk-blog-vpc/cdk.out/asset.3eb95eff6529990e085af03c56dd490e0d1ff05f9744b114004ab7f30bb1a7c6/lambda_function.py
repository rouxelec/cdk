import boto3
import time
import json
import logging as log
import cfnresponse

log.getLogger().setLevel(log.INFO)

physical_id = 'TheOnlyCustomResource'

ec2 = boto3.resource('ec2', region_name='ca-central-1')
client = boto3.client('ec2', region_name='ca-central-1')
dynamodb = boto3.resource('dynamodb', region_name='ca-central-1')
cidr_range_table = dynamodb.Table('cidr_range_table')

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
            
        cfnresponse.send(event, context, cfnresponse.SUCCESS,
                         attributes, physical_id)
    except Exception as e:
        log.exception(e)
        cfnresponse.send(event, context, cfnresponse.FAILED, {}, physical_id)

def update_dynamo():
    filters = []
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
    
        ec2_ips={}
        vpc_name='test'
        vpc_resp=response['Vpcs'][0]
        if not vpc_resp.get('Tags') is None:
            for tag in vpc_resp.get('Tags'):
                if tag['Key']=='Name':  
                    vpc_name=tag['Value']
                    ec2_ips[vpc_name]=priv_ip_add
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
    

    ###################################################