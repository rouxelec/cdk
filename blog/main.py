import boto3
import time
import json
import subprocess


ec2 = boto3.resource('ec2', region_name='ca-central-1')
client = boto3.client('ec2', region_name='ca-central-1')
dynamodb = boto3.resource('dynamodb', region_name='ca-central-1')


cidr_range_table = dynamodb.Table('cidr_range_table')


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
                       
    priv_ip_add='unknown'
    for instance in vpc.instances.all():
        priv_ip_add=instance.private_ip_address

    vpc_name=''
    vpc_id=''
    vpc_resp=response['Vpcs'][0]
    vpc_id=vpc_resp['VpcId']
    vpc_and_ec2ip=[]
    if not vpc_resp.get('Tags') is None:
        for tag in vpc_resp.get('Tags'):
            if tag['Key']=='Name':  
                vpc_name=tag['Value']
                if "vpc-dev" in vpc_name:
                    vpc_and_ec2ip.append(vpc_id)
                    vpc_and_ec2ip.append(priv_ip_add)
                    vpcs_and_ec2ips[vpc_id]=vpc_and_ec2ip
                
    response = client.describe_vpc_peering_connections(
        Filters=[]
    )
    
    
    vpcPeeringCs=response['VpcPeeringConnections']
    for vpcPeeringConn in vpcPeeringCs:
        if vpcPeeringConn.get('Status').get("Code")=="active":
            cidr_accepter=vpcPeeringConn.get('AccepterVpcInfo').get('CidrBlock')
            cidr_requester=vpcPeeringConn.get('RequesterVpcInfo').get('CidrBlock')
            vpcPConnId=vpcPeeringConn.get('VpcPeeringConnectionId')
            for route_table in vpc.route_tables.all():
                for asso_att in route_table.associations_attribute:
                    if not asso_att.get('Main'):
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
    for vpic_id,vpc_and_ec2ip in vpcs_and_ec2ips.items():
        ec2_ip=vpc_and_ec2ip[1]
        if not vpc.id==vpc_and_ec2ip[0]:
            vpc_peering_id=vpc_peering_connections[vpic_id]
            for route_table in vpc.route_tables.all():
                for asso_att in route_table.associations_attribute:
                    if not asso_att.get('Main'):
                        print(ec2_ip+"/32")
                        print(vpc_peering_id)
                        route_table.create_route(
                            DestinationCidrBlock=ec2_ip+"/32",
                            VpcPeeringConnectionId=vpc_peering_id
                        )
