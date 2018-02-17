from __future__ import absolute_import
import logging
import os
from lintreview.tools import Tool, process_checkstyle
import lintreview.docker as docker


log = logging.getLogger(__name__)


class Sasslint(Tool):

    name = 'sasslint'

    def check_dependencies(self):
        """
        See if sass-lint is on the system path.
        """
        return docker.image_exists('nodejs')

    def match_file(self, filename):
        base = os.path.basename(filename)
        name, ext = os.path.splitext(base)
        return ext == '.sass' or ext == '.scss'

    def process_files(self, files):
        """
        Run code checks with sass-lint.
        Only a single process is made for all files
        to save resources.
        """
        log.debug('Processing %s files with %s', files, self.name)
        command = ['sass-lint', '-f', 'checkstyle', '-v']
        command += files
        if self.options.get('ignore'):
            command += ['--ignore ', self.options.get('ignore')]
        if self.options.get('config'):
            command += ['--config',
                        docker.apply_base(self.options['config'])]
        output = docker.run(
            'nodejs',
            command,
            source_dir=self.base_path)
        process_checkstyle(self.problems, output, docker.strip_base)
