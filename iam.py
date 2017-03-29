from troposphere.iam import Role, User, ManagedPolicy, Policy as Pol
from awacs.aws import Action, Allow, Policy, Statement, Condition, AWSPrincipal, Bool, Principal
from troposphere import Ref, Join
from AWSObject import AWSObject
import re

regex = re.compile('[^a-zA-Z0-9]')

def principalArn(principal):
    if principal["Owner"] == "User":
        return AWSPrincipal([Join("", ["arn:aws:iam::", Ref("AWS::AccountId"), ":user/", user]) for user in
                principal["Name"]])
    elif principal["Owner"] == "CanonicalUser":
        return AWSPrincipal([Join("", ["arn:aws:iam::", Ref("AWS::AccountId"), ":user/", user]) for user in
                principal["Name"]])
    elif principal["Owner"] == "Account":
        return AWSPrincipal([Join("", ["arn:aws:iam::", accountId, ":root"]) for accountId in principal["Name"]])
    elif principal["Owner"] == "Role":
        return AWSPrincipal([Join("", ["arn:aws:iam::", Ref("AWS::AccountId"), ":role/", role]) for role in
                principal["Name"]])
    elif principal["Owner"] == "Service":
        return Principal("Service", [str(principal["Name"])])
    elif principal["Owner"] == "Federated":
        return Principal("Federated",
                         [Join("", ["arn:aws:iam::", Ref("AWS::AccountId"), ":user/", federated]) for federated in
                          principal["Name"]])
    elif principal["Owner"] == "Custom":
        return Principal("Federated",
                         [Join("", ["arn:aws:iam::", Ref("AWS::AccountId"), ":user/", federated]) for federated in
                          principal["Name"]])


def resourceArn(resource):
    if resource['Service'] == "All":
        return "*"
    elif resource['Service'] == "s3":
        return "arn:aws:s3:::" +  resource["Resource"]
    elif resource['Service'] == "execute-api":
        return "arn:aws:execute-api:" + resource["Resource"]
    elif resource['Service'] == "iam":
        return Join("", ["arn:aws:", resource["Service"], ":", Ref("AWS::AccountId"), ":",
                         resource["Resource"]])
    else:
        return Join("", ["arn:aws:", resource["Service"], ":", Ref("AWS::Region"), ":", Ref("AWS::AccountId"), ":", resource["Resource"]])


def getActions(statement):
    if "Actions" in statement:
        return [Action(action.split(":")[0], action.split(":")[1]) for action in statement["Actions"]]
    elif "Action" in statement:
        return [Action(statement["Action"].split(":")[0], statement["Action"].split(":")[1])]


def getStatement(statement):
    parameters = {
        "Sid": statement["Sid"] if "Sid" in statement else None,
        "Effect": statement["Effect"] if "Effect" in statement else Allow,
        "Principal": principalArn(statement["Principal"]) if "Principal" in statement else None,
        "Action": getActions(statement) if "Action" or "Actions" in statement else None,
        "Resource": [resourceArn(resource) for resource in
                     statement["Resources"]] if "Resources" in statement else None
    }
    return Statement(**dict((k, v) for k, v in parameters.iteritems() if v is not None))




def policy(statements):
    return Policy(
        Statement=[getStatement(statement) for statement in statements["Statements"]]
    )


def iam(item, G, defaults):
    if 'Roles' in item:
        for role in item['Roles']:
            parameters = {
                "AssumeRolePolicyDocument": policy(role["AssumeRole"]),
                "ManagedPolicyArns": [
                    Join("", ["arn:aws:iam::", Ref("AWS::AccountId"), ":", "role/",
                              managedPolicy]) for managedPolicy
                    in
                    role["ManagedPolicies"]] if "ManagedPolicies" in role else None,
                "Path": role["Path"] if "Path" in role else None,
                "Policies": [
                    Pol(PolicyName=pol["Name"],
                        PolicyDocument=policy(pol)) for pol in role["Policies"]
                    ],
                "RoleName": role["RoleName"]
            }
            roleId = regex.sub("", role['RoleName']) + "Role"
            roleRes = Role(
                roleId,
                **dict((k, v) for k, v in parameters.iteritems() if v is not None)
            )

            roleObj = AWSObject(roleId, roleRes, role["RoleName"])
            G.add_node(roleObj)