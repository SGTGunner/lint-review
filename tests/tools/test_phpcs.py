from __future__ import absolute_import
from lintreview.review import Problems, Comment
from lintreview.tools.phpcs import Phpcs
from unittest import TestCase
from nose.tools import eq_, ok_
from tests import requires_image, root_dir, read_file, read_and_restore_file


class Testphpcs(TestCase):

    fixtures = [
        'tests/fixtures/phpcs/no_errors.php',
        'tests/fixtures/phpcs/has_errors.php',
    ]

    def setUp(self):
        self.problems = Problems()
        self.tool = Phpcs(self.problems, base_path=root_dir)

    def test_match_file(self):
        self.assertTrue(self.tool.match_file('test.php'))
        self.assertTrue(self.tool.match_file('dir/name/test.php'))
        self.assertFalse(self.tool.match_file('dir/name/test.py'))
        self.assertFalse(self.tool.match_file('test.py'))
        self.assertFalse(self.tool.match_file('test.js'))

    @requires_image('phpcs')
    def test_check_dependencies(self):
        self.assertTrue(self.tool.check_dependencies())

    @requires_image('phpcs')
    def test_process_files__one_file_pass(self):
        self.tool.process_files([self.fixtures[0]])
        eq_([], self.problems.all(self.fixtures[0]))

    @requires_image('phpcs')
    def test_process_files__one_file_fail(self):
        self.tool.process_files([self.fixtures[1]])
        problems = self.problems.all(self.fixtures[1])
        eq_(3, len(problems))

        fname = self.fixtures[1]
        expected = Comment(
            fname,
            14,
            14,
            'Opening brace should be on a new line')
        eq_(expected, problems[0])

        expected = Comment(
            fname,
            16,
            16,
            "Spaces must be used to indent lines; tabs are not allowed")
        eq_(expected, problems[2])

    @requires_image('phpcs')
    def test_process_files_two_files(self):
        self.tool.process_files(self.fixtures)

        eq_([], self.problems.all(self.fixtures[0]))

        problems = self.problems.all(self.fixtures[1])
        eq_(3, len(problems))

    @requires_image('phpcs')
    def test_process_files__with_config(self):
        config = {
            'standard': 'Zend'
        }
        tool = Phpcs(self.problems, config, root_dir)
        tool.process_files([self.fixtures[1]])

        problems = self.problems.all(self.fixtures[1])

        eq_(3, len(problems), 'Changing standards changes error counts')

    @requires_image('phpcs')
    def test_process_files__with_ignore(self):
        config = {
            'standard': 'PSR2',
            'ignore': 'tests/fixtures/phpcs/*'
        }
        tool = Phpcs(self.problems, config, root_dir)
        tool.process_files([self.fixtures[1]])

        problems = self.problems.all(self.fixtures[1])

        eq_(0, len(problems), 'ignore option should exclude files')

    @requires_image('phpcs')
    def test_process_files__with_exclude(self):
        config = {
            'standard': 'PSR2',
            'exclude': 'Generic.WhiteSpace.DisallowTabIndent'
        }
        tool = Phpcs(self.problems, config, root_dir)
        tool.process_files([self.fixtures[1]])

        problems = self.problems.all(self.fixtures[1])

        eq_(1, len(problems), 'exclude option should reduce errors.')

    @requires_image('phpcs')
    def test_process_files__with_invalid_exclude(self):
        config = {
            'standard': 'PSR2',
            'exclude': 'Derpity.Derp'
        }
        tool = Phpcs(self.problems, config, root_dir)
        tool.process_files([self.fixtures[1]])

        problems = self.problems.all()
        eq_(1, len(problems), 'A failure comment should be logged.')

        error = problems[0].body
        ok_('Your PHPCS configuration output the following error' in error)
        ok_('Derpity.Derp' in error)

    def test_create_command__with_builtin_standard(self):
        config = {
            'standard': 'Zend',
            'tab_width': 4,
        }
        tool = Phpcs(self.problems, config, root_dir)
        result = tool.create_command(['some/file.php'])
        expected = [
            'phpcs',
            '--report=checkstyle',
            '--standard=Zend',
            '--extensions=php',
            '--tab-width=4',
            '/src/some/file.php'
        ]
        eq_(result, expected)

    def test_create_command__with_path_based_standard(self):
        config = {
            'standard': 'test/CodeStandards',
            'tab_width': 4,
        }
        tool = Phpcs(self.problems, config, root_dir)
        result = tool.create_command(['some/file.php'])
        expected = [
            'phpcs',
            '--report=checkstyle',
            '--standard=/src/test/CodeStandards',
            '--extensions=php',
            '--tab-width=4',
            '/src/some/file.php'
        ]
        eq_(result, expected)

    def test_create_command__ignore_option_as_list(self):
        config = {
            'standard': 'PSR2',
            'extensions': ['php', 'ctp'],
            'exclude': ['rule1', 'rule2'],
            'ignore': ['tests/fixtures/phpcs/*', 'tests/fixtures/eslint/*']
        }
        tool = Phpcs(self.problems, config, root_dir)
        result = tool.create_command(['some/file.php'])
        expected = [
            'phpcs',
            '--report=checkstyle',
            '--standard=PSR2',
            '--ignore=tests/fixtures/phpcs/*,tests/fixtures/eslint/*',
            '--exclude=rule1,rule2',
            '--extensions=php,ctp',
            '/src/some/file.php'
        ]
        eq_(result, expected)

    def test_has_fixer__not_enabled(self):
        tool = Phpcs(self.problems, {})
        eq_(False, tool.has_fixer())

    def test_has_fixer__enabled(self):
        tool = Phpcs(self.problems, {'fixer': True})
        eq_(True, tool.has_fixer())

    @requires_image('phpcs')
    def test_execute_fixer(self):
        tool = Phpcs(self.problems, {'fixer': True}, root_dir)

        original = read_file(self.fixtures[1])
        tool.execute_fixer(self.fixtures)

        updated = read_and_restore_file(self.fixtures[1], original)
        assert original != updated, 'File content should change.'
        eq_(0, len(self.problems.all()), 'No errors should be recorded')

    @requires_image('phpcs')
    def test_execute_fixer__no_problems_remain(self):
        tool = Phpcs(self.problems, {'fixer': True}, root_dir)

        # The fixture file can have all problems fixed by phpcs
        original = read_file(self.fixtures[1])
        tool.execute_fixer(self.fixtures)
        tool.process_files(self.fixtures)

        read_and_restore_file(self.fixtures[1], original)
        eq_(0, len(self.problems.all()), 'All errors should be autofixed')
