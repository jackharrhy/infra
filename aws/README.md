# jack-infra

preview and deploy:

```bash
pulumi preview
pulumi up
```

tear down:

```bash
pulumi destroy
pulumi stack rm
```

| Key          | Description                             | Default     |
| ------------ | --------------------------------------- | ----------- |
| `aws:region` | The AWS region to deploy resources into | `us-east-1` |

`pulumi config set <key> <value>` to customize config.
