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

        self.zone_extra = [
            'keyless_certificates',
            'custom_pages',
            'pagerules',
            'settings'
        ]

        self.zone_extra_firewall = [
            'access_rules',
            'ua_rules'
        ]

    def run(self, zone=None) -> None:
        if self.config.get('export') and self.config['export'].get('zones'):
            zones = self.config['export']['zones']
            zones_extra = zones.get('extra')

            formats = ['json', 'yaml', 'bind']

            conf = {
                f'zone_format_{row}': {
                    'path': zones[row].get('path'),
                    'file_ext': zones[row].get('file_ext', row),
                    'compress': zones[row].get('compress', True),
                } for row in formats if zones.get(row)
            }

            if zones_extra:
                conf.update({
                    f'zone_extra_{row}': zones_extra.get(row)
                    for row in self.zone_extra
                })
                if zones_extra.get('firewall'):
                    conf.update({
                        f'zone_extra_firewall_{row}': zones_extra['firewall'].get(row)
                        for row in self.zone_extra_firewall
                    })

            conf['limit_zone'] = zone

            self.export_zones(**conf)

    def load_config(self, config_path: str) -> str:
        with open(config_path, 'r') as stream:
            return yaml.safe_load(stream)

    def export_zones(self, **kwargs) -> None:
        zone_json = kwargs.get('zone_format_json')
        zone_yaml = kwargs.get('zone_format_yaml')
        zone_bind = kwargs.get('zone_format_bind')

        for zone in self._extract_query(self.cf.zones, zone_name=kwargs.get('limit_zone')):
            logging.info(f'Exporting zone. Zone: {zone["name"]}; ID: {zone["id"]}')

            data = {
                'zone': zone,
                'firewall': {}
            }

            save_kwargs = {
                'zone_name': zone['name'],
                'zone_id': zone['id']
            }

            if zone_json or zone_yaml:
                data.update({
                    'records': self._extract_query(
                        self.cf.zones.dns_records,
                        zone['id']
                    )
                })

                for extra in self.zone_extra:
                    if kwargs.get(f'zone_extra_{extra}'):
                        data.update({
                            extra: self._extract_query(
                                getattr(self.cf.zones, extra),
                                zone['id']
                            )
                        })

                if kwargs.get('zone_extra_firewall_access_rules'):
                    data['firewall']['access_rules'] = self._extract_query(
                        self.cf.zones.firewall.access_rules.rules,
                        zone['id']
                    )

                if kwargs.get('zone_extra_firewall_ua_rules'):
                    data['firewall']['ua_rules'] = self._extract_query(
                        self.cf.zones.firewall.ua_rules,
                        zone['id']
                    )

                if zone_json:
                    save_kwargs.update(zone_json)
                    save_kwargs['data'] = json.dumps(data)
                    self.save_zone_file(**save_kwargs)

                if zone_yaml:
                    save_kwargs.update(zone_yaml)
                    save_kwargs['data'] = yaml.dump(data)
                    self.save_zone_file(**save_kwargs)

            if zone_bind:
                save_kwargs.update(zone_bind)
                save_kwargs['data'] = self._extract_query(
                    self.cf.zones.dns_records.export,
                    zone['id']
                )
                self.save_zone_file(**save_kwargs)

    @staticmethod
    def _extract_query(func, zone_id=None, zone_name=None):
        rows = []
        page_number = 0

        while True:
            page_number += 1
            params = {'per_page': 50, 'page': page_number}
            if zone_name:
                params['name'] = zone_name

            if zone_id:
                results = func.get(zone_id, params=params)
            else:
                results = func.get(params=params)

            if type(results['result']) == list:
                rows.extend(results['result'])
            else:
                return results['result']

            if results.get('result_info'):
                total_pages = results['result_info']['total_pages']

                if total_pages == 0 or page_number == total_pages:
                    break

            else:
                break

        return rows

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
    parser.add_argument('--zone', type=str, help='Limit to specific zone')
    args = parser.parse_args()

    CFBackup(args.config).run(args.zone)
