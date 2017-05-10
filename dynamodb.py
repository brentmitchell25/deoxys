from troposphere.dynamodb import ProvisionedThroughput, Table, AttributeDefinition, KeySchema, GlobalSecondaryIndex, \
    LocalSecondaryIndex, Projection, StreamSpecification
from troposphere import Ref, Join, GetAtt
from troposphere.awslambda import EventSourceMapping
from awacs.aws import Principal
import awacs.awslambda as awslambda
import re
import utilities
import matplotlib.image as mpimg

lambdaImg = './AWS_Simple_Icons/Compute/Compute_AWSLambda.png'
dynamodbImg = './AWS_Simple_Icons/Database/Database_AmazonDynamoDB_table.png'

regex = re.compile('[^a-zA-Z0-9]')


def keySchema(keySchemas, defaults):
    return [KeySchema(AttributeName=keySchema["AttributeName"],
                      KeyType=keySchema["KeyType"] if "KeyType" in keySchema else defaults.get("DEFAULT",
                                                                                               "AttributeType")) for
            keySchema in
            keySchemas]


def getProjection(projection):
    if "NonKeyAttributes" in projection and "ProjectionType" in projection:
        retVal = Projection(
            NonKeyAttributes=projection["NonKeyAttributes"],
            ProjectionType=projection["ProjectionType"],
        )
    elif "NonKeyAttributes" in projection:
        retVal = Projection(
            NonKeyAttributes=projection["NonKeyAttributes"],
        )
    else:
        retVal = Projection(
            ProjectionType=projection["ProjectionType"],
        )
    return retVal


def getAttributeDefinitions(table, defaults):
    if "AttributeDefinitions" in table:
        return [AttributeDefinition(AttributeName=attribute["AttributeName"],
                                    AttributeType=attribute["AttributeType"]) for attribute in
                table["AttributeDefinitions"]]

    return [AttributeDefinition(AttributeName=attribute["AttributeName"],
                                AttributeType=defaults.get("DEFAULT", "AttributeType")) for attribute in
            table["KeySchema"]]


def dynamodb(item, G, defaults):
    if 'Tables' in item:
        for table in item['Tables']:
            parameters = {
                "AttributeDefinitions": getAttributeDefinitions(table, defaults=defaults),
                "GlobalSecondaryIndexes": [GlobalSecondaryIndex(
                    IndexName=globalSecondaryIndex["IndexName"],
                    KeySchema=keySchema(globalSecondaryIndex["KeySchema"], defaults=defaults),
                    Projection=getProjection(globalSecondaryIndex["Projection"]),
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
                ) for globalSecondaryIndex in
                    table["GlobalSecondaryIndexes"]] if "GlobalSecondaryIndexes" in table else None,
                "KeySchema": keySchema(table["KeySchema"], defaults=defaults),
                "LocalSecondaryIndexes": [LocalSecondaryIndex(
                    IndexName=localSecondaryIndex["IndexName"],
                    KeySchema=keySchema(localSecondaryIndex["KeySchema"], defaults=defaults),
                    Projection=getProjection(localSecondaryIndex["Projection"]),
                ) for localSecondaryIndex in
                    table["LocalSecondaryIndexes"]] if "LocalSecondaryIndexes" in table else None,
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
            utilities.mergeNode(G, id=tableId, resource=tableResource, image=dynamodbImg,
                                name=table["TableName"])

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
                    utilities.mergeNode(G, id=eventSourceMappingId, resource=eventSourceMapping, image=lambdaImg,
                                        name="EventSourceMapping")

                    funcId = regex.sub("", trigger[
                                               "FunctionName"] + 'lambda' if "FunctionName" in trigger else trigger + 'lambda')

                    G.add_edge(eventSourceMappingId, tableId)
                    G.add_edge(eventSourceMappingId, funcId)
