import datetime
import uuid
import random
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

    def get_next_cidr_range(self,**kwargs):
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
            item = response.get('Item')
            if item:
                print("GetItem succeeded:")
                print(item)
                last_cidr_range=response['Item']['value']
                next_cidr_range=increment_cidr_range(last_cidr_range);
            else:
                next_cidr_range=default_vpc_cidr_range    

        last_cidr_range_table.put_item(
           Item={
                'id': 'last_cidr_range',
                'value': next_cidr_range
            }
        )

        return next_cidr_range


    def get_current_or_next_cidr_range(self,vpc_name,**kwargs):
        # The code that defines your stack goes here
        dynamodb = boto3.resource('dynamodb', region_name=kwargs['env'].region)


        print(vpc_name)
        cidr_range_table = dynamodb.Table('cidr_range_table')
        
        try:
            response = cidr_range_table.get_item(
                Key={
                    "id": vpc_name
                }
            )
            print(response)
        except ClientError as e:
            print(e.response['Error']['Message'])
            current_or_next_cidr_range=self.get_next_cidr_range(**kwargs)
        else:
            item = response.get('Item')
            if item:
                print("GetItem succeeded:")
                print(item)
                current_or_next_cidr_range=response['Item']['cidr_range']
            else:
                current_or_next_cidr_range=self.get_next_cidr_range(**kwargs)
                
        return current_or_next_cidr_range
        
        
    def __init__(self, scope: core.Construct, id: str, vpc_name:str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)
            
        self.next_cidr_range = self.get_current_or_next_cidr_range(id+"/"+vpc_name,**kwargs)
        #Provisioning VPC
        self.vpc = ec2.Vpc(self, vpc_name,
            cidr=self.next_cidr_range,
            max_azs=3,

            subnet_configuration=[
                ec2.SubnetConfiguration(
                subnet_type=ec2.SubnetType.PUBLIC,
                name="Ingress",
                cidr_mask=24
            #), ec2.SubnetConfiguration(
             #  cidr_mask=24,
             #  name="Application",
             # subnet_type=ec2.SubnetType.PRIVATE
            )
            ]
        )
        self.vpc_id=self.vpc.vpc_id
        

class CdkBlogMyCustomResourceStack(core.Stack):
    def __init__(self, scope: core.App, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        resource = CdkBlogMyCustomResource(
            self, "cdk-blog-resource",
            message="CustomResource is done",
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

        my_lambda_role = iam.Role(self, "Role_lambda",assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"))
        
        my_lambda_role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            resources=["*"],
            actions=["logs:*","ec2:DescribeVpcs","ec2:DescribeInstances","ec2:DescribeInstanceAttribute","dynamodb:PutItem","ec2:DescribeSubnets","ec2:DescribeVpcPeeringConnections","ec2:DescribeRouteTables","ec2:CreateRoute","ec2:ReplaceRouteTableAssociation","ec2:CreateRouteTable","ec2:DisassociateRouteTable","ec2:AssociateRouteTable","ec2:DeleteRoute","ec2:ReplaceRoute","ec2:DeleteRouteTable"]
        ))
        
        _uuid=uuid.uuid1()
        resource = cfn.CustomResource(
            self, "Resource",
            provider=cfn.CustomResourceProvider.lambda_(
                aws_lambda.SingletonFunction(
                    self, "Singleton",
                    uuid=str(_uuid),
                    code=aws_lambda.Code.from_asset("./cdk_blog_vpc/lambda"),
                    handler="lambda_function.lambda_handler",
                    timeout=core.Duration.seconds(300),
                    runtime=aws_lambda.Runtime.PYTHON_3_7,
                    role=my_lambda_role
                )
            ),
            properties=kwargs,
        )

        self.response = resource.get_att("Response").to_string()
        

class CdkBlogVpcPeeringStack(core.Stack):
    def __init__(self, scope: core.Construct, id: str, vpc_id1:str,vpc_id2:str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)
        tag=core.CfnTag(key='Name',value=vpc_id1+vpc_id2)
        self.vpc_peer=VPCPeeringConnection(self,'vpc_peering_connection', vpc_id=vpc_id1, peer_vpc_id=vpc_id2,tags=[tag])
        self.vpc_peer_ref=self.vpc_peer.ref

        
class EC2InstanceStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str,vpc:ec2.Vpc, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)


        # AMI 
        amzn_linux = ec2.MachineImage.latest_amazon_linux(
            generation=ec2.AmazonLinuxGeneration.AMAZON_LINUX_2,
            edition=ec2.AmazonLinuxEdition.STANDARD,
            virtualization=ec2.AmazonLinuxVirt.HVM,
            storage=ec2.AmazonLinuxStorage.GENERAL_PURPOSE
            )

        my_ec2_role = iam.Role(self, "Role_ec2",assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"))
        
        my_ec2_role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            resources=["*"],
            actions=["dynamodb:Scan",
                    "dynamodb:PutItem","dynamodb:UpdateItem"]
        ))


        allow_ping_security_group = ec2.SecurityGroup(self, "SecurityGroup",
            vpc=vpc,
            description="Allow ping",
            allow_all_outbound=True
        )
        allow_ping_security_group.add_ingress_rule(ec2.Peer.ipv4("10.0.0.0/8"), ec2.Port.icmp_ping(), "allow ssh access from the world")

        # Instance
        instance = ec2.Instance(self, "Instance",
            instance_type=ec2.InstanceType("t2.micro"),
            machine_image=amzn_linux,
            vpc = vpc,
            key_name = "test-ec2",
            role = my_ec2_role
            )

        instance.add_security_group(allow_ping_security_group)

        instance.user_data.add_commands(
            "yum update -y","yum install python3 -y","yum install git -y","pip3 install boto3","git clone https://github.com/rouxelec/ec2_user_data.git",'echo "* * * * * python3 /ec2_user_data/userdata.py" >> /tmp/montest','crontab /tmp/montest'
        )

        
def increment_cidr_range(current_cidr_range):
    startIp=current_cidr_range.split("/")[0]
    newip = ipaddress.IPv4Address(startIp)+vpc_nb_ips
    new_cidr_range=str(newip)+vpc_size
    #check if we used all available cidr_range
    if max_vpc_cidr_range == new_cidr_range:
        new_cidr_range=default_vpc_cidr_range
    print(new_cidr_range)
    return new_cidr_range
        