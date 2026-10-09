# AWS

Pulumi manages SES sending identities/events and the inbound mail pipeline:
SES → S3 → Lambda → SQS → the `lists` service on Mug. Campaign media uses a
separate public S3 bucket. Resource definitions are in `index.ts`.

```sh
npm run pulumi:preview
npm run pulumi:up
```

These scripts load `.env`, use the project-local `.pulumi` backend, and select
`dev`. Region defaults to `us-east-1`; set options with
`pulumi config set <key> <value>`.

## Mail DNS

The checked-in `jackharrhy.dev` and `siliconharbour.dev` zones have SES DKIM,
`mail.*` MAIL FROM records, and enforcing DMARC policies. Reports go to
`reports@dmarc.<domain>` for the `lists` dashboard.

`jackharrhy.com` uses Zoho MX/SPF, but its zone file has no DKIM or DMARC record.
Retrieve the DKIM selector and record from Zoho Mail's domain settings. Add it
and a `_dmarc` TXT record with `v=DMARC1; p=quarantine;` to
`dns/zones/jackharrhy.com.yaml` after DKIM works. Review with
`infra dns diff jackharrhy.com.` before `infra dns sync jackharrhy.com.`;
verify DNS and a signed test email afterward.
