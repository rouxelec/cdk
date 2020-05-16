#!/usr/bin/env python3

from aws_cdk import core

from cdk_blog_vpc.cdk_blog_vpc_stack import CdkBlogVpcStack
from cdk_blog_vpc.cdk_blog_vpc_stack import CdkBlogVpcPeeringStack


env_CA = core.Environment(region="ca-central-1")
env_US = core.Environment(region="us-east-1")
print('Calling')
app = core.App()
print(app)
vpc1_stack=CdkBlogVpcStack(app, id="cdk-blog-vpc1", vpc_name="vpc-dev1", env=env_CA)
print(vpc1_stack.vpc)
vpc2_stack=CdkBlogVpcStack(app, id="cdk-blog-vpc2", vpc_name="vpc-dev2", env=env_CA)
vpc2_stack.add_dependency(vpc1_stack);

vpc_peer_stack=CdkBlogVpcPeeringStack(app, id="cdk-blog-vpc-peer", vpc=vpc1_stack.vpc, peer_vpc=vpc2_stack.vpc, env=env_CA)
vpc_peer_stack.add_dependency(vpc2_stack);

print(vpc1_stack.vpc)

app.synth()
