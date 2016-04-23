import subprocess
import tempfile
import re
import os
import os.path
import readline
import itertools
import shlex
import json
import sys
from copy import copy
from collections import namedtuple
from glob import glob
from functools import partial

prelude = """
#include <iostream>
#include <boost/type_index.hpp>

namespace fakerepl {

template<typename T>
auto TPRINT_ONE(std::ostream &stream, const T &value) -> decltype(stream << value)
{
    return stream << value;
}

template<typename S, typename T>
void TPRINT_ONE(S &stream, const T &value)
{
    stream << "some " << boost::typeindex::type_id<T>().pretty_name();
}


template<typename T>
auto TPRINT(const T &value)
{
    TPRINT_ONE(std::cout, value);
    std::cout << std::endl;
}

template<typename T1, typename T2, typename... Targs>
void TPRINT(const T1 &value1, const T2 &value2, const Targs& ... Fargs) // recursive variadic function
{
    TPRINT_ONE(std::cout, value1);
    std::cout << std::endl;
    TPRINT(value2, Fargs...);
}

}
"""

type_chunk = """

int main()
{
    std::cout << boost::typeindex::type_id<decltype(
%s
    )>().pretty_name() << std::endl;
}
"""

print_function = """



"""

image_files = {
        "PNG_OUTPUT_FILE": "out.png"
        }

class ChunkList(object):
    def __init__(self, defines):
        self.counter = itertools.count().__next__
        self.tempdir = tempfile.TemporaryDirectory()
        self.tmpdirname = self.tempdir.name
        defines = "".join("#define %s %s\n" % (var, json.dumps(filename)) for var, filename in defines.items())
        self.header = prelude + defines
        self.cppflags = ()

    def reset_precompiled_headers(self):
        for file in glob(os.path.join(self.tmpdirname, "*.pch")):
            os.unlink(file)

    def add_chunk(self, fakerepl, chunk):
        count = self.counter()
        guard = "FAKE_REPL_CHUNK_%d_HPP" % count
        chunk = self.header + "\n" + chunk
        chunk = "#ifndef %s\n#define %s\n%s\n#endif\n" % (guard, guard, chunk)
        cppflags = self.cppflags
        filename = os.path.join(self.tmpdirname, "chunk%d.hpp" % count)
        with open(filename, "w") as f:
            f.write(chunk)
        self.header = '#include "%s"\n' % filename
        self.cppflags = ("-include", filename)
        pch_filename = filename + ".pch"
        pch_filename2 = filename + ".pch.TEMP"
        fakerepl.compile_file(filename, pch_filename2, ("-x", "c++-header") + cppflags)
        os.rename(pch_filename2, pch_filename)

      
class FakeRepl(object):
    magic_re = re.compile(r'^\s*%\s*(\S+)(.*)$', re.DOTALL)
    print_shell_re = re.compile(r'^\s*([!?])(.*)$', re.DOTALL)
    magics = "print shell action do type reset ldflags cppflags pwd cd pkg-config"
    obj_extension = ".o"
    exe_extension = ""
    compiler = "clang++"
    compiler_flags = ("-std=c++14",)

    cppflags = ()
    ldflags = ()

    def __init__(self, display, error_display):
        self.tempdir = tempfile.TemporaryDirectory()
        self.tmpdirname = self.tempdir.name
        self.display = display
        self.error_display = error_display
        self.compiler = os.getenv("CXX")
        self.cppflags = tuple(shlex.split(os.getenv("CPPFLAGS")))
        self.ldflags = tuple(shlex.split(os.getenv("LDFLAGS")))
        self.magics = self.process_magics(self.magics.split())
        self.image_files = {
                var : os.path.join(self.tmpdirname, filename) 
                for var, filename in image_files.items()
                }
        self.runtime_lib_path = os.path.pathsep.join(shlex.split(os.getenv("RUNTIME_LIB_PATH")))
        if sys.platform.startswith("darwin"):
            self.runtime_lib_path_env = "DYLD_LIBRARY_PATH"
        else:
            self.runtime_lib_path_env = "LD_LIBRARY_PATH"
        runtime_lib_path = os.getenv(self.runtime_lib_path_env)
        if runtime_lib_path:
            self.runtime_lib_path = self.runtime_lib_path + os.path.pathsep + runtime_lib_path
        self.env = dict(os.environ)
        self.env[self.runtime_lib_path_env] = self.runtime_lib_path
        self.reset_magic("")

    def process_magics(self, magics):
        table = {}
        for magic in magics:
            method = magic.replace("-", "_") + "_magic"
            for i in range(1, len(magic)):
                table.setdefault(magic[:i], []).append(method)
        table = {k:v[0] for k, v in table.items() if len(v) == 1}
        for magic in magics:
            method = magic.replace("-", "_") + "_magic"
            table[magic] = method
        return table

    def process_variable(self, name, args):
        args = args.split()
        if len(args) == 0:
            self.display(" ".join(getattr(self, name)))
            return False
        elif args[0] == "=":
            setattr(self, name, tuple(args[1:]))
            return True
        elif args[0] == "+=":
            setattr(self, name, getattr(self, name) + tuple(args[1:]))
            return True
        else:
            self.error_display("Expected = or += after %%%s" % name)

    def ldflags_magic(self, args):
        self.process_variable("ldflags", args)

    def cppflags_magic(self, args):
        if self.process_variable("cppflags", args):
            self.chunks.reset_precompiled_headers()

    def eval(self, code):
        try:
            mo = self.magic_re.match(code)
            if mo is not None:
                magic, args = mo.groups()
                magic_method = self.magics.get(magic)
                if magic_method is not None:
                    (getattr(self, magic_method))(args)
                else:
                    self.error_display("No such magic: %%%s" % magic)
            else:
                mo = self.print_shell_re.match(code)
                if mo is not None:
                    action, args = mo.groups()
                    if action == "?":
                        self.print_magic(args)
                    else:
                        self.shell_magic(args)
                else:
                    self.process_chunk(code)
        except subprocess.CalledProcessError as err:
           self.error_display(err.stdout.decode())
        except os.error as err:
           self.error_display(err.strerror)

    def pwd_magic(self, args):
        self.display(os.getcwd())

    def cd_magic(self, args):
        os.chdir(os.path.expanduser(args.strip()))
 
    def print_magic(self, args):
        chunk = "int main() {\nfakerepl::TPRINT(\n%s\n);\n}\n" % args
        self.process_chunk(chunk, add_chunk=False, run_code=True)

    def shell_magic(self, args):
        if args:
            try:
                result = subprocess.run(args,
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                        shell=True, check=True)
                self.display(result.stdout.decode())
            except subprocess.CalledProcessError as err:
                self.error_display(err.stdout.decode())


    def do_magic(self, args):
        chunk = "int main() {\n%s\n;\n}\n" % args
        self.process_chunk(chunk, add_chunk=False, run_code=True)

    def type_magic(self, args):
        chunk = type_chunk % args
        self.process_chunk(chunk, add_chunk=False, run_code=True)

    def fresh_name(self):
        self.counter = self.counter + 1
        return "iNtErNaL__%d" % self.counter

    def action_magic(self, args):
        chunk = "int %s = ([](){\n%s\n;return 0;})();\n" % (self.fresh_name(), args)
        self.process_chunk(chunk, add_chunk=True, run_code=False)

    def pkg_config_magic(self, args):
        args = args.split()
        try:
            for pkg in args:
                if pkg in self.pkg_config:
                    continue
                cppflags = subprocess.check_output(("pkg-config", "--cflags", pkg),
                        stderr=subprocess.PIPE,
                        ).decode()
                libs = subprocess.check_output(("pkg-config", "--libs", pkg),
                        stderr=subprocess.PIPE,
                        ).decode()
                self.cppflags = self.cppflags + tuple(cppflags.split())
                self.ldflags = self.ldflags + tuple(libs.split())
                self.pkg_config.add(pkg)
                self.chunks.reset_precompiled_headers()
        except subprocess.SubprocessError as err:
            self.error_display(err.stderr.decode())



    def reset_magic(self, args):
        self.chunks = ChunkList(self.image_files)
        self.counter = 0
        self.pkg_config = set()


    def compile_file(self, filename, objfile, extra_flags=()):
        cppflags = self.cppflags
        args = (self.compiler,) + extra_flags + self.compiler_flags + cppflags + \
                ("-c", os.path.basename(filename), "-o", objfile) 
#        self.display(" ".join(args))

        compile_call = partial(subprocess.run, args,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                cwd=os.path.dirname(filename), check=True)

        try:
            compile_call()
            return
        except subprocess.CalledProcessError as err:
            if b"Segmentation fault" not in err.stdout:
                raise
 #       self.display("Retry")

        self.chunks.reset_precompiled_headers()
        compile_call()


    def link_file(self, objfile, executable):
        subprocess.run((self.compiler, os.path.basename(objfile), "-o", executable) + self.ldflags,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                cwd=os.path.dirname(objfile), check=True)


    def process_chunk(self, code, add_chunk=True, run_code=False):
        main_file = os.path.join(self.tmpdirname, "repl.cxx")
        obj_file = os.path.join(self.tmpdirname, "repl" + self.obj_extension)
        new_chunks = self.chunks
        if add_chunk:
            new_chunks = copy(new_chunks)
            new_chunks.add_chunk(self, code)
        with open(os.path.join(self.tmpdirname, "repl.cxx"), "w") as f:
            f.write(new_chunks.header)
            if not add_chunk:
                f.write(code)
        self.compile_file(main_file, obj_file, new_chunks.cppflags)
        if run_code:
            exe_file = os.path.join(self.tmpdirname, "main" + self.exe_extension)
            self.link_file(obj_file, exe_file)
            result = subprocess.run((exe_file,), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=True, env=self.env)
            self.display(result.stdout.decode())
        self.chunks = new_chunks

def mainloop(tmpdirname):
    fakerepl = FakeRepl(tmpdirname, print)
    try:
        while True:
            code = input("> ")
            try:
               fakerepl.eval(code)
            except subprocess.SubprocessError as err:
               print(err.stdout.decode())
    except EOFError:
        print("Bye")
        return

def main():
    with tempfile.TemporaryDirectory() as tmpdirname:
        mainloop(tmpdirname)

if __name__ == "__main__":
    main()
