import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/aws";

const config = new pulumi.Config();
const managementId = config.require("managementAccountId");
if (
  !/^\d{12}$/.test(managementId) ||
  aws.config.allowedAccountIds?.length !== 1 ||
  aws.config.allowedAccountIds[0] !== managementId
) {
  throw new Error(
    "Set aws:allowedAccountIds to exactly the managementAccountId before running this project",
  );
}
if (!aws.config.profile || aws.config.region !== "us-east-1") {
  throw new Error("Select an explicit AWS profile and us-east-1 for the foundation project");
}
const instanceArn = config.require("ssoInstanceArn");
const ownerUserId = config.require("ownerUserId");
const permissionSetArn = config.require("ownerPermissionSetArn");

const production = new aws.organizations.Account(
  "production",
  {
    name: "jack-production",
    email: config.requireSecret("productionEmail"),
    closeOnDeletion: false,
    tags: { Project: "foundation", Environment: "production", ManagedBy: "pulumi" },
  },
  { protect: true },
);
const sandbox = new aws.organizations.Account(
  "sandbox",
  {
    name: "jack-sandbox",
    email: config.requireSecret("sandboxEmail"),
    closeOnDeletion: false,
    tags: { Project: "foundation", Environment: "sandbox", ManagedBy: "pulumi" },
  },
  { protect: true },
);

const permission = new aws.ssoadmin.PermissionSet(
  "owner",
  {
    instanceArn,
    name: "JackAdministratorAccess",
    sessionDuration: "PT12H",
  },
  { protect: true, import: `${permissionSetArn},${instanceArn}` },
);
const policy = new aws.ssoadmin.ManagedPolicyAttachment(
  "owner-administrator",
  {
    instanceArn,
    permissionSetArn: permission.arn,
    managedPolicyArn: "arn:aws:iam::aws:policy/AdministratorAccess",
  },
  {
    protect: true,
    import: `arn:aws:iam::aws:policy/AdministratorAccess,${permissionSetArn},${instanceArn}`,
  },
);
for (const [name, accountId] of [
  ["management", pulumi.output(managementId)],
  ["production", production.id],
  ["sandbox", sandbox.id],
] as const) {
  new aws.ssoadmin.AccountAssignment(
    `owner-${name}`,
    {
      instanceArn,
      permissionSetArn: permission.arn,
      principalId: ownerUserId,
      principalType: "USER",
      targetId: accountId,
      targetType: "AWS_ACCOUNT",
    },
    {
      protect: true,
      dependsOn: [policy],
      import:
        name === "management"
          ? `${ownerUserId},USER,${managementId},AWS_ACCOUNT,${permissionSetArn},${instanceArn}`
          : undefined,
    },
  );
}

export const managementAccountId = managementId;
export const productionAccountId = production.id;
export const sandboxAccountId = sandbox.id;
