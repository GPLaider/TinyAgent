"""Use target ARM64 floating point for mpg123, including a fresh contrib extraction."""
import os
from pathlib import Path
import sys
import subprocess
import tempfile

OLD = 'if(WIN32 OR (ARCH_IS_ARM64 AND APPLE))'
NEW = 'if(WIN32 OR (ARCH_IS_ARM64 AND (APPLE OR ANDROID)))'
QUERY = 'GRADLE_CACHED_VERSION=$(./gradlew -q 2>/dev/null | grep gradle_version= | cut -b 16-)'
VERSION_QUERY = "GRADLE_CACHED_VERSION=$(./gradlew --version 2>/dev/null | sed -n 's/^Gradle //p')"
MESON_SETUP = 'if [ ! -d "build-android-$ANDROID_ABI/" ] || [ ! -f "build-android-$ANDROID_ABI/build.ninja" ]; then\n    export PATH="$LIBVLCJNI_SRC_DIR/vlc/extras/tools/build/bin:$PATH"'
MESON_REUSE = 'export PATH="$LIBVLCJNI_SRC_DIR/vlc/extras/tools/build/bin:$PATH"\n'+MESON_SETUP.split('\n')[0]

def replace_once(text, old=OLD, new=NEW):
    assert text.count(old) == 1 or text.count(new) == 1, 'Unexpected upstream source'
    return text.replace(old, new)

def write_changed(path, content):
    if not path.exists() or path.read_text() != content:
        path.write_text(content)

def prepare_build_scripts(base):
    x264 = base/'src/x264/rules.mak'
    write_changed(x264, replace_once(x264.read_text(), '$(subst ld,,$(LD))', '$(patsubst %ld,%,$(LD))'))
    compile_script = base.parents[2]/'buildsystem/compile.sh'
    old = ('if [ "$GRADLE_PATH_VERSION" != "$GRADLE_VERSION" ]; then\n'
           '        diagnostic "gradlew version $GRADLE_PATH_VERSION not matching $GRADLE_VERSION"')
    content = replace_once(compile_script.read_text(), old,
                           old.replace('GRADLE_PATH_VERSION', 'GRADLE_CACHED_VERSION'))
    write_changed(compile_script, replace_once(content, QUERY, VERSION_QUERY))
    medialibrary = compile_script.with_name('compile-medialibrary.sh')
    write_changed(medialibrary, replace_once(medialibrary.read_text(), MESON_SETUP, MESON_REUSE))
    print('x264 preserves linker directory; Gradle compares the measured wrapper version', flush=True)

def check_prefix():
    with tempfile.TemporaryDirectory() as directory:
        makefile = Path(directory)/'prefix.mk'
        makefile.write_text('LD := /opt/tinyagent-build/toolchain/llvm-ld\n'
                            '$(info old=$(subst ld,,$(LD)))\n'
                            '$(info new=$(patsubst %ld,%,$(LD)))\nall:\n')
        output = subprocess.check_output(['make', '--no-print-directory', '-f', str(makefile)], text=True)
        assert 'old=/opt/tinyagent-bui/toolchain/llvm-' in output
        assert 'new=/opt/tinyagent-build/toolchain/llvm-' in output
        print('PASS: actual GNU Make reproduces and fixes directory truncation')

def check_wrapper():
    bash = 'C:/Program Files/Git/bin/bash.exe' if os.name == 'nt' else '/usr/bin/bash'
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        wrapper = root/'gradlew'
        wrapper.write_text('#!/bin/sh\ncase "$1" in --version) printf "Gradle 9.3.1\\n";; *) printf "Welcome to Gradle\\n";; esac\n')
        wrapper.chmod(0o755)
        for query, expected in [(QUERY, ''), (VERSION_QUERY, '9.3.1')]:
            script = root/'probe.sh'
            script.write_text(query+'\nprintf "%s" "$GRADLE_CACHED_VERSION"\n')
            output = subprocess.check_output([bash, str(script)], cwd=root, text=True)
            assert output == expected, (query, output)
    print('PASS: wrapper version query avoids project default-task output')

def check_meson():
    bash = 'C:/Program Files/Git/bin/bash.exe' if os.name == 'nt' else '/usr/bin/bash'
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        tool = root/'vlc/extras/tools/build/bin/meson'
        tool.parent.mkdir(parents=True)
        tool.write_text('#!/bin/sh\nprintf "pinned-meson\\n"\n')
        tool.chmod(0o755)
        cache = root/'build-android-arm64-v8a'
        cache.mkdir()
        (cache/'build.ninja').touch()
        for text, expected in [(MESON_SETUP, False), (MESON_REUSE, True)]:
            script = root/'probe.sh'
            script.write_text('LIBVLCJNI_SRC_DIR="$PWD"\nANDROID_ABI=arm64-v8a\n'+text+'\n    :\nfi\ncommand -v meson\n')
            result = subprocess.run([bash, str(script)], cwd=root, capture_output=True, text=True)
            assert ('vlc/extras/tools/build/bin/meson' in result.stdout) == expected, result.stdout
        assert replace_once(MESON_SETUP, MESON_SETUP, MESON_REUSE) == MESON_REUSE
        assert replace_once(MESON_REUSE, MESON_SETUP, MESON_REUSE) == MESON_REUSE
    print('PASS: cached build reproduces wrong Meson selection; fixed path selects pinned tool')

def prepare(base):
    rules = base/'src/mpg123/rules.mak'
    content = rules.read_text()
    assert 'MPG123_VERSION := 1.33.6' in content
    patch = base/'src/mpg123/tinyagent-android-arm64-fpu.patch'
    write_changed(patch, '--- a/ports/cmake/src/CMakeLists.txt\n'
                     '+++ b/ports/cmake/src/CMakeLists.txt\n'
                     '@@ -199,5 +199,5 @@\n-'+OLD+'\n+'+NEW+'\n'
                     '     set(HAVE_FPU 1)\n'
                     ' else()\n'
                     '     cmake_host_system_information(RESULT HAVE_FPU QUERY HAS_FPU)\n'
                     ' endif()\n')
    anchor = '\t$(APPLY) $(SRC)/mpg123/0002-ports-cmake-Fix-building-ARM-assembly-for-Windows-fo.patch\n'
    addition = '\t$(APPLY) $(SRC)/mpg123/tinyagent-android-arm64-fpu.patch\n'
    assert content.count(anchor) == 1
    if addition not in content:
        rules.write_text(content.replace(anchor, anchor+addition))
    extracted = base/'contrib-android-aarch64-linux-android/mpg123/ports/cmake/src/CMakeLists.txt'
    if extracted.exists():
        original = extracted.read_text()
        updated = replace_once(original)
        if original != updated:
            extracted.write_text(updated)
        subprocess.run(['git', 'apply', '--check', '--reverse', str(patch)],
                       cwd=extracted.parents[3], check=True)
    print('mpg123 Android ARM64 uses target FPU; other targets unchanged', flush=True)

if __name__ == '__main__':
    if sys.argv[1:] == ['--check']:
        assert replace_once(OLD) == NEW
        assert replace_once(NEW) == NEW
        try:
            replace_once('unknown upstream')
        except AssertionError:
            pass
        else:
            raise AssertionError('Unknown upstream must fail')
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            rules = base/'src/mpg123/rules.mak'
            rules.parent.mkdir(parents=True)
            rules.write_text('MPG123_VERSION := 1.33.6\n'
                             '\t$(APPLY) $(SRC)/mpg123/0002-ports-cmake-Fix-building-ARM-assembly-for-Windows-fo.patch\n')
            extracted = base/'contrib-android-aarch64-linux-android/mpg123/ports/cmake/src/CMakeLists.txt'
            extracted.parent.mkdir(parents=True)
            extracted.write_text('\n'*198+OLD+'\n    set(HAVE_FPU 1)\nelse()\n'
                                 '    cmake_host_system_information(RESULT HAVE_FPU QUERY HAS_FPU)\nendif()\n')
            prepare(base)
            tracked = [extracted, rules, rules.with_name('tinyagent-android-arm64-fpu.patch')]
            timestamps = {path: path.stat().st_mtime_ns for path in tracked}
            prepare(base)
            assert {path: path.stat().st_mtime_ns for path in tracked} == timestamps, 'Unchanged build inputs rewritten'
        print('PASS: replacement, idempotence, upstream drift rejection, patch application')
    elif sys.argv[1:] == ['--check-prefix']:
        check_prefix()
    elif sys.argv[1:] == ['--check-wrapper']:
        check_wrapper()
    elif sys.argv[1:] == ['--check-meson']:
        check_meson()
    else:
        assert os.environ.get('TINYAGENT_EXECUTION_PROVIDER') == 'fedora-local'
        assert os.uname().machine == 'aarch64'
        base = Path('/workspace/tinyagent-six-builds/vlc-android/libvlcjni/vlc/contrib')
        prepare_build_scripts(base)
        prepare(base)
