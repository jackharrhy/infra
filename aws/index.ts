import * as pulumi from "@pulumi/pulumi";
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

const inboundEmailBucket = new aws.s3.Bucket("ses-inbound-email", {
  bucket: "jackharrhy-ses-inbound-email",
  forceDestroy: false,
});

new aws.s3.BucketPublicAccessBlock("ses-inbound-email-public-access-block", {
  bucket: inboundEmailBucket.id,
  blockPublicAcls: true,
  blockPublicPolicy: true,
  ignorePublicAcls: true,
  restrictPublicBuckets: true,
});

new aws.s3.BucketPolicy("ses-inbound-email-policy", {
  bucket: inboundEmailBucket.id,
  policy: pulumi.all([inboundEmailBucket.arn, accountId]).apply(([bucketArn, id]) =>
    JSON.stringify({
      Version: "2012-10-17",
      Statement: [
        {
          Sid: "AllowSESPut",
          Effect: "Allow",
          Principal: { Service: "ses.amazonaws.com" },
          Action: "s3:PutObject",
          Resource: `${bucketArn}/*`,
          Condition: {
            StringEquals: { "AWS:SourceAccount": id },
          },
        },
      ],
    }),
  ),
});

const inboundEmailDLQ = new aws.sqs.Queue("ses-inbound-email-dlq", {
  name: "ses-inbound-email-dlq",
  messageRetentionSeconds: 1209600, // 14 days
});

const inboundEmailQueue = new aws.sqs.Queue("ses-inbound-email-queue", {
  name: "ses-inbound-email-queue",
  visibilityTimeoutSeconds: 60,
  messageRetentionSeconds: 345600, // 4 days
  redrivePolicy: inboundEmailDLQ.arn.apply((dlqArn) =>
    JSON.stringify({
      deadLetterTargetArn: dlqArn,
      maxReceiveCount: 3,
    }),
  ),
});

const inboundEmailLambdaRole = new aws.iam.Role("ses-inbound-email-lambda-role", {
  assumeRolePolicy: aws.iam.assumeRolePolicyForPrincipal({
    Service: "lambda.amazonaws.com",
  }),
});

new aws.iam.RolePolicyAttachment("ses-inbound-email-lambda-basic-execution", {
  role: inboundEmailLambdaRole.name,
  policyArn: aws.iam.ManagedPolicy.AWSLambdaBasicExecutionRole,
});

new aws.iam.RolePolicy("ses-inbound-email-lambda-sqs-write", {
  role: inboundEmailLambdaRole.name,
  policy: inboundEmailQueue.arn.apply((queueArn) =>
    JSON.stringify({
      Version: "2012-10-17",
      Statement: [
        {
          Effect: "Allow",
          Action: "sqs:SendMessage",
          Resource: queueArn,
        },
      ],
    }),
  ),
});

const inboundEmailLambda = new aws.lambda.CallbackFunction("ses-inbound-email-lambda", {
  role: inboundEmailLambdaRole,
  timeout: 30,
  memorySize: 128,
  environment: {
    variables: {
      SQS_QUEUE_URL: inboundEmailQueue.url,
    },
  },
  callback: async (event: any) => {
    const record = event.Records?.[0];
    if (!record?.ses) {
      console.error("No SES record found");
      return { disposition: "STOP_RULE" };
    }

    const mail = record.ses.mail;
    const receipt = record.ses.receipt;

    const payload = {
      messageId: mail.messageId,
      timestamp: mail.timestamp,
      source: mail.source,
      from: mail.commonHeaders?.from,
      to: mail.commonHeaders?.to,
      subject: mail.commonHeaders?.subject,
      spamVerdict: receipt.spamVerdict?.status,
      virusVerdict: receipt.virusVerdict?.status,
      spfVerdict: receipt.spfVerdict?.status,
      dkimVerdict: receipt.dkimVerdict?.status,
      dmarcVerdict: receipt.dmarcVerdict?.status,
      action: receipt.action,
    };

    const { SQSClient, SendMessageCommand } = require("@aws-sdk/client-sqs");
    const sqs = new SQSClient({});

    await sqs.send(
      new SendMessageCommand({
        QueueUrl: process.env.SQS_QUEUE_URL,
        MessageBody: JSON.stringify(payload),
        MessageAttributes: {
          messageId: {
            DataType: "String",
            StringValue: mail.messageId,
          },
        },
      }),
    );

    console.log(`Queued message ${mail.messageId}`);
    return { disposition: "CONTINUE" };
  },
});

new aws.lambda.Permission("ses-invoke-inbound-email-lambda", {
  action: "lambda:InvokeFunction",
  function: inboundEmailLambda.name,
  principal: "ses.amazonaws.com",
  sourceAccount: accountId,
});

const inboundRuleSet = new aws.ses.ReceiptRuleSet("ses-inbound-rule-set", {
  ruleSetName: "ses-inbound-rules",
});

new aws.ses.ActiveReceiptRuleSet("ses-inbound-active-rule-set", {
  ruleSetName: inboundRuleSet.ruleSetName,
});

new aws.ses.ReceiptRule("ses-inbound-receipt-rule", {
  name: "store-and-forward",
  ruleSetName: inboundRuleSet.ruleSetName,
  recipients: ["reply.jackharrhy.dev", "reply.siliconharbour.dev"],
  enabled: true,
  scanEnabled: true,
  s3Actions: [
    {
      bucketName: inboundEmailBucket.bucket,
      objectKeyPrefix: "inbound/",
      position: 1,
    },
  ],
  lambdaActions: [
    {
      functionArn: inboundEmailLambda.arn,
      invocationType: "Event",
      position: 2,
    },
  ],
});

const listsUser = new aws.iam.User("lists", {
  name: "lists",
});

new aws.iam.UserPolicy("lists-policy", {
  user: listsUser.name,
  policy: pulumi
    .all([inboundEmailQueue.arn, inboundEmailDLQ.arn, inboundEmailBucket.arn])
    .apply(([queueArn, dlqArn, bucketArn]) =>
      JSON.stringify({
        Version: "2012-10-17",
        Statement: [
          {
            Sid: "SQSRead",
            Effect: "Allow",
            Action: [
              "sqs:ReceiveMessage",
              "sqs:DeleteMessage",
              "sqs:GetQueueAttributes",
              "sqs:ChangeMessageVisibility",
            ],
            Resource: [queueArn, dlqArn],
          },
          {
            Sid: "S3Read",
            Effect: "Allow",
            Action: ["s3:GetObject"],
            Resource: `${bucketArn}/*`,
          },
          {
            Sid: "SESSend",
            Effect: "Allow",
            Action: ["ses:SendRawEmail", "ses:SendEmail"],
            Resource: "*",
          },
        ],
      }),
    ),
});
