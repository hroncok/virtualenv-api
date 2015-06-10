import os
import six
import subprocess

from virtualenvapi.exceptions import *
from virtualenvapi.util import to_text

class PipWrapper(object):
    """
    This class is a low-level wrapper around the `pip` command.
    It is designed to be used by the `VirtualEnvironment` class,
    not directly.
    """

    global_pip_args = ['--disable-pip-version-check']

    def __init__(self, path, cache=None):
        self.path = path
        if cache is not None:
            self.global_pip_args += ['--cache-dir', os.path.expanduser(os.path.expandvars(cache))]
        self.env = os.environ.copy()

    @property
    def pip_rpath(self):
        """
        The relative path (from environment root) to pip.
        """
        return os.path.join('bin', 'pip')

    def exists(self):
        """
        Returns True if the `pip` executable exists.
        """
        return os.path.isfile(os.path.join(self.path, self.pip_rpath))

    def _execute(self, args):
        """
        Executes a pip command and returns a tuple of (stdout, stderr).
        """
        args = [self.pip_rpath] + self.global_pip_args + args
        try:
            proc = subprocess.Popen(args, cwd=self.path, env=self.env, 
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = proc.communicate()
            if proc.returncode:
                print(stdout, stderr)
                raise subprocess.CalledProcessError(proc.returncode, args[0], (stdout, stderr))
        except OSError as e:
            # raise a more meaningful error with the program name
            prog = args[0]
            if prog[0] != os.sep:
                prog = os.path.join(self.path, prog)
            raise OSError('%s: %s' % (prog, six.u(e)))
        except subprocess.CalledProcessError as e:
            output, error = e.output
            e.output = output
            raise e
        else:
            return (to_text(stdout.strip()), to_text(stderr.strip()))

    def install(self, package_name, options=None):
        """
        Calls `pip install` to install a package with the given pip options.
        """
        if options is None:
            options = []
        try:
            args = ['install', package_name] + options
            return self._execute(args)
        except subprocess.CalledProcessError as e:
            raise PackageInstallationException((e.returncode, e.output, package_name))

    def uninstall(self, package_name):
        """
        Calls `pip uninstall` to remove a package.
        """
        try:
            args = ['uninstall', '-y', package_name]
            return self._execute(args)
        except subprocess.CalledProcessError as e:
            raise PackageRemovalException((e.returncode, e.output, package_name))

    def wheel(self, package_name, options=None):
        """
        Calls `pip wheel` to create a wheel for the given package.
        """
        if options is None:
            options = []
        try:
            args = ['wheel', package_name] + options
            return self._execute(args)
        except subprocess.CalledProcessError as e:
            raise PackageWheelException((e.returncode, e.output, package_name))

    def search(self, term):
        """
        Searches the PyPi repository for the given `term` and returns a
        dictionary of results.

        New in 2.1.5: returns a dictionary instead of list of tuples
        """
        packages = {}
        args = ['search', term]
        stdout, _ = self._execute(args)
        for result in stdout.split(os.linesep):
            try:
                name, description = result.split(six.u(' - '), 1)
            except ValueError:
                # '-' not in result so unable to split into tuple;
                # this could be from a multi-line description
                continue
            else:
                name = name.strip()
                if len(name) == 0:
                    continue
                packages[name] = description.split(six.u('<br'), 1)[0].strip()
        return packages
