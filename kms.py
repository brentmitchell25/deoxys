from troposphere.kms import Alias, Key
from troposphere import Ref, Join
from awacs.aws import Action, Allow, Policy, Statement, Condition, AWSPrincipal, Bool
import awacs.kms as KMS


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
                    Join("", ["arn:aws:iam::", Ref("AWS::AccountId"), ":", admin["Type"], "/", admin["Name"]]) for admin
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
                    Join("", ["arn:aws:iam::", Ref("AWS::AccountId"), ":", user["Type"], "/", user["Name"]]) for user
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
                                           Join("", ["arn:aws:iam::", Ref("AWS::AccountId"), ":", user["Type"], "/",
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


def kms(item, template, defaults):
    if 'Keys' in item:
        for key in item['Keys']:
            kmsKey = template.add_resource(Key(
                key["Alias"] + "Key",
                Description=key['Description'] if 'Description' in key else Ref('AWS::NoValue'),
                Enabled=key['Enabled'] if 'Enabled' in key else defaults.getboolean('DEFAULT', 'KmsEnabled'),
                EnableKeyRotation=key['EnableKeyRotation'] if 'EnableKeyRotation' in key else defaults.getboolean('DEFAULT',
                    'KmsEnableKeyRotation'),
                KeyPolicy=defaultKeyPolicy(key['KeyAdmins'], key['KeyUsers']),
                # DeletionPolicy=key['DeletionPolicy'] e
            ))
            alias = template.add_resource(Alias(
                key["Alias"]  + "Alias",
                AliasName=key["Alias"],
                TargetKeyId=Ref(kmsKey),
                # DeletionPolicy="Retain"
            ))

    return template
