"""Run production WorkspaceFiles with Android API doubles backed by real Linux FDs.

Requires Linux, a JDK (JAVA_HOME or PATH), cc and an unprivileged user. This is
host regression evidence; it does not replace Android SELinux/device testing.
"""
import os
import re
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]

def main():
    if os.geteuid() == 0:
        raise SystemExit('Run as an unprivileged user so permission-denial assertions are meaningful')
    home = os.environ.get('JAVA_HOME')
    javac = Path(home) / 'bin/javac' if home else Path(shutil.which('javac') or '/missing-javac')
    if not javac.is_file():
        raise SystemExit('JDK missing: set JAVA_HOME or put javac on PATH')
    java_home = javac.resolve().parents[1]
    fixture = ROOT / 'tests/workspace-files'
    with tempfile.TemporaryDirectory(prefix='tinyagent-workspace-') as directory:
        temp = Path(directory)
        subprocess.run(['cc', '-shared', '-fPIC', '-Wall', '-Werror',
                        '-I' + str(java_home / 'include'), '-I' + str(java_home / 'include/linux'),
                        str(fixture / 'posix.c'), '-o', str(temp / 'libworkspace_test.so')], check=True, timeout=30)
        installer = (ROOT / 'app/src/main/java/io/github/gplaider/tinyagent/InstallerActivity.java').read_text()
        def method(start, end):
            return installer[installer.index(start):installer.index(end, installer.index(start))]
        export_check = (fixture / 'InstallerExportCheck.template').read_text()
        export_check = export_check.replace('/* PRODUCTION_MEMBERS */', re.search(r'private String pendingExport;', installer).group())
        export_check = export_check.replace('/* PRODUCTION_RESTORE */', re.search(r'pendingExport = saved == null[^;]+;', installer).group())
        export_check = export_check.replace('/* PRODUCTION_METHODS */',
            method('    @Override protected void onSaveInstanceState', '    private void stageWorkspace') +
            method('    private void exportWorkspace()', '    private interface Source'))
        (temp / 'InstallerExportCheck.java').write_text(export_check)
        sources = sorted(p for p in fixture.rglob('*.java') if 'device' not in p.relative_to(fixture).parts) + [temp / 'InstallerExportCheck.java']
        for name in ['WorkspaceFiles.java', 'WorkspaceFileProvider.java', 'WorkspaceCopy.java']:
            sources.append(ROOT / 'app/src/main/java/io/github/gplaider/tinyagent' / name)
        subprocess.run([str(javac), '-encoding', 'UTF-8', '-d', directory, *map(str, sources)], check=True, timeout=30)
        subprocess.run([str(java_home / 'bin/java'), '-Djava.library.path=' + directory, '-cp', directory,
                        'io.github.gplaider.tinyagent.WorkspaceFilesCheck', directory], check=True, timeout=30)
        subprocess.run([str(java_home / 'bin/java'), '-cp', directory,
                        'io.github.gplaider.tinyagent.WorkspaceCopyCheck'], check=True, timeout=30)
        export_fixture = temp / 'export'
        export_fixture.mkdir()
        subprocess.run([str(java_home / 'bin/java'), '-Djava.library.path=' + directory, '-cp', directory,
                        'io.github.gplaider.tinyagent.InstallerExportCheck', str(export_fixture)], check=True, timeout=30)

if __name__ == '__main__':
    main()
