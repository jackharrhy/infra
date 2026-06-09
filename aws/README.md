# AWS

Pulumi project for AWS resources.

Preview and deploy:

```bash
pulumi preview
pulumi up
```

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
