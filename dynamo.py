from troposphere.dynamodb2 import ProvisionedThroughput, Table, AttributeDefinition, KeySchema, GlobalSecondaryIndex, \
    LocalSecondaryIndex, Projection
from troposphere import Ref, Join

def keySchema(keySchemas):
    return (KeySchema(AttributeName=keySchema["AttributeName"], KeyType=keySchema["KeyName"]) for keySchema in keySchemas)

def dynamo(item, template, defaults):
    if 'Tables' in item:
        for table in item['Tables']:
            parameters = {
                "AttributeDefinitions": [AttributeDefinition(AttributeName=attribute["AttributeName"],
                                                             AttributeType=attribute[
                                                                 "AttributeType"] if "AttributeType" in attribute else
                                                             defaults["AttributeType"]) for attribute in
                                         table["AttributeDefinitions"]],
                "GlobalSecondaryIndexes": table[
                    "GlobalSecondaryIndexes"] if "GlobalSecondaryIndexes" in table else None,
                "KeySchema": [keySchema(table["KeySchema"])],
                "LocalSecondaryIndexes": [LocalSecondaryIndex(
                    IndexName=localSecondaryIndex["IndexName"],
                    KeySchema=[keySchema(localSecondaryIndex["KeySchema"])],
                    Projection=Projection(

                    )
                ) for localSecondaryIndex in table] if "LocalSecondaryIndexes" in table else None,
                "ProvisionedThroughput": table[
                    "ProvisionedThroughput"] if "ProvisionedThroughput" in table else ProvisionedThroughput(
                    ReadCapacityUnits=defaults["ReadCapacityUnits"], WriteCapacityUnits=defaults["WriteCapacityUnits"]),
                "StreamSpecification": table["StreamSpecification"] if "StreamSpecification" in table else None,
                "TableName": table["TableName"],
            }
            resource = Table(
                table['QueueName'].replace("_", "") + item['Protocol'],
                **dict((k, v) for k, v in parameters.iteritems() if v is not None)
            )
            template.add_resource(resource)
    return template
