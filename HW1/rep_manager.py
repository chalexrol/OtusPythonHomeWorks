import gzip
import json
import logging
import os
import re
from collections import namedtuple
from datetime import datetime
from functools import partial
from string import Template

from progress import log_progress_update

LogFileData = namedtuple('LogFileData', ('file_name', 'date', 'is_zip'))


class UrlsData:
    def __init__(self):
        self.request_time = {}
        self.all_request_count = 0
        self.all_request_time = 0

    def add_count(self, url, request_time):
        self.all_request_count += 1
        self.all_request_time += request_time
        try:
            self.request_time[url].append(request_time)
        except KeyError:
            self.request_time[url] = [request_time]

    def as_json(self):
        data = []
        for url, request_time_list in self.request_time.items():
            call_times = len(request_time_list)
            time_sum = sum(request_time_list)
            data.append({
                'url': url,
                'count': call_times,
                'count_perc': round(call_times / self.all_request_count, 3),
                'time_sum': round(time_sum, 3),
                'time_perc': round(time_sum / self.all_request_time, 3),
                'time_avg': round(time_sum / call_times, 3),
                'time_max': round(max(request_time_list), 3),
                'time_med': round(sorted(request_time_list)[int(call_times / 2)], 3),
            })
        return json.dumps(data)


class BaseRepManager:
    log_re = NotImplemented

    def get_urls_data(self):
        raise NotImplementedError()

    def get_template(self):
        raise NotImplementedError()

    def prepare_report(self):
        raise NotImplementedError()

    def prepare_and_save_report(self):
        raise NotImplementedError()

    def is_report_exist(self):
        raise NotImplementedError()

    def __init__(self, config):
        self.config = config


class NginxRepManager(BaseRepManager):
    log_re = re.compile(
        r'(.+?) (.+?) {2}(.+?) \[(.+?)\] "((.*?) (.*?)(\?.*)? (.*?))?" (.+?) (.+?) "(.*?)" "(.*?)" "(.*?)" "(.*?)" (.+) (.+)')

    @staticmethod
    def get_log_file_data(file_name, regex=None):
        regex = regex or r'nginx-access-ui\.log-(\d+)(\.gz)?'
        result = re.match(regex, file_name)
        if result:
            date_string = result.group(1)
            try:
                date = datetime.strptime(date_string, '%Y%m%d')
            except ValueError:
                return None
            is_zip = bool(result.group(2))
            return LogFileData(file_name, date, is_zip)

    @staticmethod
    def get_last_log_file(log_dir):
        logging.info('Searching last log file.')
        last_log_file_data = None

        try:
            file_names = os.listdir(log_dir)
        except FileNotFoundError:
            logging.exception('Nginx log directory not found > log_dir=%s', log_dir)
            raise
        else:
            for file_name in file_names:
                log_file_data = NginxRepManager.get_log_file_data(file_name)
                if log_file_data:
                    if not last_log_file_data:
                        last_log_file_data = log_file_data
                    else:
                        if last_log_file_data.date < log_file_data.date:
                            last_log_file_data = log_file_data
        return last_log_file_data

    @staticmethod
    def get_file_line_count(opener, full_path):
        file = opener(full_path)
        line_count = sum(1 for _ in file)
        file.close()
        return line_count

    def get_urls_data(self):
        logging.info('Getting urls data.')
        full_path = f'{self.config["LOG_DIR"]}/{self.log_file_data.file_name}'

        if self.log_file_data.is_zip:
            opener = partial(gzip.open, encoding='utf-8', mode='rt')
        else:
            opener = partial(open, encoding='utf-8', mode='rt')
        line_count = self.get_file_line_count(opener, full_path)
        urls_data = UrlsData()
        with opener(full_path) as file:
            for num, line in enumerate(file):
                result = re.match(self.log_re, line)
                if result:
                    url = result.group(7)
                    request_time = result.group(17)
                    urls_data.add_count(url, float(request_time))
                log_progress_update(num / line_count)
        parsed_lines_percent = (urls_data.all_request_count / line_count)

        if parsed_lines_percent < self.config['MAX_UNPARSED_LINES']:
            logging.error('Too many lines unparsed > parsed_lines_percent=%s', parsed_lines_percent)
            raise Exception('Too many lines unparsed.')
        logging.info('Successfully parsed > parsed_lines_count=%s', urls_data.all_request_count)
        return urls_data

    def get_template(self):
        logging.info('Loading template.')
        template_path = f'{self.config["TEMPLATES_DIR"]}/{self.config["REPORT_TEMPLATE_FILE"]}'
        try:
            with open(template_path) as report_template_file:
                report_template = report_template_file.read()
        except FileNotFoundError:
            logging.exception('Template file not found > template_path=%s', template_path)
            raise
        return Template(report_template)

    def prepare_report(self):
        if not self.template_with_data:
            urls_data = self.get_urls_data()
            self.template_with_data = self.template.safe_substitute(table_json=urls_data.as_json())
            logging.info('Report prepared.')
        else:
            logging.info('Report already prepared.')

    def prepare_and_save_report(self):
        if not self.is_report_exist():
            if not self.template_with_data:
                self.prepare_report()
            with open(self.report_path, 'w') as report_file:
                report_file.write(self.template_with_data)
            logging.info('Report created.')
        else:
            logging.info('Report already exist.')

    def is_report_exist(self):
        os.makedirs(self.config['REPORT_DIR'], exist_ok=True)
        return os.path.exists(self.report_path)

    def __init__(self, config):
        super(NginxRepManager, self).__init__(config)
        self.log_file_data = self.get_last_log_file(self.config['LOG_DIR'])

        if self.log_file_data:
            logging.info('Found log file > log_file_name=%s', self.log_file_data.file_name)
            self.template = self.get_template()
            self.template_with_data = None

            report_date = self.log_file_data.date.strftime('%Y.%m.%d')
            self.report_name = f'log_report-{report_date}.html'
            self.report_path = os.path.join(self.config['REPORT_DIR'], self.report_name)
        else:
            logging.error('Log files not found.')
            raise FileNotFoundError('Log files not found.')
