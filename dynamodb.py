from troposphere.dynamodb import ProvisionedThroughput, Table, AttributeDefinition, KeySchema, GlobalSecondaryIndex, \
    LocalSecondaryIndex, Projection, StreamSpecification
from troposphere import Ref, Join, GetAtt
from troposphere.awslambda import EventSourceMapping
from awacs.aws import Principal
import awacs.awslambda as awslambda
from AWSObject import AWSObject
import re

regex = re.compile('[^a-zA-Z0-9]')


def keySchema(keySchemas, defaults):
    return [KeySchema(AttributeName=keySchema["AttributeName"],
                      KeyType=keySchema["KeyType"] if "KeyType" in keySchema else defaults.get("DEFAULT",
                                                                                               "AttributeType")) for
            keySchema in
            keySchemas]


def dynamodb(item, G, defaults):
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
                    KeySchema=keySchema(globalSecondaryIndex["KeySchema"], defaults=defaults),
                    Projection=Projection(
                        NonKeyAttributes=globalSecondaryIndex["Projection"]["NonKeyAttributes"],
                        ProjectionType=globalSecondaryIndex["Projection"]["ProjectionType"]
                    ),
                    ProvisionedThroughput=ProvisionedThroughput(
                        ReadCapacityUnits=int(globalSecondaryIndex["ProvisionedThroughput"][
                                                  "ReadCapacityUnits"] if "ProvisionedThroughput" in globalSecondaryIndex and "ReadCapacityUnits" in
                                                                                                                              globalSecondaryIndex[
                                                                                                                                  "ProvisionedThroughput"] else
                                              defaults.get("DEFAULT", "ReadCapacityUnits")),
                        WriteCapacityUnits=int(globalSecondaryIndex["ProvisionedThroughput"][
                                                   "WriteCapacityUnits"] if "ProvisionedThroughput" in globalSecondaryIndex and "WriteCapacityUnits" in
                                                                                                                                globalSecondaryIndex[
                                                                                                                                    "ProvisionedThroughput"] else
                                               defaults.get("DEFAULT", "WriteCapacityUnits"))
                    )
                ) for globalSecondaryIndex in table] if "GlobalSecondaryIndexes" in table else None,
                "KeySchema": keySchema(table["KeySchema"], defaults=defaults),
                "LocalSecondaryIndexes": [LocalSecondaryIndex(
                    IndexName=localSecondaryIndex["IndexName"],
                    KeySchema=keySchema(localSecondaryIndex["KeySchema"], defaults=defaults),
                    Projection=Projection(
                        NonKeyAttributes=localSecondaryIndex["Projection"]["NonKeyAttributes"],
                        ProjectionType=localSecondaryIndex["Projection"]["ProjectionType"]
                    )
                ) for localSecondaryIndex in table] if "LocalSecondaryIndexes" in table else None,
                "ProvisionedThroughput": ProvisionedThroughput(
                    ReadCapacityUnits=int(table["ProvisionedThroughput"][
                                              "ReadCapacityUnits"] if "ProvisionedThroughput" in table and "ReadCapacityUnits" in
                                                                                                           table[
                                                                                                               "ProvisionedThroughput"] else
                                          defaults.get("DEFAULT", "ReadCapacityUnits")),
                    WriteCapacityUnits=int(table["ProvisionedThroughput"][
                                               "WriteCapacityUnits"] if "ProvisionedThroughput" in table and "WriteCapacityUnits" in
                                                                                                             table[
                                                                                                                 "ProvisionedThroughput"] else
                                           defaults.get("DEFAULT", "WriteCapacityUnits")),

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
            tableObj = AWSObject(tableId, tableResource)
            G.add_node(tableObj)

            if "Triggers" in table:
                for trigger in table["Triggers"]:
                    parameters = {
                        "BatchSize": int(trigger["BatchSize"]) if "BatchSize" in trigger else None,
                        "Enabled": bool(trigger["Enabled"]) if "Enabled" in trigger else None,
                        "EventSourceArn": GetAtt(tableResource, "StreamArn"),
                        "FunctionName": trigger["FunctionName"] if "FunctionName" in trigger else trigger,
                        "StartingPosition": trigger[
                            "StartingPosition"] if "StartingPosition" in trigger else defaults.get("DEFAULT",
                                                                                                   "StartingPosition"),
                        "DependsOn": [tableId]
                    }
                    eventSourceMappingId = regex.sub("", trigger[
                            "FunctionName"] if "FunctionName" in trigger else trigger) + tableId + "EventSourceMapping"
                    eventSourceMapping = EventSourceMapping(
                        eventSourceMappingId,
                        **dict((k, v) for k, v in parameters.iteritems() if v is not None)
                    )
                    eventSourceMappingObj = AWSObject(eventSourceMappingId, eventSourceMapping)
                    G.add_node(tableObj, eventSourceMappingObj)
                    functionObj = AWSObject(trigger["FunctionName"] if "FunctionName" in trigger else trigger)
                    G.add_edge(eventSourceMappingObj, functionObj)

    return G
