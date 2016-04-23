from ipykernel.kernelbase import Kernel
from pexpect import replwrap, EOF

from . import fakerepl

import subprocess
import os

import base64
import imghdr
import re
import signal
import urllib

__version__ = '0.1'

version_pat = re.compile(r'version (\d+(\.\d+)+)')

from .images import display_data_for_image


class FakeReplKernel(Kernel):
    implementation = 'fakerepl_kernel'
    implementation_version = __version__

    @property
    def language_version(self):
        m = version_pat.search(self.banner)
        return m.group(1)

    _banner = "C++ Fake REPL"

    @property
    def banner(self):
        return self._banner

    language_info = {'name': 'C++',
                     'codemirror_mode': 'C++',
                     'mimetype': 'text/x-c++src',
                     'file_extension': '.cpp'}

    def __init__(self, **kwargs):
        Kernel.__init__(self, **kwargs)
        self._results = []
        self._errors = []
        self._fakerepl = fakerepl.FakeRepl(self._results.append, self._errors.append)

    def do_execute(self, code, silent, store_history=True,
                   user_expressions=None, allow_stdin=False):
        if not code.strip():
            return {'status': 'ok', 'execution_count': self.execution_count,
                    'payload': [], 'user_expressions': {}}

        interrupted = False
        try:
           self._fakerepl.eval(code)
        except KeyboardInterrupt:
            interrupted = True
        except EOF:
            self._fakerepl.reset_magic("")

        if not silent:
            # Send standard output
            output = "\n".join(self._results)
            stream_content = {'name': 'stdout', 'text': output}
            self.send_response(self.iopub_socket, 'stream', stream_content)

            for filename in self._fakerepl.image_files.values():
                try:
                    data = display_data_for_image(filename)
                except os.error:
                    pass
                except ValueError as e:
                    message = {'name': 'stdout', 'text': str(e)}
                    self.send_response(self.iopub_socket, 'stream', message)
                else:
                    self.send_response(self.iopub_socket, 'display_data', data)

        self._results[:] = []

        status = 'ok'
        if self._errors:
            for error in self._errors:
                stream_content = {'name': 'stderr', 'text': error}
                self.send_response(self.iopub_socket, 'stream', stream_content)
            self._errors[:] = []
            status = 'error'

        if interrupted:
            return {'status': 'abort', 'execution_count': self.execution_count}
        else:
            return {'status': status, 'execution_count': self.execution_count,
                    'payload': [], 'user_expressions': {}, 'traceback': []}

    def do_complete(self, code, cursor_pos):
        code = code[:cursor_pos]
        default = {'matches': [], 'cursor_start': 0,
                   'cursor_end': cursor_pos, 'metadata': dict(),
                   'status': 'ok'}

        return default
