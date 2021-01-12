import logging
import os
import unittest
from unittest import mock
from rep_manager import NginxRepManager


@mock.patch('rep_manager.log_progress_update', new=mock.Mock())
class TestReportParser(unittest.TestCase):
    def setUp(self):
        super(TestReportParser, self).setUp()
        logging.disable(logging.CRITICAL)
        self.config = {
            'REPORT_SIZE': 1000,
            'REPORT_DIR': './data/reports',
            'TEMPLATES_DIR': './data/templates',
            'REPORT_TEMPLATE_FILE': 'report.html',
            'LOG_DIR': './data/logs',
            'MAX_UNPARSED_LINES': 0.1,
        }
        self.test_report_file_name = 'log_report-2021.01.11.html'
        file_names = os.listdir(self.config['REPORT_DIR'])
        for file_name in file_names:
            full_path = f'{self.config["REPORT_DIR"]}/{file_name}'
            '''os.remove(full_path)'''

    def tearDown(self):
        super(TestReportParser, self).tearDown()
        file_names = os.listdir(self.config['REPORT_DIR'])
        for file_name in file_names:
            full_path = f'{self.config["REPORT_DIR"]}/{file_name}'
            os.remove(full_path)

    @mock.patch('rep_manager.Template.safe_substitute')
    def test_success_with_creation(self, mock_safe_substitute):
        mock_safe_substitute.return_value = 'test'
        rep_manager = NginxRepManager(self.config)
        report_full_path = f'{self.config["REPORT_DIR"]}/{self.test_report_file_name}'
        'self.assertFalse(os.path.exists(report_full_path))'
        rep_manager.prepare_and_save_report()
        self.assertEqual({'table_json': '[{"url": "/test_route", "count": 2, "count_perc": 1.0, '
                                        '"time_sum": 3.0, "time_perc": 1.0, "time_avg": 1.5, '
                                        '"time_max": 2.0, "time_med": 2.0}]'}, mock_safe_substitute.call_args[1])
        self.assertTrue(os.path.exists(report_full_path))

    @mock.patch('rep_manager.Template.safe_substitute')
    def test_success_gz_with_creation(self, mock_safe_substitute):
        mock_safe_substitute.return_value = 'test'
        self.config['LOG_DIR'] = './data/gz_logs'
        rep_manager = NginxRepManager(self.config)
        report_full_path = f'{self.config["REPORT_DIR"]}/{self.test_report_file_name}'
        self.assertFalse(os.path.exists(report_full_path))
        rep_manager.prepare_and_save_report()
        self.assertEqual({'table_json': '[{"url": "/test_route", "count": 2, "count_perc": 1.0, '
                                        '"time_sum": 3.0, "time_perc": 1.0, "time_avg": 1.5, '
                                        '"time_max": 2.0, "time_med": 2.0}]'}, mock_safe_substitute.call_args[1])
        self.assertTrue(os.path.exists(report_full_path))

    def test_success_already_exists(self):
        rep_manager = NginxRepManager(self.config)
        report_full_path = f'{self.config["REPORT_DIR"]}/{self.test_report_file_name}'
        fo = open(report_full_path, 'w')
        self.assertTrue(os.path.exists(report_full_path))
        rep_manager.prepare_and_save_report()
        fo.close()

    def test_file_not_found_exception(self):
        self.config['TEMPLATES_DIR'] = './wrong'
        with self.assertRaises(FileNotFoundError):
            NginxRepManager(self.config)

        self.config['LOG_DIR'] = './wrong'
        with self.assertRaises(FileNotFoundError):
            NginxRepManager(self.config)

    def test_too_many_unparsed_exception(self):
        self.config['MAX_UNPARSED_LINES'] = 0.7
        rep_manager = NginxRepManager(self.config)
        with self.assertRaises(Exception) as e:
            rep_manager.prepare_and_save_report()
        self.assertEqual(('Too many lines unparsed.',), e.exception.args)


if __name__ == '__main__':
    unittest.main()
