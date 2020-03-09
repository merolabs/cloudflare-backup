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
        if not self.config['cloudflare'].get('raw'):
            self.config['cloudflare']['raw'] = True

        self.cf = CloudFlare.CloudFlare(**self.config['cloudflare'])

    def run(self):
        if 'export' in self.config and 'zones' in self.config['export']:
            conf = {
                f'zone_{row}': self.config['export']['zones'].get(row)
                for row in ['json', 'yaml', 'bind']
            }

            if any([conf[row] is not None for row in conf.keys()]):
                self.export_zones(**conf)

    def load_config(self, config_path):
        with open(config_path, 'r') as stream:
            return yaml.safe_load(stream)

    def export_zones(self, **kwargs):
        page_number = 0
        while True:
            page_number += 1
            zones_results = self.cf.zones.get(params={'per_page': 50, 'page': page_number})
            total_pages = zones_results['result_info']['total_pages']

            for zone in zones_results['result']:
                logging.info(f'Exporting zone. Zone: {zone["name"]}; ID: {zone["id"]}')
                data = {
                    'zone': zone,
                    'records': []
                }

                if kwargs.get('zone_json') or kwargs.get('zone_yaml'):
                    records_page_number = 0
                    while True:
                        records_page_number += 1
                        records_params = {'per_page': 50, 'page': records_page_number}
                        records_results = self.cf.zones.dns_records.get(zone['id'], params=records_params)
                        records_total_pages = records_results['result_info']['total_pages']

                        for record in records_results['result']:
                            data['records'].append(record)

                        if records_total_pages == 0 or records_page_number == records_total_pages:
                            break

                    if kwargs.get('zone_json'):
                        path = f'{kwargs["zone_json"]}/{zone["name"]}-{zone["id"]}.json.gz'
                        with gzip.open(path, 'wb') as fd:
                            fd.write(json.dumps(data).encode('utf-8'))

                    if kwargs.get('zone_yaml'):
                        path = f'{kwargs["zone_yaml"]}/{zone["name"]}-{zone["id"]}.yaml.gz'
                        with gzip.open(path, 'wb') as fd:
                            fd.write(yaml.dump(data).encode('utf-8'))

                if kwargs.get('zone_bind'):
                    dns_records = self.cf.zones.dns_records.export.get(zone['id'])
                    path = f'{kwargs["zone_bind"]}/{zone["name"]}-{zone["id"]}.db.gz'
                    with gzip.open(path, 'wb') as fd:
                        fd.write(dns_records['result'].encode('utf-8'))

            if total_pages == 0 or page_number == total_pages:
                break


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Cloudflare Backup')
    parser.add_argument('--config', type=str, required=True, help='Path to config file')
    args = parser.parse_args()

    CFBackup(args.config).run()
