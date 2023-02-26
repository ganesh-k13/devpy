import os
import errno
import sys
import shutil
import click
from pathlib import Path
import subprocess
from .util import run, install_dir, set_mem_rlimit

def run_asv(cmd):
    EXTRA_PATH = ['/usr/lib/ccache', '/usr/lib/f90cache',
                  '/usr/local/lib/ccache', '/usr/local/lib/f90cache']
    bench_dir = 'benchmarks'
    sys.path.insert(0, str(bench_dir))

    # Always use ccache, if installed
    env = dict(os.environ)
    env['PATH'] = os.pathsep.join(EXTRA_PATH +
                                  env.get('PATH', '').split(os.pathsep))
    # Control BLAS/LAPACK threads
    env['OPENBLAS_NUM_THREADS'] = '1'
    env['MKL_NUM_THREADS'] = '1'

    # Limit memory usage
    try:
        set_mem_rlimit()
    except (ImportError, RuntimeError):
        pass
    try:
        return subprocess.call(cmd, env=env, cwd=bench_dir)
    except OSError as err:
        if err.errno == errno.ENOENT:
            cmd_str = " ".join(cmd)
            print(f"Error when running '{cmd_str}': {err}\n")
            print("You need to install Airspeed Velocity "
                  "(https://airspeed-velocity.github.io/asv/)")
            print("to run Scipy benchmarks")
            return 1
        raise

@click.command()
@click.option("-t", "--tests", help="Specify tests to run", default=None, multiple=True)
@click.option("-s", "--submodule", help="Submodule whose tests to run", default=None, multiple=True)
@click.option("-c", "--compare",help=(
            "Compare benchmark results of current HEAD to BEFORE. "
            "Use an additional --bench COMMIT to override HEAD with COMMIT. "
            "Note that you need to commit your changes first!"), default=None, multiple=True)
def bench(tests, submodule, compare):
    """🔧 Build package with Meson/ninja and install

    MESON_ARGS are passed through e.g.:

    ./dev.py build -- -Dpkg_config_path=/lib64/pkgconfig

    The package is installed to BUILD_DIR-install

    By default builds for release, to be able to use a debugger set CFLAGS
    appropriately. For example, for linux use

    CFLAGS="-O0 -g" ./dev.py build
    """
    extra_argv = []
    if tests:
        extra_argv.append(tests)
    if submodule:
        extra_argv.append([submodule])

    bench_args = []
    for a in extra_argv:
        bench_args.extend(['--bench', ' '.join(str(x) for x in a)])
    if not compare:
        cmd = ['asv', 'run', '--dry-run', '--show-stderr',
               '--python=same'] + bench_args
        retval = run_asv(cmd)
        sys.exit(retval)
    else:
        if len(compare) == 1:
            commit_a = args.compare[0]
            commit_b = 'HEAD'
        elif len(args.compare) == 2:
            commit_a, commit_b = compare
        else:
            print("Too many commits to compare benchmarks for")
        # Check for uncommitted files
        if commit_b == 'HEAD':
            r1 = subprocess.call(['git', 'diff-index', '--quiet',
                                  '--cached', 'HEAD'])
            r2 = subprocess.call(['git', 'diff-files', '--quiet'])
            if r1 != 0 or r2 != 0:
                print("*" * 80)
                print("WARNING: you have uncommitted changes --- "
                      "these will NOT be benchmarked!")
                print("*" * 80)

        # Fix commit ids (HEAD is local to current repo)
        p = subprocess.Popen(['git', 'rev-parse', commit_b],
                             stdout=subprocess.PIPE)
        out, err = p.communicate()
        commit_b = out.strip()

        p = subprocess.Popen(['git', 'rev-parse', commit_a],
                             stdout=subprocess.PIPE)
        out, err = p.communicate()
        commit_a = out.strip()
        cmd_compare = [
            'asv', 'continuous', '--show-stderr', '--factor', '1.05',
            commit_a, commit_b
        ] + bench_args
        run_asv(dirs, cmd_compare)
        sys.exit(1)
