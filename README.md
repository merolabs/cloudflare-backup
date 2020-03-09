# Cloudflare Backup

This simple application can make a backup from Cloudflare accounts.

Supported exports:

* Zone
  * DNS Records
  * Settings
  * PageRules
  * Custom Pages
  * Keyless Certificates
  * Firewall
    * Access
    * UserAgent Rules

## Requirements

* Python version - 3.6+.
* Python modules - in file `requirements.txt`

## Config

Supported zone export formats:
* json
* yaml
* bind

### Example config

```yaml
cloudflare:
  token: "<your access token>"
export:
  zones:
    extra:
      keyless_certificates: true
      custom_pages: true
      pagerules: true
      settings: true
      firewall:
        access_rules: true
        ua_rules: true
    json:
      path: "/var/backup/cloudflare/zones/json"
    yaml:
      path: "/var/backup/cloudflare/zones/yaml"
    bind:
      compress: false
      path: "/var/backup/cloudflare/zones/bind"
```
