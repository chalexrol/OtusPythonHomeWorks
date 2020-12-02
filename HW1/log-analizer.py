#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Log Analyzer

The program is supposed to be used to analyze Nginx access logs in
the predefined format.

Example of allowed log names:
* nginx-access-ui.log-20170101.gz
* nginx-access-ui.log-20170101.log

log_format ui_short '$remote_addr  $remote_user $http_x_real_ip [$time_local] '$request' '
                     '$status $body_bytes_sent '$http_referer' '
                     ''$http_user_agent' '$http_x_forwarded_for' '$http_X_REQUEST_ID' '$http_X_RB_USER' '
                     '$request_time';

"""
import json
import logging
import argparse
import copy
from json import JSONDecodeError
from rep_manager import NginxRepManager

config = {
    'REPORT_SIZE': 1000,
    'REPORT_DIR': './reports',
    'TEMPLATES_DIR': './templates',
    'REPORT_TEMPLATE_FILE': 'report.html',
    'LOG_DIR': './nginx_log',
    'MAX_UNPARSED_LINES': 0.1,
}


def start_logging(parsed_config):
    logging.basicConfig(filename=parsed_config.get('LOG_PATH', None),
                        format='[%(asctime)s] %(levelname).1s %(message)s', datefmt='%Y.%m.%d %H:%M:%S',
                        level=logging.INFO)


def get_config(file_name=None):
    result_config = copy.deepcopy(config)
    if file_name:
        try:
            with open(file_name, 'r') as config_file:
                parsed_config = json.load(config_file)
        except FileNotFoundError:
            logging.exception(f'File {file_name} not found.')
        except JSONDecodeError:
            logging.exception(f'File {file_name} content cannot be decoded.')
            raise
        result_config.update(parsed_config)
    return result_config


def get_parsed_args():
    arg_parser = argparse.ArgumentParser(description='Parses nginx log file and generates report.')
    arg_parser.add_argument('--config', default='config.json', help='Path to the config file.')
    return arg_parser.parse_args()


def main():
    args = get_parsed_args()
    custom_config = get_config(args.config)

    start_logging(custom_config)

    logging.info('Initializing report manager.')
    rep_manager = NginxRepManager(config)
    rep_manager.prepare_and_save_report()


if __name__ == '__main__':
    try:
        main()
    except (KeyboardInterrupt, Exception):
        logging.exception('Unexpected error.')
