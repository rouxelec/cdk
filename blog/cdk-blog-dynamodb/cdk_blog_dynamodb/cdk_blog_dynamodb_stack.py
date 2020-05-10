from aws_cdk import core
from aws_cdk import aws_dynamodb

class CdkBlogDynamodbStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # The code that defines your stack goes here
        # create dynamo table
        cidr_range_table = aws_dynamodb.Table(
            self, "cidr_range_table",
            table_name="cidr_range_table",
            partition_key=aws_dynamodb.Attribute(
                name="id",
                type=aws_dynamodb.AttributeType.STRING
            )
        )
        
        last_cidr_range_table = aws_dynamodb.Table(
            self, "last_cidr_range_table",
            table_name="last_cidr_range_table",
            partition_key=aws_dynamodb.Attribute(
                name="id",
                type=aws_dynamodb.AttributeType.STRING
            )
        )