#!/usr/bin/env python

import os
import gzip
import json
import logging
import argparse
import yaml
import CloudFlare


class CFBackup:
    def __init__(self, config_path: str) -> None:
        logging.basicConfig(
            format='[%(asctime)s] %(message)s',
            level=logging.INFO
        )

        self.config = self.load_config(config_path)
        self.config['cloudflare']['raw'] = True

        self.cf = CloudFlare.CloudFlare(**self.config['cloudflare'])

    def run(self) -> None:
        if self.config.get('export') and self.config['export'].get('zones'):
            formats = ['json', 'yaml', 'bind']
            conf = {
                f'zone_{row}': {
                    'path': self.config['export']['zones'][row].get('path'),
                    'file_ext': self.config['export']['zones'][row].get('file_ext', row),
                    'compress': self.config['export']['zones'][row].get('compress', True),
                } for row in formats if self.config['export']['zones'].get(row)
            }

            if conf:
                self.export_zones(**conf)

    def load_config(self, config_path: str) -> str:
        with open(config_path, 'r') as stream:
            return yaml.safe_load(stream)

    def export_zones(self, **kwargs) -> None:
        zone_json = kwargs.get('zone_json')
        zone_yaml = kwargs.get('zone_yaml')
        zone_bind = kwargs.get('zone_bind')

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

                save_kwargs = {
                    'zone_name': zone['name'],
                    'zone_id': zone['id']
                }

                if zone_json or zone_yaml:
                    data['records'] = self.export_zone_records(zone['id'])

                    if zone_json:
                        save_kwargs.update(zone_json)
                        save_kwargs['data'] = json.dumps(data)
                        self.save_zone_file(**save_kwargs)

                    if zone_yaml:
                        save_kwargs.update(zone_yaml)
                        save_kwargs['data'] = yaml.dump(data)
                        self.save_zone_file(**save_kwargs)

                if zone_bind:
                    dns_records = self.cf.zones.dns_records.export.get(zone['id'])
                    save_kwargs.update(zone_bind)
                    save_kwargs['data'] = dns_records['result']
                    self.save_zone_file(**save_kwargs)

            if total_pages == 0 or page_number == total_pages:
                break

    def export_zone_records(self, zone_id: str) -> list:
        records = []
        records_page_number = 0
        while True:
            records_page_number += 1
            records_params = {'per_page': 50, 'page': records_page_number}
            records_results = self.cf.zones.dns_records.get(zone_id, params=records_params)
            records_total_pages = records_results['result_info']['total_pages']

            for record in records_results['result']:
                records.append(record)

            if records_total_pages == 0 or records_page_number == records_total_pages:
                break

        return records


    @staticmethod
    def save_zone_file(path: str, zone_name: str, zone_id: str, file_ext: str, data: bytes, compress: bool) -> None:
        file_name = f'{zone_name}-{zone_id}.{file_ext}'
        func = open

        if compress:
            file_name = f'{file_name}.gz'
            func = gzip.open

        save_path = os.path.join(path, file_name)

        directory = os.path.dirname(save_path)
        if not os.path.exists(directory):
            logging.info(f'Creating directory: {directory}')
            os.makedirs(directory)

        with func(save_path, 'wb') as fd:
            fd.write(data.encode('utf-8'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Cloudflare Backup')
    parser.add_argument('--config', type=str, required=True, help='Path to config file')
    args = parser.parse_args()

    CFBackup(args.config).run()
