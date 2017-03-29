from troposphere.awslambda import Function, Code, Permission, VPCConfig, Environment
from troposphere.apigateway import RestApi, Resource, Method, Integration, Deployment, IntegrationResponse, \
    MethodResponse
from AWSObject import AWSObject
from troposphere.events import Rule, Target
from troposphere import FindInMap, GetAtt, Join, Output
from troposphere import Parameter, Ref, Template
from distutils.util import strtobool
import uuid
import re
import json

regex = re.compile('[^a-zA-Z0-9]')


def getRequestTemplate(params):
    template = "{\n"
    for idx, val in enumerate(params):
        template += "\"" + val + "\": \"$input.params('" + val + "')\""
        if idx < len(params) - 1:
            template += ",\n"

    template += "\n}"
    retVal = {
        "application/json": template
    }
    return retVal


def getIntegration(params, isAsynchronous=False, func=None, isCors=False):
    if isCors:
        integrationParameters = {
            'Type': "MOCK",
            'IntegrationResponses': [
                IntegrationResponse(
                    StatusCode='200',
                    ResponseParameters={
                        "method.response.header.Access-Control-Allow-Headers": '\'Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token\'',
                        "method.response.header.Access-Control-Allow-Methods": '\'DELETE,GET,HEAD,OPTIONS,PATCH,POST,PUT\'',
                        "method.response.header.Access-Control-Allow-Origin": '\'*\'',
                    }
                )
            ],
            'RequestTemplates': {
                "application/json": '{\"statusCode\": 200}'
            },
        }
    elif isAsynchronous and str(params['HttpMethod']).upper() == 'GET':
        integrationParameters = {
            'Type': "AWS",
            'Credentials': Join("", ["arn:aws:iam::", Ref("AWS::AccountId"), ":", "role/",
                                     params['Role']]),
            'IntegrationHttpMethod': "POST",
            'Uri': Join("", ["arn:aws:apigateway:us-east-1:lambda:path/",
                             params['Uri']]),
            'IntegrationResponses': [
                IntegrationResponse(
                    StatusCode='200'
                )
            ],
            'RequestTemplates': getRequestTemplate(
                params['UrlQueryStringParameters']) if str(
                params['HttpMethod']).upper() == 'GET' else None,
            'RequestParameters': {
                "integration.request.header.X-Amz-Invocation-Type": '\'Event\''
            }
        }
    elif isAsynchronous:
        integrationParameters = {
            'Type': "AWS",
            'Credentials': Join("", ["arn:aws:iam::", Ref("AWS::AccountId"), ":", "role/",
                                     params['Role']]),
            # IntegrationHttpMethod=str(parameters['HttpMethod']).upper(),
            'IntegrationHttpMethod': "POST",
            'Uri': Join("", ["arn:aws:apigateway:us-east-1:lambda:path/",
                             params['Uri']]),
            'IntegrationResponses': [
                IntegrationResponse(
                    StatusCode='200'
                )
            ],
            'RequestParameters': {
                "integration.request.header.X-Amz-Invocation-Type": '\'Event\''
            }
        }
    elif str(params['HttpMethod']).upper() == 'GET':
        integrationParameters = {
            'Type': "AWS",
            'IntegrationHttpMethod': "POST",
            'Uri': Join("",
                        ["arn:aws:apigateway:", Ref("AWS::Region"),
                         ":lambda:path/2015-03-31/functions/",
                         GetAtt(func, "Arn"), "/invocations"]),
            'RequestTemplates': getRequestTemplate(
                params['UrlQueryStringParameters']) if str(
                params['HttpMethod']).upper() == 'GET' and 'UrlQueryStringParameters' in params else None,
            'IntegrationResponses': [
                IntegrationResponse(
                    StatusCode='200'
                )
            ],
        }
    else:
        integrationParameters = {
            'Type': "AWS",
            # IntegrationHttpMethod=str(parameters['HttpMethod']).upper(),
            'IntegrationHttpMethod': "POST",
            'Uri': Join("",
                        ["arn:aws:apigateway:", Ref("AWS::Region"),
                         ":lambda:path/2015-03-31/functions/",
                         GetAtt(func, "Arn"), "/invocations"]),
            'IntegrationResponses': [
                IntegrationResponse(
                    StatusCode='200'
                )
            ],
        }

    return Integration(
        **dict((k, v) for k, v in integrationParameters.iteritems() if v is not None)
    )




def getCode(function, defaults):
    if 'Code' in function and 'S3Bucket' in function['Code'] and 'S3Key' in function['Code']:
        code = Code(
            S3Bucket=function['Code']['S3Bucket'],
            S3Key=function['Code']['S3Key']
        )
    elif 'Code' in function and 'ZipFile' in function['Code']:
        code = Code(
            ZipFile=function['Code']['ZipFile']
        )
    else:
        code = Code(
            ZipFile=defaults.get('DEFAULT', 'Code')
        )
    return code


def getVpcConfig(function, defaults):
    vpcConfig = None
    if 'VpcConfig' in function and str(function['VpcConfig']).lower().strip() == "true":
        vpcConfig = VPCConfig(
            SecurityGroupIds=(defaults.get('DEFAULT', 'LambdaSecurityGroupIds')).split(','),
            SubnetIds=(defaults.get('DEFAULT', 'LambdaSubnetIds')).split(',')
        )
    elif 'VpcConfig' in function and str(function['VpcConfig']).lower().strip() != "false":
        vpcConfig = VPCConfig(
            SecurityGroupIds=function['VpcConfig']['SecurityGroupIds'].split(','),
            SubnetIds=function['VpcConfig']['SubnetIds'].split(',')
        )
    return vpcConfig


def awslambda(item, template, defaults, G):
    if 'Functions' in item:
        for function in item['Functions']:
            functionId = regex.sub("", function['FunctionName'])
            parameters = {
                "FunctionName": function['FunctionName'],
                "Description": function['Description'] if 'Description' in function else None,
                "Code": getCode(function, defaults=defaults),
                "Handler": function[
                    'Handler'] if 'Handler' in function else 'index.handler',
                "Environment": Environment(
                    Variables={key: value for key, value in
                               list(function["Environment"]["Variables"].items())}
                ) if 'Environment' in function else None,
                "VpcConfig": getVpcConfig(function, defaults=defaults),
                "Role": Join("",
                             ["arn:aws:iam::",
                              Ref(
                                  "AWS::AccountId"),
                              ":role/",
                              function['Role']]),
                "Runtime": function[
                    'Runtime'] if 'Runtime' in function else defaults.get(
                    "DEFAULT", "LambdaRuntime"),
                "MemorySize":
                    function['MemorySize'] if 'MemorySize' in function else defaults.get("DEFAULT", "LambdaMemorySize"),
                "Timeout": str(function['Timeout']) if 'Timeout' in function else defaults.get("DEFAULT", "Timeout")
            }
            func = Function(
                functionId + item['Protocol'],
                **dict((k, v) for k, v in parameters.iteritems() if v is not None)
            )

            funcObj = AWSObject(functionId + item['Protocol'], func)

            if G.has_node(AWSObject(functionId + item['Protocol'])):
                for node in G.nodes():
                    if str(node) == functionId + item['Protocol']:
                        node.troposphereResource = func
                        break
            else:
                G.add_node(funcObj)

            if 'Poller' in function:
                pollerId = functionId + 'Poller'
                permissionId = pollerId + 'Permission'
                poller = Rule(
                    pollerId,
                    Name=function['FunctionName'] + 'Poller',
                    Description=function['FunctionName'] + " Poller",
                    ScheduleExpression="rate(" + str(function['Poller']['Rate']) + ")",
                    State="ENABLED",
                    Targets=[Target(
                        Arn=GetAtt(func, "Arn"),
                        Id=functionId
                    )],
                )
                permission = Permission(
                    permissionId,
                    Action="lambda:InvokeFunction",
                    Principal="events.amazonaws.com",
                    SourceArn=GetAtt(poller, "Arn"),
                    FunctionName=Ref(func)
                )
                poll = AWSObject(pollerId, poller)
                perm = AWSObject(permissionId, permission)
                G.add_node(poll)
                G.add_node(perm)
                G.add_edge(poll, funcObj)
                G.add_edge(perm, funcObj)
                G.add_edge(perm, poll)
            if 'Api' in function:
                if str(function['Api']['Path']).startswith('/'):
                    function['Api']['Path'] = str(function['Api']['Path'])[1:]
                if str(function['Api']['Path']).endswith('/'):
                    function['Api']['Path'] = str(function['Api']['Path'])[:-1]
                parameters = {
                    'RestApi': function['Api']['RestApi'],
                    'Path': function['Api']['Path'],
                    'HttpMethod': function['Api']['HttpMethod'],
                    'Asynchronous': function['Api']['Asynchronous'] if 'Asynchronous' in function['Api'] else 'false',
                    'Role': function['Api']['Role'] if 'Role' in function['Api'] else None,
                    'AuthorizationType': function['Api']['AuthorizationType'] if 'AuthorizationType' in function[
                        'Api'] else defaults.get('DEFAULT', 'AuthorizationType'),
                    'Uri': function['Api']['Uri'] if 'Uri' in function['Api'] else None,
                    'StageName': function['Api']['StageName'],
                    'UrlQueryStringParameters': function['Api'][
                        'UrlQueryStringParameters'] if 'UrlQueryStringParameters' in function[
                        'Api'] else None,
                    'RequestParameters': function['Api'][
                        'RequestParameters'] if 'RequestParameters' in function[
                        'Api'] else None,
                    'IntegrationRequestTemplates': function['Api'][
                        'IntegrationRequestTemplates'] if 'IntegrationRequestTemplates' in function[
                        'Api'] else None,
                    'Cors': function['Api']['Cors'] if 'Cors' in function['Api'] else None,
                }

                restApiObj = None
                if 'Name' in parameters['RestApi']:
                    restApiId = regex.sub("", function['Api']['RestApi']["Name"]) + 'api'
                    restApi = RestApi(
                        restApiId,
                        Name=function['Api']['RestApi']["Name"],
                    )
                    restApiObj = AWSObject(restApiId, restApi, function['Api']['RestApi']["Name"])
                    apiId = Ref(restApi)
                    resourceId = GetAtt(restApi, "RootResourceId")
                else:
                    apiId = str(function['Api']['RestApi']['Id'])
                    resourceId = str(function['Api']['RestApi']["ResourceId"])

                apiResourceObj = None
                apiResource = None
                pathToMethod = ""
                if 'Path' in parameters:
                    for i, path in enumerate(str(parameters['Path']).split('/')):
                        pathToMethod = "/" + path
                        apiResourceId = regex.sub("", path) + 'Path'
                        apiParameters = {
                            "RestApiId": apiId,
                            "ParentId": resourceId if i == 0 else Ref(apiResource),
                            "PathPart": path.replace("/", ""),
                        }
                        apiResource = Resource(
                            apiResourceId,
                            **dict((k, v) for k, v in apiParameters.iteritems() if v is not None)
                        )
                        apiResourceObj = AWSObject(apiResourceId, apiResource, regex.sub("", path))
                        G.add_node(apiResourceObj)

                        if i == 0:
                            if restApiObj is not None:
                                G.add_edge(apiResourceObj, restApiObj)
                        else:
                            prevPath = str(parameters['Path']).split('/')[i - 1]
                            G.add_edge(apiResourceObj, AWSObject(regex.sub("", prevPath) + 'Path'))

                corsMethodObj = None
                if str(parameters['Cors']).lower() == 'true':
                    corsMethodParameters = {
                        "RestApiId": apiId,
                        "ResourceId": resourceId if apiResource is None else Ref(apiResource),
                        "HttpMethod": 'OPTIONS',
                        "AuthorizationType": 'NONE',
                        "Integration": getIntegration(parameters, isCors=True),
                        "MethodResponses": [
                            MethodResponse(
                                StatusCode='200',
                                ResponseParameters={
                                    'method.response.header.Access-Control-Allow-Headers': True,
                                    'method.response.header.Access-Control-Allow-Methods': True,
                                    'method.response.header.Access-Control-Allow-Origin': True,
                                }
                            )
                        ],
                    }
                    corsMethodId = regex.sub("", pathToMethod) + 'Cors'
                    corsMethod = Method(
                        corsMethodId,
                        **dict((k, v) for k, v in corsMethodParameters.iteritems() if v is not None)
                    )
                    corsMethodObj = AWSObject(corsMethodId, corsMethod, pathToMethod + 'CorsMethod')

                if str(parameters['Asynchronous']).lower() == 'true':
                    methodParameters = {
                        "RestApiId": apiId,
                        "ResourceId": resourceId if apiResource is None else Ref(apiResource),
                        "HttpMethod": str(parameters['HttpMethod']).upper(),
                        "AuthorizationType": parameters['AuthorizationType'],
                        "Integration": getIntegration(parameters, isAsynchronous=True, func=func),
                        "MethodResponses": [
                            MethodResponse(
                                StatusCode='200'
                            )
                        ],
                    }
                else:
                    methodParameters = {
                        "RestApiId": apiId,
                        "ResourceId": resourceId if apiResource is None else Ref(apiResource),
                        "HttpMethod": str(parameters['HttpMethod']).upper(),
                        "AuthorizationType": parameters['AuthorizationType'],
                        "Integration": getIntegration(parameters, isAsynchronous=False, func=func),
                        "RequestParameters": dict(
                            ("method.request.querystring." + (v if 'Name' not in v else v),
                             bool(strtobool(defaults.get('DEFAULT', 'QueryStringRequired')))
                             if 'Required' not in v else bool(strtobool(str(v))))
                            for v in parameters['UrlQueryStringParameters'])
                        if parameters['UrlQueryStringParameters'] != None else None,
                        "RequestTemplates": parameters['RequestParameters'],
                        "MethodResponses": [
                            MethodResponse(
                                StatusCode='200'
                            )
                        ],
                    }
                methodId = regex.sub("", pathToMethod + parameters['HttpMethod']) + 'Method'
                method = Method(
                    methodId,
                    **dict((k, v) for k, v in methodParameters.iteritems() if v is not None)
                )
                methodObj = AWSObject(methodId, method,
                                      apiResourceObj.label + '-' + str(parameters['HttpMethod']).upper())

                deploymentId = regex.sub("", str(apiId) + str(uuid.uuid4())) + 'Deployment'
                deploymentParameters = {
                    "RestApiId": apiId,
                    "StageName": parameters['StageName'],
                    "Description": parameters['Description'] if 'Description' in parameters else None,
                }
                deployment = Deployment(
                    deploymentId,
                    **dict((k, v) for k, v in deploymentParameters.iteritems() if v is not None)
                )
                deploymentObj = AWSObject(deploymentId, deployment, parameters['StageName'] + "-Deployment")

                permissionId = regex.sub("", parameters['Path']) + parameters['HttpMethod'] + 'Path' + 'Permission'
                permission = Permission(
                    permissionId,
                    Action="lambda:InvokeFunction",
                    Principal="apigateway.amazonaws.com",
                    SourceArn=Join("", ["arn:aws:execute-api:", Ref("AWS::Region"), ":", Ref("AWS::AccountId"), ":",
                                        apiId, "/*/", parameters['HttpMethod'], "/",
                                        str(parameters['Path'])]),
                    FunctionName=Ref(func),
                )
                permissionObj = AWSObject(permissionId, permission, "InvokeFunctionPermission")

                G.add_node(methodObj)
                G.add_node(permissionObj)
                G.add_node(deploymentObj)
                if corsMethodObj is not None:
                    G.add_node(corsMethodObj)

                G.add_edge(methodObj, apiResourceObj)
                G.add_edge(deploymentObj, methodObj)
                G.add_edge(permissionObj, methodObj)
                G.add_edge(permissionObj, funcObj)

                if corsMethodObj is not None:
                    print('HERE')
                    G.add_edge(corsMethodObj, apiResourceObj)
                    G.add_edge(deploymentObj, corsMethodObj)
                if restApiObj is not None:
                    G.add_edge(permissionObj, restApiObj)
