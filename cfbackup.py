#!/usr/bin/env python

import gzip
import json
import logging
import argparse
import yaml
import CloudFlare


class CFBackup:
    def __init__(self, config_path):
        logging.basicConfig(
            format='[%(asctime)s] %(message)s',
            level=logging.INFO
        )

        self.config = self.load_config(config_path)
        self.cf = CloudFlare.CloudFlare(**self.config['cloudflare'])

    def run(self):
        if 'export' in self.config and 'zones' in self.config['export']:
            conf = {
                'zone_json': self.config['export']['zones'].get('json'),
                'zone_yaml': self.config['export']['zones'].get('yaml')
            }

            if any([conf[row] is not None for row in conf.keys()]):
                self.export_zones(**conf)

    def load_config(self, config_path):
        with open(config_path, 'r') as stream:
            return yaml.safe_load(stream)

    def export_zones(self, **kwargs):
        for zone in self.cf.zones.get():
            logging.info(f'Exporting zone. Zone: {zone["name"]}; ID: {zone["id"]}')
            data = {
                'zone': zone,
                'records': [
                    row for row in self.cf.zones.dns_records.get(zone['id'])
                ]
            }

            if kwargs.get('zone_json'):
                path = f'{kwargs["zone_json"]}/{zone["name"]}-{zone["id"]}.json.gz'
                with gzip.open(path, 'wb') as fd:
                    fd.write(json.dumps(data).encode('utf-8'))

            if kwargs.get('zone_yaml'):
                path = f'{kwargs["zone_yaml"]}/{zone["name"]}-{zone["id"]}.yaml.gz'
                with gzip.open(path, 'wb') as fd:
                    fd.write(yaml.dump(data).encode('utf-8'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Cloudflare Backup')
    parser.add_argument('--config', type=str, required=True, help='Path to config file')
    args = parser.parse_args()

    CFBackup(args.config).run()
