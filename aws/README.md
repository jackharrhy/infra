# AWS

Account separation is prepared in [foundation](foundation/README.md) and
[production mail](mail/README.md). These use separate project/stack states in
the same local backend. The root project below remains the live mail owner
until the reviewed migration and retirement are complete.

Pulumi manages SES sending identities/events and inbound mail:
SES → S3 → Lambda → SQS → the `lists` service on Mug. Campaign media uses a
separate public S3 bucket. Resources are in `index.ts`.

```sh
npm run pulumi:preview
npm run pulumi:up
```

These scripts load `.env`, use the project-local `.pulumi` backend, and select
`dev`. Region defaults to `us-east-1`.

## Mail DNS

The `jackharrhy.dev` and `siliconharbour.dev` zones have SES DKIM, `mail.*`
MAIL FROM records, and enforcing DMARC. Reports go to `reports@dmarc.<domain>`
for the `lists` dashboard.

`jackharrhy.com` uses Zoho MX/SPF; its zone has no DKIM or DMARC record.
Zoho Mail's domain settings supply its DKIM selector and record.
