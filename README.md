# Cloudflare Backup

This simple application can make a backup from Cloudflare accounts.

## Requirements

* Python version - 3.6+.
* Python modules - in file `requirements.txt`

## Config

Supported export formats:
* json
* yaml
* bind

### Example config

```yaml
cloudflare:
  token: "<you access token>"
export:
  zones:
    json:
      path: "/var/backup/cloudflare/zones/json"
    yaml:
      path: "/var/backup/cloudflare/zones/yaml"
    bind:
      compress: false
      path: "/var/backup/cloudflare/zones/bind"
```
