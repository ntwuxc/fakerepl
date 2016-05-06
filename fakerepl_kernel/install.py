import json
import os
import sys
import shlex
import shutil
import subprocess
import re
from glob import glob

from jupyter_client.kernelspec import install_kernel_spec
from IPython.utils.tempdir import TemporaryDirectory

def quote_list(lst):
    return " ".join(shlex.quote(item) for item in lst)

def find_compiler():
    compiler = shutil.which("clang++")
    subprocess.check_call((compiler, "--version"))
    return compiler

def find_boost_cppflags():
    locations = ["/usr/include", "/usr/local/include", "/opt/local/include"]
    BOOST_ROOT = os.getenv("BOOST_ROOT")
    if BOOST_ROOT is not None:
        locations.insert(0, BOOST_ROOT)
    for loc in locations:
        if os.path.exists(os.path.join(loc, "boost", "version.hpp")):
            return ("-I", loc)
    return ()

def find_boost_ldflags():
    locations = ["/usr/lib", "/usr/local/lib", "/opt/local/lib"]
    BOOST_ROOT = os.getenv("BOOST_ROOT")
    if BOOST_ROOT is not None:
        locations.insert(0, os.path.join(BOOST_ROOT, "stage", "lib"))
    serlib_re = re.compile(r"^lib(boost_serialization[^.]*).*")

    for loc in locations:
        try:
            filenames = os.listdir(loc)
        except os.error:
            continue
        for filename in filenames:
            mo = serlib_re.match(filename)
            if mo is not None:
               return ("-L", loc, "-l" + mo.group(1)), (loc,)
    return (), ()

def make_kernel_json(env):
    return {"argv":[sys.executable,"-m","fakerepl_kernel", "-f", "{connection_file}"],
     "display_name":"fakerepl",
     "language":"C++",
     "codemirror_mode":"C++",
     "env": env
    }


def install_my_kernel_spec(user=True):
    ldflags, ld_lib_path = find_boost_ldflags()
    env = { "CXX" : find_compiler(),
            "CPPFLAGS" : quote_list(find_boost_cppflags()),
            "LDFLAGS" : quote_list(ldflags),
            "RUNTIME_LIB_PATH" : '' }
    with TemporaryDirectory() as td:
        os.chmod(td, 0o755) # Starts off as 700, not user readable
        with open(os.path.join(td, 'kernel.json'), 'w') as f:
            json.dump(make_kernel_json(env), f, sort_keys=True)
        # TODO: Copy resources once they're specified

        print('Installing IPython kernel spec')
        install_kernel_spec(td, 'fakerepl', user=user, replace=True)
    for name in sorted(env):
        print("%s=%s" % (name, env[name]))

def _is_root():
    try:
        return os.geteuid() == 0
    except AttributeError:
        return False # assume not an admin on non-Unix platforms

def main(argv=[]):
    user = '--user' in argv or not _is_root()
    install_my_kernel_spec(user=user)

if __name__ == '__main__':
    main(argv=sys.argv)
