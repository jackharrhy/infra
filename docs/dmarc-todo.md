# DMARC/DKIM status

DMARC aggregate reporting for the newsletter domains is handled by the `lists`
service through SES inbound email, S3, SQS, and its DMARC dashboard.

## jackharrhy.com

**Current state:** MX points to Zoho (`mx.zohomail.com`, `mx2.zoho.com`), SPF includes `zoho.com`.

**Missing:**

- **DKIM** -- Zoho provides CNAME records for DKIM signing. These need to be retrieved from the Zoho admin panel (Settings > Mail > Domain > DomainKeys) and added as CNAME records in the zone file.
- **DMARC** -- No `_dmarc` TXT record exists. Once DKIM is in place, add:
  ```
  _dmarc:
    type: TXT
    value: "v=DMARC1; p=quarantine;"
  ```

**Steps:**

1. Log into Zoho Mail admin, go to domain DKIM settings
2. Generate or retrieve the DKIM selector and CNAME value
3. Add the DKIM CNAME record(s) to `dns/zones/jackharrhy.com.yaml`
4. Add the `_dmarc` TXT record
5. `infra dns diff` to verify, `infra dns sync` to apply
6. Verify with `dig TXT _dmarc.jackharrhy.com` and an email test service

## Newsletter domains

`jackharrhy.dev` and `siliconharbour.dev` both have SES Easy DKIM, custom
`mail.*` MAIL FROM MX/SPF records, and enforcing DMARC policies. Aggregate
reports are delivered to `reports@dmarc.<domain>` and ingested by `lists`.
