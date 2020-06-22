#!/usr/bin/env python3
import boto3
import time
from aws_cdk import core
import random
import aws_cdk.aws_ec2 as ec2
import os

from cdk_blog_vpc.cdk_blog_vpc_stack import CdkBlogVpcStack
from cdk_blog_vpc.cdk_blog_vpc_stack import CdkBlogVpcPeeringStack
from cdk_blog_vpc.cdk_blog_vpc_stack import CdkBlogMyCustomResourceStack
from cdk_blog_vpc.cdk_blog_vpc_stack import EC2InstanceStack


env_CA = core.Environment(account=os.environ['CDK_DEFAULT_ACCOUNT'],region="ca-central-1")
env_US = core.Environment(account=os.environ['CDK_DEFAULT_ACCOUNT'],region="us-east-1")


app = core.App()

#devs vpc
vpc_dev1_stack=CdkBlogVpcStack(app, id="cdk-blog-vpc-dev1", vpc_name="vpc-dev1", env=env_CA)
my_ec2_dev1=EC2InstanceStack(app, "cdk-blog-vpc1-ec2",vpc_dev1_stack.vpc, env=env_CA)
my_ec2_dev1.add_dependency(vpc_dev1_stack);
vpc_dev2_stack=CdkBlogVpcStack(app, id="cdk-blog-vpc-dev2", vpc_name="vpc-dev2", env=env_CA)
my_ec2_dev2=EC2InstanceStack(app, "cdk-blog-vcp2-ec2",vpc_dev2_stack.vpc, env=env_CA)
my_ec2_dev2.add_dependency(vpc_dev2_stack);
# you can add more...

#staging vpc
vpc_staging_stack=CdkBlogVpcStack(app, id="cdk-blog-vpc-staging", vpc_name="vpc-staging", env=env_CA)
my_ec2_staging=EC2InstanceStack(app, "cdk-blog-vpc-staging-ec2",vpc_staging_stack.vpc, env=env_CA)
my_ec2_staging.add_dependency(vpc_staging_stack);
#staging vpc will be created only once dev vpc are available

vpc_peer_stack1=CdkBlogVpcPeeringStack(app, id="cdk-blog-vpc-peer1", vpc_id1=vpc_dev1_stack.vpc_id, vpc_id2=vpc_staging_stack.vpc_id, env=env_CA)
vpc_peer_stack2=CdkBlogVpcPeeringStack(app, id="cdk-blog-vpc-peer2", vpc_id1=vpc_dev2_stack.vpc_id, vpc_id2=vpc_staging_stack.vpc_id, env=env_CA)


my_custom_resource=CdkBlogMyCustomResourceStack(app, "cdk-blog-custom-resource", env=env_CA)

my_custom_resource.add_dependency(vpc_peer_stack2);
my_custom_resource.add_dependency(vpc_peer_stack1);


app.synth()

