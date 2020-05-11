#!/usr/bin/env python3

from aws_cdk import core

from cdk_blog_vpc.cdk_blog_vpc_stack import CdkBlogVpcStack


env_CA = core.Environment(region="ca-central-1")
print('Calling')
app = core.App()
print(app)
CdkBlogVpcStack(app, "cdk-blog-vpc1", vpc_name="vpc-dev1", env=env_CA)
CdkBlogVpcStack(app, "cdk-blog-vpc2", vpc_name="vpc-dev2", env=env_CA)

app.synth()
