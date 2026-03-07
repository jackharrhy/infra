# DMARC/DKIM gaps

Two domains have mail configured (MX + SPF) but are missing DKIM and DMARC records.

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

## siliconharbour.dev

**Current state:** MX points to Porkbun forwarding (`fwd1.porkbun.com`, `fwd2.porkbun.com`), SPF includes `_spf.porkbun.com`.

**Missing:**

- **DKIM** -- Porkbun's email forwarding may not support outbound DKIM signing. Check Porkbun's docs to see if they provide DKIM records for forwarded mail. If not, DKIM may not be applicable here (forwarding-only setup).
- **DMARC** -- No `_dmarc` TXT record. Even for forwarding-only, a DMARC record prevents spoofing. Add:
  ```
  _dmarc:
    type: TXT
    value: "v=DMARC1; p=reject;"
  ```
  Using `p=reject` is appropriate here if no legitimate mail is sent from this domain (only forwarded inbound).

**Steps:**

1. Check Porkbun for any DKIM configuration options
2. Add `_dmarc` TXT record to `dns/zones/siliconharbour.dev.yaml`
3. `infra dns diff` to verify, `infra dns sync` to apply
4. Verify with `dig TXT _dmarc.siliconharbour.dev`
