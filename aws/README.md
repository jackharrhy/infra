# AWS

Pulumi project for AWS resources.

Preview and deploy:

```bash
npm run pulumi:preview
npm run pulumi:up
```

These scripts load `.env`, use the project-local `.pulumi` backend, and select
the `dev` stack.

Tear down:

```bash
pulumi destroy
pulumi stack rm
```

Config:

- `aws:region`: AWS region, defaults to `us-east-1`

Set config with:

```bash
pulumi config set <key> <value>
```
