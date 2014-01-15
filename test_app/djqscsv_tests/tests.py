from django.test import TestCase
from django.core.exceptions import ValidationError

from django import VERSION as DJANGO_VERSION

import csv

from StringIO import StringIO

from context import djqscsv

from models import Person


class ValidateCleanFilenameTests(TestCase):

    def assertValidatedEquals(self, filename, expected_value):
        validated = djqscsv._validate_and_clean_filename(filename)
        self.assertEqual(validated, expected_value)

    def test_validate_no_dots(self):
        self.assertValidatedEquals('karg', 'karg.csv')

    def test_validate_multiple_dots_csv(self):
        self.assertValidatedEquals('hort.town.csv',
                                   'horttown.csv')

    def test_validate_regular_csv(self):
        self.assertValidatedEquals('roke-knoll.csv',
                                   'roke-knoll.csv')

    def test_non_csv_raises(self):
        self.assertRaises(ValidationError,
                          djqscsv._validate_and_clean_filename,
                          'gont.island')

    def test_non_csv_raises_2(self):
        self.assertRaises(ValidationError,
                          djqscsv._validate_and_clean_filename,
                          'gont.csv.island')


class SanitizeUnicodeRecordTests(TestCase):
    def test_sanitize(self):
        record = {'name': 'Ged',
                  'nickname': u'\ufeffSparrowhawk'}
        sanitized = djqscsv._sanitize_unicode_record(record)
        self.assertEqual(sanitized,
                         {'name': 'Ged',
                          'nickname': '\xef\xbb\xbfSparrowhawk'})


class AppendDatestampTests(TestCase):

    def test_clean_returns(self):
        filename = "the_reach.csv"
        stamped = djqscsv._append_datestamp(filename)
        self.assertRegexpMatches(stamped, r'the_reach_[0-9]{8}.csv')

    def test_no_extension_raises(self):
        filename = "iffish"
        self.assertRaises(ValidationError,
                          djqscsv._append_datestamp,
                          filename)

    def test_unclean_extension_raises(self):
        filename = "hort.town"
        self.assertRaises(ValidationError,
                          djqscsv._append_datestamp,
                          filename)


class GenerateFilenameTests(TestCase):
    def test_generate_filename(self):
        Person.objects.create(name='vetch', address='iffish', info='wizard')
        Person.objects.create(name='nemmerle', address='roke',
                              info='arch mage')

        qs = Person.objects.all()

        self.assertEqual(djqscsv.generate_filename(qs),
                         'person_export.csv')

        self.assertRegexpMatches(djqscsv.generate_filename(qs, True),
                                 r'person_export_[0-9]{8}.csv')


class WriteCSVDataTests(TestCase):

    def setUp(self):
        Person.objects.create(name='vetch', address='iffish', info='wizard')
        Person.objects.create(name='nemmerle', address='roke',
                              info='arch mage')
        self.qs = Person.objects.all()

        self.full_verbose_csv = [
            ['\xef\xbb\xbfID', 'Person\'s name', 'address', 'Info on Person'],
            ['1', 'vetch', 'iffish', 'wizard'],
            ['2', 'nemmerle', 'roke', 'arch mage']]

        self.full_csv = [['\xef\xbb\xbfid', 'name', 'address', 'info'],
                         ['1', 'vetch', 'iffish', 'wizard'],
                         ['2', 'nemmerle', 'roke', 'arch mage']]

        self.limited_verbose_csv = [
            ['\xef\xbb\xbfPerson\'s name', 'address', 'Info on Person'],
            ['vetch', 'iffish', 'wizard'],
            ['nemmerle', 'roke', 'arch mage']]

        self.limited_csv = [['\xef\xbb\xbfname', 'address', 'info'],
                            ['vetch', 'iffish', 'wizard'],
                            ['nemmerle', 'roke', 'arch mage']]

    def assertMatchesCsv(self, csv_file, expected_data):
        csv_data = csv.reader(csv_file)
        iteration_happened = False
        for csv_row, expected_row in zip(csv_data, expected_data):
            iteration_happened = True
            self.assertEqual(csv_row, expected_row)

        self.assertTrue(iteration_happened, "The CSV does not contain data.")

    def test_write_csv_full_terse(self):
        obj = StringIO()
        djqscsv.write_csv(self.qs, obj, use_verbose_names=False)
        csv_file = filter(None, obj.getvalue().split('\n'))
        self.assertMatchesCsv(csv_file, self.full_csv)

    def test_write_csv_full_verbose(self):
        obj = StringIO()
        djqscsv.write_csv(self.qs, obj)
        csv_file = filter(None, obj.getvalue().split('\n'))
        self.assertMatchesCsv(csv_file, self.full_verbose_csv)

    def test_write_csv_limited_terse(self):
        qs = self.qs.values('name', 'address', 'info')
        obj = StringIO()
        djqscsv.write_csv(qs, obj, use_verbose_names=False)
        csv_file = filter(None, obj.getvalue().split('\n'))
        self.assertMatchesCsv(csv_file, self.limited_csv)

    def test_write_csv_limited_verbose(self):
        qs = self.qs.values('name', 'address', 'info')
        obj = StringIO()
        djqscsv.write_csv(qs, obj)
        csv_file = filter(None, obj.getvalue().split('\n'))
        self.assertMatchesCsv(csv_file, self.limited_verbose_csv)

    def test_render_to_csv_response(self):
        response = djqscsv.render_to_csv_response(self.qs,
                                                  filename="test_csv",
                                                  use_verbose_names=False)
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertMatchesCsv(response.content.split('\n'),
                              self.full_csv)

    def test_empty_queryset(self):
        qs = self.qs.none()
        obj = StringIO()
        if DJANGO_VERSION[:2] == (1, 5):
            with self.assertRaises(djqscsv.CSVException):
                djqscsv.write_csv(qs, obj)
        elif DJANGO_VERSION[:2] == (1, 6):
            djqscsv.write_csv(qs, obj, use_verbose_names=False)
            self.assertEqual(obj.getvalue(),
                             '\xef\xbb\xbfid,name,address,info\r\n')
