#!/usr/bin/env python3
import boto3
import time
from aws_cdk import core

from cdk_blog_vpc.cdk_blog_vpc_stack import CdkBlogVpcStack
from cdk_blog_vpc.cdk_blog_vpc_stack import CdkBlogVpcPeeringStack
from cdk_blog_vpc.cdk_blog_vpc_stack import CdkBlogMyLambdaStack


env_CA = core.Environment(region="ca-central-1")
env_US = core.Environment(region="us-east-1")

app = core.App()

#devs vpc
vpc_dev1_stack=CdkBlogVpcStack(app, id="cdk-blog-vpc-dev1", vpc_name="vpc-dev1", env=env_CA)
my_lambda_stack=CdkBlogMyLambdaStack(app, id="cdk-blog-lambda", env=env_CA)
my_lambda_stack.add_dependency(vpc_dev1_stack);

#vpc_dev2_stack=CdkBlogVpcStack(app, id="cdk-blog-vpc-dev2", vpc_name="vpc-dev2", env=env_CA)
# you can add more...

#staging vpc
#vpc_staging_stack=CdkBlogVpcStack(app, id="cdk-blog-vpc-staging", vpc_name="vpc-staging", env=env_CA)

#staging vpc will be created only once dev vpc are available
#vpc_staging_stack.add_dependency(vpc_dev1_stack);
#vpc_staging_stack.add_dependency(vpc_dev2_stack);

#vpc_peer_stack=CdkBlogVpcPeeringStack(app, id="cdk-blog-vpc-peer", vpc=vpc_dev1_stack.vpc, peer_vpc=vpc_staging_stack.vpc, env=env_CA)
#vpc_peer_stack=CdkBlogVpcPeeringStack(app, id="cdk-blog-vpc-peer", vpc=vpc_dev2_stack.vpc, peer_vpc=vpc_staging_stack.vpc, env=env_CA)
# staging vpc required
#vpc_peer_stack.add_dependency(vpc_staging_stack);

app.synth()

