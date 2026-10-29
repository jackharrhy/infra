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
const instanceArn = config.get("ssoInstanceArn");
const ownerUserId = config.get("ownerUserId");
if (Boolean(instanceArn) !== Boolean(ownerUserId)) {
  throw new Error(
    "Set ssoInstanceArn and ownerUserId together after organization Identity Center is enabled",
  );
}
const emails = pulumi
  .all([config.requireSecret("productionEmail"), config.requireSecret("sandboxEmail")])
  .apply(([production, sandbox]) => {
    if (
      ![production, sandbox].every((v) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v)) ||
      production.toLowerCase() === sandbox.toLowerCase()
    ) {
      throw new Error(
        "Jack must supply distinct, valid recovery email addresses for production and sandbox",
      );
    }
    return { production, sandbox };
  });

const production = new aws.organizations.Account(
  "production",
  {
    name: config.get("productionName") ?? "jack-production",
    email: emails.apply((v) => v.production),
    closeOnDeletion: false,
    tags: { Project: "foundation", Environment: "production", ManagedBy: "pulumi" },
  },
  { protect: true },
);
const sandbox = new aws.organizations.Account(
  "sandbox",
  {
    name: config.get("sandboxName") ?? "jack-sandbox",
    email: emails.apply((v) => v.sandbox),
    closeOnDeletion: false,
    tags: { Project: "foundation", Environment: "sandbox", ManagedBy: "pulumi" },
  },
  { protect: true },
);

if (instanceArn && ownerUserId) {
  const permission = new aws.ssoadmin.PermissionSet(
    "owner",
    {
      instanceArn,
      name: "JackAdministrator",
      sessionDuration: "PT4H",
      description: "Jack's owner access, selected through an explicit account profile",
    },
    { protect: true },
  );
  const policy = new aws.ssoadmin.ManagedPolicyAttachment(
    "owner-administrator",
    {
      instanceArn,
      permissionSetArn: permission.arn,
      managedPolicyArn: "arn:aws:iam::aws:policy/AdministratorAccess",
    },
    { protect: true },
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
      { protect: true, dependsOn: [policy] },
    );
  }
}

export const managementAccountId = managementId;
export const productionAccountId = production.id;
export const sandboxAccountId = sandbox.id;
export const ownerAccessConfigured = Boolean(instanceArn && ownerUserId);
