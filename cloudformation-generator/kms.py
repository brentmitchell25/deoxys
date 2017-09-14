from troposphere.kms import Alias, Key
from troposphere import Ref, Join
from awacs.aws import Action, Allow, Policy, Statement, Condition, AWSPrincipal, Bool
import awacs.kms as KMS
import re

regex = re.compile('[^a-zA-Z0-9]')


def defaultKeyPolicy(admins, users):
    return Policy(
        Statement=[
            Statement(
                Sid="Enable IAM User Permissions",
                Effect=Allow,
                Principal=AWSPrincipal(Join("", ["arn:aws:iam::", Ref("AWS::AccountId"), ":root"])),
                Action=[Action("kms", "*")],
                Resource=["*"]
            ),
            Statement(
                Sid="Allow access for Key Administrators",
                Effect=Allow,
                Principal=AWSPrincipal([
                    Join("", ["arn:aws:iam::", Ref("AWS::AccountId"), ":", str(admin["Type"]).lower(), "/", admin["Name"]]) for admin
                    in
                    admins]),
                Action=[
                    Action("kms", "Create*"),
                    Action("kms", "Describe*"),
                    Action("kms", "Enable*"),
                    Action("kms", "List*"),
                    Action("kms", "Put*"),
                    Action("kms", "Update*"),
                    Action("kms", "Revoke*"),
                    Action("kms", "Disable*"),
                    Action("kms", "Get*"),
                    Action("kms", "Delete*"),
                    KMS.ScheduleKeyDeletion,
                    KMS.CancelKeyDeletion,
                ],
                Resource=["*"]
            ),
            Statement(
                Sid="Allow use of the key",
                Effect=Allow,
                Principal=AWSPrincipal([
                    Join("", ["arn:aws:iam::", Ref("AWS::AccountId"), ":", str(user["Type"]).lower(), "/", user["Name"]]) for user
                    in
                    users]),
                Action=[
                    KMS.Encrypt,
                    KMS.Decrypt,
                    Action("kms", "ReEncrypt*"),
                    Action("kms", "GenerateDataKey*"),
                    KMS.DescribeKey,
                ],
                Resource=["*"]
            ),
            Statement(
                Sid="Allow attachment of persistent resources",
                Effect=Allow,
                Principal=AWSPrincipal([
                                           Join("", ["arn:aws:iam::", Ref("AWS::AccountId"), ":", str(user["Type"]).lower(), "/",
                                                     user["Name"]]) for user
                                           in
                                           users]),
                Action=[
                    KMS.CreateGrant,
                    KMS.ListGrants,
                    KMS.RevokeGrant,
                ],
                Resource=["*"],
                Condition=Condition(
                    Bool("kms:GrantIsForAWSResource", "true")
                )
            ),
        ]
    )


def kms(item, G, defaults):
    if 'Keys' in item:
        for key in item['Keys']:
            kmsKeyId = regex.sub("", key["Alias"]) + "Key"
            kmsKey = Key(
                kmsKeyId,
                Description=key['Description'] if 'Description' in key else Ref('AWS::NoValue'),
                Enabled=key['Enabled'] if 'Enabled' in key else defaults.getboolean('DEFAULT', 'KmsEnabled'),
                EnableKeyRotation=key['EnableKeyRotation'] if 'EnableKeyRotation' in key else defaults.getboolean('DEFAULT',
                    'KmsEnableKeyRotation'),
                KeyPolicy=defaultKeyPolicy(key['KeyAdmins'], key['KeyUsers']),
            )

            aliasId = regex.sub("", key["Alias"])  + "Alias"
            alias = Alias(
                aliasId,
                AliasName=key["Alias"] if str(key["Alias"]).startswith("alias/")  else "alias/" + key["Alias"],
                TargetKeyId=Ref(kmsKey),
            )

            kmsKeyObj = AWSObject(kmsKeyId, kmsKey, "KMS-Key")
            aliasObj = AWSObject(aliasId, alias, key["Alias"])
            G.add_node(kmsKeyObj)
            G.add_node(aliasObj)
            G.add_edge(aliasObj, kmsKeyObj)
