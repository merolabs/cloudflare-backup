# Cloudflare Backup

This simple application can make a backup from Cloudflare accounts.

## Requirements

* Python version - 3.6+.
* Python modules - in file `requirements.txt`

## Config

Supported export formats:
* json
* yaml

### Example config

```yaml
cloudflare:
  token: "<you access token>"
export:
  zones:
    json: "/backup/cloudflare/zones/json"
    yaml: "/backup/cloudflare/zones/yaml"
```
