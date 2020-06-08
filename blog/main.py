import boto3
import time
import json
import subprocess


ec2 = boto3.resource('ec2', region_name='ca-central-1')
client = boto3.client('ec2', region_name='ca-central-1')
dynamodb = boto3.resource('dynamodb', region_name='ca-central-1')


cidr_range_table = dynamodb.Table('cidr_range_table')
#response = cidr_range_table.scan()
# for item in response['Items']:
#     print(item)
#     ip=item.get('ec2_ip_address')
#     vpc_name=item.get('id')
#     if not ip is None:
#         out = subprocess.Popen(['ping', ip, '-n', '1', '-w', '1'], 
#           stdout=subprocess.PIPE, 
#           stderr=subprocess.STDOUT)
#         stdout,stderr = out.communicate()
#         response = cidr_range_table.update_item(
#             Key={
#                 'id': "the_defaut"
#             },
#             UpdateExpression="SET ping_from_"+str(ip.replace('.',"_"))+" = :r",
#             ExpressionAttributeValues={
#                 ':r':  str(stdout),
#             },
#             ReturnValues="UPDATED_NEW"
#         )
        

# print(response)

filters = []
vpcs = list(ec2.vpcs.filter(Filters=filters))

for vpc in vpcs:
    response = client.describe_vpcs(
            VpcIds=[
                vpc.id,
            ]
        )
    #print(response)    
    my_json=json.dumps(response, sort_keys=True, indent=4)    
    cidr_range_table = dynamodb.Table('cidr_range_table')
    subnet_name=''
    for subnet in vpc.subnets.all():
             subnet_name=''
             if not subnet.tags==None:
                 for tag in subnet.tags:
                     if tag['Key']=="Name":
                         subnet_name=tag['Value']
                         #print(subnet_name)
                         response_cidr_range_table = cidr_range_table.put_item(
                	            Item={
                                'id': subnet_name,
                                'cidr_range': subnet.cidr_block,
                                'vpc_id' : subnet.vpc_id,
                                'type' : "Subnet",
                                'subnet_id': subnet.subnet_id
        
                             })
    private_ip_address=''
    for instance in vpc.instances.all():
        #print(instance.private_ip_address)
        private_ip_address=instance.private_ip_address

    vpc_name=''
    if not response['Vpcs'][0].get('Tags') is None:
        for tag in response['Vpcs'][0].get('Tags'):
            if tag['Key']=='Name':  
                vpc_name=tag['Value']
                #response_cidr_range_table = cidr_range_table.put_item(
                #Item={
                #    'id': vpc_name,
                #    'cidr_range': response['Vpcs'][0]['CidrBlock'],
                #    'vpc_id' : response['Vpcs'][0]['VpcId'],
                #    'type' : "VPC",
                #    'ec2_ip_address' : private_ip_address
                #    }
                #)
    print("************************************************")                
    response = client.describe_vpc_peering_connections(
    Filters=[
        
    ]
    )
    
    vpcPeeringConnections=response['VpcPeeringConnections']
    for vpcPeeringConnection in vpcPeeringConnections:
        print(vpcPeeringConnection.get('AccepterVpcInfo').get('CidrBlock'))
        print(vpcPeeringConnection.get('RequesterVpcInfo').get('CidrBlock'))
        print(vpcPeeringConnection.get('VpcPeeringConnectionId'))
        print(vpcPeeringConnection.get('Status'))
        print(vpc.route_tables.all())
        cidr_accepter=vpcPeeringConnection.get('AccepterVpcInfo').get('CidrBlock')
        cidr_requester=vpcPeeringConnection.get('RequesterVpcInfo').get('CidrBlock')
        vpcPeeringConnectionId=vpcPeeringConnection.get('VpcPeeringConnectionId')
        status=vpcPeeringConnection.get('Status').get("Code")
        print(status)
        
        if status=="active":
            for route_table in vpc.route_tables.all():
                for associations_attribute in route_table.associations_attribute:
                    if associations_attribute.get('Main'):
                        if vpc.cidr_block==cidr_accepter:
                            route = route_table.create_route(
                                DestinationCidrBlock=cidr_requester,
                                VpcPeeringConnectionId=vpcPeeringConnectionId
                            )
                        if vpc.cidr_block==cidr_requester:
                            route = route_table.create_route(
                                DestinationCidrBlock=cidr_accepter,
                                VpcPeeringConnectionId=vpcPeeringConnectionId
                            )    
                            
    
                

