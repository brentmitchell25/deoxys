from troposphere.dynamodb2 import ProvisionedThroughput, Table, AttributeDefinition, KeySchema, GlobalSecondaryIndex, \
    LocalSecondaryIndex, Projection, StreamSpecification
from troposphere import Ref, Join, GetAtt
from troposphere.awslambda import EventSourceMapping
from awacs.aws import Principal
import awacs.awslambda as awslambda
import re

regex = re.compile('[^a-zA-Z]')


def keySchema(keySchemas):
    return (KeySchema(AttributeName=keySchema["AttributeName"], KeyType=keySchema["KeyName"]) for keySchema in
            keySchemas)


def dynamodb(item, template, defaults):
    if 'Tables' in item:
        for table in item['Tables']:
            parameters = {
                "AttributeDefinitions": [AttributeDefinition(AttributeName=attribute["AttributeName"],
                                                             AttributeType=attribute[
                                                                 "AttributeType"] if "AttributeType" in attribute else
                                                             defaults.get("DEFAULT", "AttributeType")) for attribute in
                                         table["AttributeDefinitions"]],
                "GlobalSecondaryIndexes": [GlobalSecondaryIndex(
                    IndexName=globalSecondaryIndex["IndexName"],
                    KeySchema=[keySchema(globalSecondaryIndex["KeySchema"])],
                    Projection=Projection(
                        NonKeyAttributes=globalSecondaryIndex["Projection"]["NonKeyAttributes"],
                        ProjectionType=globalSecondaryIndex["Projection"]["ProjectionType"]
                    ),
                    ProvisionedThroughput=ProvisionedThroughput(
                        ReadCapacityUnits=globalSecondaryIndex["ProvisionedThroughput"][
                            "ReadCapacityUnits"] if "ProvisionedThroughput" in globalSecondaryIndex and "ReadCapacityUnits" in
                                                                                                        globalSecondaryIndex[
                                                                                                            "ProvisionedThroughput"] else
                        defaults.get("DEFAULT", "ReadCapacityUnits"),
                        WriteCapacityUnits=globalSecondaryIndex["ProvisionedThroughput"][
                            "WriteCapacityUnits"] if "ProvisionedThroughput" in globalSecondaryIndex and "WriteCapacityUnits" in
                                                                                                         globalSecondaryIndex[
                                                                                                             "ProvisionedThroughput"] else
                        defaults.get("DEFAULT", "WriteCapacityUnits")
                    )
                ) for globalSecondaryIndex in table] if "GlobalSecondaryIndexes" in table else None,
                "KeySchema": [keySchema(table["KeySchema"])],
                "LocalSecondaryIndexes": [LocalSecondaryIndex(
                    IndexName=localSecondaryIndex["IndexName"],
                    KeySchema=[keySchema(localSecondaryIndex["KeySchema"])],
                    Projection=Projection(
                        NonKeyAttributes=localSecondaryIndex["Projection"]["NonKeyAttributes"],
                        ProjectionType=localSecondaryIndex["Projection"]["ProjectionType"]
                    )
                ) for localSecondaryIndex in table] if "LocalSecondaryIndexes" in table else None,
                "ProvisionedThroughput": ProvisionedThroughput(
                    ReadCapacityUnits=table["ProvisionedThroughput"][
                        "ReadCapacityUnits"] if "ProvisionedThroughput" in table and "ReadCapacityUnits" in
                                                                                     table[
                                                                                         "ProvisionedThroughput"] else
                    defaults.get("DEFAULT", "ReadCapacityUnits"),
                    WriteCapacityUnits=table["ProvisionedThroughput"][
                        "WriteCapacityUnits"] if "ProvisionedThroughput" in table and "WriteCapacityUnits" in
                                                                                      table[
                                                                                          "ProvisionedThroughput"] else
                    defaults.get("DEFAULT", "WriteCapacityUnits"),

                ),
                "StreamSpecification": StreamSpecification(
                    StreamViewType=table["StreamSpecification"][
                        "StreamViewType"] if "StreamSpecification" in table and "StreamViewType" in table[
                        "StreamSpecification"] else defaults.get("DEFAULT", "StreamViewType")
                ),
                "TableName": table["TableName"],
            }
            tableId = regex.sub("", table['TableName']) + item['Protocol']
            tableResource = Table(
                tableId,
                **dict((k, v) for k, v in parameters.iteritems() if v is not None)
            )
            template.add_resource(tableResource)

            if "Triggers" in table:
                for trigger in table["Triggers"]:
                    parameters = {
                        "BatchSize": trigger["BatchSize"] if "BatchSize" in trigger else None,
                        "Enabled": trigger["FunctionName"] if "Enabled" in trigger else "Enabled",
                        "EventSourceArn": GetAtt(tableResource, "StreamArn"),
                        "FunctionName": trigger["FunctionName"],
                        "StartingPosition": trigger[
                            "StartingPosition"] if "StartingPosition" in trigger else defaults.get("DEFAULT",
                                                                                                   "StartingPosition"),
                        "DependsOn": [tableId]
                    }
                    eventSourceMapping = EventSourceMapping(
                        regex.sub("", trigger["FunctionName"]) + tableId + "EventSourceMapping",
                        **dict((k, v) for k, v in parameters.iteritems() if v is not None)
                    )
                    template.add_resource(eventSourceMapping)

    return template
