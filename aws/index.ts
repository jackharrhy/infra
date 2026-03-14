import * as aws from "@pulumi/aws";

const { accountId } = aws.getCallerIdentityOutput();

const configSet = new aws.sesv2.ConfigurationSet("jackharrhy-dev-config-set", {
  configurationSetName: "jackharrhy-dev-config-set",
  deliveryOptions: {
    tlsPolicy: "OPTIONAL",
  },
  reputationOptions: {
    reputationMetricsEnabled: true,
  },
  sendingOptions: {
    sendingEnabled: true,
  },
});

new aws.sesv2.EmailIdentity("jackharrhy-dev", {
  emailIdentity: "jackharrhy.dev",
  configurationSetName: configSet.configurationSetName,
  dkimSigningAttributes: {
    nextSigningKeyLength: "RSA_2048_BIT",
  },
});

new aws.sesv2.EmailIdentity("siliconharbour-dev", {
  emailIdentity: "siliconharbour.dev",
  configurationSetName: configSet.configurationSetName,
  dkimSigningAttributes: {
    nextSigningKeyLength: "RSA_2048_BIT",
  },
});

const sesEventsTopic = new aws.sns.Topic("ses-events", {
  name: "ses-events",
  policy: accountId.apply((id) =>
    JSON.stringify({
      Version: "2008-10-17",
      Statement: [
        {
          Sid: "stmt1772834748858",
          Effect: "Allow",
          Principal: { Service: "ses.amazonaws.com" },
          Action: "SNS:Publish",
          Resource: `arn:aws:sns:us-east-1:${id}:ses-events`,
          Condition: {
            StringEquals: { "AWS:SourceAccount": id },
            StringLike: { "AWS:SourceArn": "arn:aws:ses:*" },
          },
        },
      ],
    }),
  ),
});

new aws.sns.TopicSubscription("ses-events-subscription", {
  topic: sesEventsTopic.arn,
  protocol: "https",
  endpoint: "https://lists.jackharrhy.dev/webhooks/service/ses",
  confirmationTimeoutInMinutes: 1,
  endpointAutoConfirms: false,
});

new aws.sesv2.ConfigurationSetEventDestination("ses-events-destination", {
  configurationSetName: configSet.configurationSetName,
  eventDestinationName: "ses-events",
  eventDestination: {
    enabled: true,
    matchingEventTypes: ["BOUNCE", "COMPLAINT"],
    snsDestination: {
      topicArn: sesEventsTopic.arn,
    },
  },
});

const sesSmtpUser = new aws.iam.User("listmonk-ses-smtp", {
  name: "listmonk-ses-smtp",
});

const sesSendingGroup = new aws.iam.Group("AWSSESSendingGroupDoNotRename", {
  name: "AWSSESSendingGroupDoNotRename",
});

new aws.iam.GroupPolicy("AmazonSesSendingAccess", {
  group: sesSendingGroup.name,
  name: "AmazonSesSendingAccess",
  policy: JSON.stringify({
    Version: "2012-10-17",
    Statement: [
      {
        Effect: "Allow",
        Action: "ses:SendRawEmail",
        Resource: "*",
      },
    ],
  }),
});

new aws.iam.UserGroupMembership("listmonk-ses-smtp-membership", {
  user: sesSmtpUser.name,
  groups: [sesSendingGroup.name],
});
