#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/random.h>
#include <sys/stat.h>
#include <sys/xattr.h>
#include <sys/syscall.h>
#include <unistd.h>

static int probe_execve(const char *, char *const [], char *const []);
// Reuse the exact native FD duplication/close_range/environment code. Only its
// final fixed executable destination is intercepted in this independent probe.
#define execve probe_execve
#include "executor_fd.c"
#undef execve

static char **guest_arguments;
static void fail(const char *operation) {
    fprintf(stderr, "{\"probe\":\"failed\",\"operation\":\"%s\",\"errno\":%d}\n", operation, errno);
    exit(1);
}
static void require(int condition, const char *operation) {
    if (!condition) { errno = EINVAL; fail(operation); }
}
static void seed_step(const char *operation, long long result) {
    fprintf(stderr, "{\"phase\":\"seed-step\",\"operation\":\"%s\",\"status\":\"ok\",\"result\":%lld}\n", operation, result);
    fflush(stderr);
}

// Metadata only. Preserve the caller's errno even when a diagnostic fails.
static void meta_error(const char *stage, const char *operation, int error) {
    fprintf(stderr, "{\"phase\":\"seed-metadata\",\"stage\":\"%s\",\"operation\":\"%s\",\"status\":\"unavailable\",\"errno\":%d}\n", stage, operation, error);
}
static void meta_text(const char *stage, const char *operation, const unsigned char *text, size_t size) {
    fprintf(stderr, "{\"phase\":\"seed-metadata\",\"stage\":\"%s\",\"operation\":\"%s\",\"status\":\"ok\",\"value\":\"", stage, operation);
    // Byte escaping keeps labels and procfd links valid JSON without logging content.
    for (size_t i = 0; i < size; ++i) fprintf(stderr, "\\u%04x", (unsigned)text[i]);
    fputs("\"}\n", stderr);
}
static void seed_metadata(int fd, const char *stage) {
    int saved_errno = errno;
    struct stat value;
    if (fstat(fd, &value)) meta_error(stage, "fstat", errno);
    else fprintf(stderr, "{\"phase\":\"seed-metadata\",\"stage\":\"%s\",\"operation\":\"fstat\",\"status\":\"ok\",\"pid\":%ld,\"uid\":%ju,\"gid\":%ju,\"mode_octal\":\"%06jo\",\"nlink\":%ju,\"size\":%jd,\"dev\":%ju,\"ino\":%ju}\n",
                 stage, (long)getpid(), (uintmax_t)value.st_uid, (uintmax_t)value.st_gid,
                 (uintmax_t)value.st_mode, (uintmax_t)value.st_nlink, (intmax_t)value.st_size,
                 (uintmax_t)value.st_dev, (uintmax_t)value.st_ino);
    const int commands[] = {F_GETFD, F_GETFL, F_GET_SEALS};
    const char *names[] = {"F_GETFD", "F_GETFL", "F_GET_SEALS"};
    for (size_t i = 0; i < 3; ++i) {
        int result = fcntl(fd, commands[i]);
        if (result < 0) meta_error(stage, names[i], errno);
        else fprintf(stderr, "{\"phase\":\"seed-metadata\",\"stage\":\"%s\",\"operation\":\"%s\",\"status\":\"ok\",\"result\":%d}\n", stage, names[i], result);
    }
    char path[64];
    unsigned char text[512];
    snprintf(path, sizeof(path), "/proc/self/fd/%d", fd);
    ssize_t size = readlink(path, (char *)text, sizeof(text));
    if (size < 0) meta_error(stage, "procfd_readlink", errno);
    else if ((size_t)size == sizeof(text)) meta_error(stage, "procfd_readlink", EOVERFLOW);
    else meta_text(stage, "procfd_readlink", text, (size_t)size);
    size = fgetxattr(fd, "security.selinux", text, sizeof(text));
    if (size < 0) meta_error(stage, "security.selinux", errno);
    else {
        if (size > 0 && text[size - 1] == 0) --size;
        meta_text(stage, "security.selinux", text, (size_t)size);
    }
    fflush(stderr);
    errno = saved_errno;
}

static uint64_t number(const char *text) {
    char *end;
    require(text[0] >= '0' && text[0] <= '9', "unsigned decimal expected");
    errno = 0;
    unsigned long long value = strtoull(text, &end, 10);
    require(errno == 0 && *end == 0, "invalid decimal");
    return value;
}
static struct stat metadata(int fd) {
    struct stat value;
    if (fstat(fd, &value) != 0) fail("fstat");
    return value;
}
static unsigned int actual_id(int group) {
    FILE *input = fopen("/proc/self/status", "r");
    if (!input) fail("open proc status");
    char line[1024];
    unsigned int real, effective, saved, filesystem;
    while (fgets(line, sizeof(line), input)) {
        if (sscanf(line, group ? "Gid: %u %u %u %u" : "Uid: %u %u %u %u", &real, &effective, &saved, &filesystem) == 4) {
            fclose(input);
            require(real == effective && real == saved && real == filesystem, "proc credential fields differ");
            return real;
        }
    }
    fclose(input); errno = EINVAL; fail("proc credential absent"); return 0;
}
static unsigned int actual_uid(void) { return actual_id(0); }
static unsigned int actual_gid(void) { return actual_id(1); }
static void same(struct stat a, struct stat b, const char *label) {
    require(a.st_dev == b.st_dev && a.st_ino == b.st_ino, label);
}

static int app_phase(const char *phase) {
    return !strcmp(phase, "check-app-anon-v1") || !strcmp(phase, "received-app-anon-v1");
}
static void app_credentials(uint64_t uid, uint64_t gid) {
    unsigned int proc_uid = actual_uid(), proc_gid = actual_gid();
    fprintf(stderr, "{\"phase\":\"app-credentials\",\"actual_uid\":%u,\"actual_gid\":%u,\"getuid\":%u,\"geteuid\":%u,\"getgid\":%u,\"getegid\":%u}\n",
            proc_uid, proc_gid, (unsigned)getuid(), (unsigned)geteuid(), (unsigned)getgid(), (unsigned)getegid());
    require(proc_uid == uid && getuid() == uid && geteuid() == uid &&
            proc_gid == gid && getgid() == gid && getegid() == gid, "app credential translation or mismatch");
}
static struct stat app_memfd(int fd, uint64_t uid, uint64_t gid, int created) {
    struct stat value = metadata(fd);
    require(S_ISREG(value.st_mode) && (value.st_mode & 07777) == 0666 &&
            value.st_uid == uid && value.st_gid == gid && value.st_nlink == 0 &&
            value.st_size == (created ? 0 : 16), "app anonymous metadata mismatch");
    int seals = fcntl(fd, F_GET_SEALS);
    if (seals < 0) fail("app F_GET_SEALS");
    require(seals == (created ? 32 : 47), "app exact seals mismatch");
    int flags = fcntl(fd, F_GETFL), fdflags = fcntl(fd, F_GETFD);
    if (flags < 0 || fdflags < 0) fail("app FD flags query");
    require((flags & O_ACCMODE) == O_RDWR && !(flags & O_APPEND), "app FD access mismatch");
    if (created) require(fdflags == FD_CLOEXEC, "app initial CLOEXEC mismatch");
    return value;
}
static void immutable(int fd, const unsigned char expected[16]) {
    errno = 0;
    require(pwrite(fd, expected, 1, 0) == -1 && errno == EPERM, "app sealed write not EPERM");
    errno = 0;
    require(ftruncate(fd, 15) == -1 && errno == EPERM, "app sealed shrink not EPERM");
    errno = 0;
    require(ftruncate(fd, 17) == -1 && errno == EPERM, "app sealed grow not EPERM");
    unsigned char content[16];
    require(metadata(fd).st_size == 16, "app sealed size changed");
    if (pread(fd, content, sizeof(content), 0) != 16) fail("app sealed readback");
    require(!memcmp(expected, content, 16), "app sealed content changed");
}
static void android_app_label(int fd) {
#ifdef __ANDROID__
    char label[512], context[512];
    ssize_t count = fgetxattr(fd, "security.selinux", label, sizeof(label) - 1);
    if (count < 0) fail("app seed SELinux label");
    label[count] = 0;
    FILE *input = fopen("/proc/self/attr/current", "r");
    if (!input) fail("app seed SELinux current context");
    char *result = fgets(context, sizeof(context), input);
    fclose(input);
    require(result != NULL && strlen(context) < sizeof(context) - 1, "app seed context unavailable or truncated");
    context[strcspn(context, "\n")] = 0;
    const char prefix[] = "u:r:untrusted_app:";
    const char object[] = "u:object_r:appdomain_tmpfs:";
    require(!strncmp(context, prefix, sizeof(prefix) - 1) &&
            !strncmp(label, object, sizeof(object) - 1) &&
            !strcmp(context + sizeof(prefix) - 1, label + sizeof(object) - 1), "app seed SELinux domain or category mismatch");
#else
    (void)fd; // Linux controls do not attest Android SELinux policy.
#endif
}

static void inspect(char **args) {
    int app = app_phase(args[1]);
    if (app) app_credentials(number(args[2]), number(args[12]));
    require(actual_uid() == number(args[2]), "actual UID mismatch");
    struct stat root = metadata(3), memory = metadata(4);
    require(S_ISDIR(root.st_mode), "root FD is not directory");
    require((uint64_t)root.st_dev == number(args[3]) && (uint64_t)root.st_ino == number(args[4]), "root identity changed");
    require((uint64_t)memory.st_dev == number(args[5]) && (uint64_t)memory.st_ino == number(args[6]), "memfd identity changed");
    if (app) {
        (void)app_memfd(4, number(args[2]), number(args[12]), 0);
        require(root.st_uid == number(args[2]) && !(root.st_mode & 0022), "app root owner or mode mismatch");
    } else require(S_ISREG(memory.st_mode) && memory.st_nlink == 0 && (memory.st_mode & 0777) == 0600, "memfd metadata differs");
    int seals = fcntl(4, F_GET_SEALS);
    if (seals < 0) fail("F_GET_SEALS inherited");
    require((uint64_t)seals == number(args[7]) && (seals & 15) == 15, "memfd seals differ");
    require(strlen(args[8]) == 32 && memory.st_size == 16, "payload size differs");
    unsigned char expected[16], content[16];
    for (int i = 0; i < 16; ++i) {
        char pair[3] = {args[8][2*i], args[8][2*i+1], 0};
        char *end;
        unsigned long value = strtoul(pair, &end, 16);
        require(*end == 0, "invalid payload hex"); expected[i] = (unsigned char)value;
    }
    if (pread(4, content, sizeof(content), 0) != 16) fail("pread inherited memfd");
    require(memcmp(expected, content, 16) == 0, "memfd content changed");
    int guest_root = open("/", O_RDONLY | O_DIRECTORY | O_CLOEXEC);
    int proc_root = open("/proc/self/fd/3", O_RDONLY | O_DIRECTORY | O_CLOEXEC);
    int proc_memory = open("/proc/self/fd/4", (app ? O_RDWR : O_RDONLY) | O_CLOEXEC);
    if (guest_root < 0 || proc_root < 0 || proc_memory < 0) fail("open guest or procfd");
    same(root, metadata(guest_root), "guest slash differs from retained real root");
    same(root, metadata(proc_root), "root procfd differs");
    same(memory, metadata(proc_memory), "memfd procfd differs");
    require(fcntl(proc_memory, F_GET_SEALS) == seals, "procfd seals differ");
    if (pread(proc_memory, content, sizeof(content), 0) != 16) fail("pread procfd memfd");
    require(memcmp(expected, content, 16) == 0, "procfd content differs");
    if (app) {
        (void)app_memfd(proc_memory, number(args[2]), number(args[12]), 0);
        immutable(4, expected);
        immutable(proc_memory, expected);
    }
    close(guest_root); close(proc_root); close(proc_memory);
    errno = 0;
    require(pwrite(4, expected, 1, 0) == -1 && errno == EPERM, "sealed memfd write not rejected");
    int executable = open("/proc/self/exe", O_RDONLY | O_CLOEXEC);
    int program = open(args[0], O_RDONLY | O_CLOEXEC);
    if (executable < 0 || program < 0) fail("open executable identity");
    struct stat exe = metadata(executable), binary = metadata(program);
    int self_is_program = exe.st_dev == binary.st_dev && exe.st_ino == binary.st_ino;
    if (!strcmp(args[9], "direct")) require(self_is_program, "direct proc exe differs from program");
    else {
        int loader = open(args[10], O_RDONLY | O_CLOEXEC);
        if (loader < 0) fail("open loader identity");
        same(exe, metadata(loader), "proc exe differs from requested loader"); close(loader);
    }
    close(executable); close(program);
    printf("{\"phase\":\"%s\",\"actual_uid\":%u,\"guest_euid\":%u,\"root_inode\":\"%" PRIu64 "\",\"memfd_inode\":\"%" PRIu64 "\",\"seals\":%d,\"root_procfd_guest_match\":true,\"content_match\":true,\"immutable\":true,\"proc_exe_is_program\":%s}\n",
           args[1], actual_uid(), (unsigned)geteuid(), (uint64_t)root.st_ino, (uint64_t)memory.st_ino, seals, self_is_program ? "true" : "false");
    fflush(stdout);
}
static int probe_execve(const char *path, char *const argv[], char *const envp[]) {
    require(!strcmp(path, "/usr/libexec/dnfast-executor") && !strcmp(argv[1], "--plan-fd") && !strcmp(argv[2], "3"), "unexpected native fixed launch contract");
    int app = app_phase(guest_arguments[1]);
    guest_arguments[1] = app ? "received-app-anon-v1" : "received";
    if (!strcmp(guest_arguments[9], "direct")) return execve(guest_arguments[0], guest_arguments, envp);
    char *loaded[17] = {guest_arguments[10], "--library-path", guest_arguments[11]};
    int count = app ? 13 : 12;
    for (int i = 0; i < count; ++i) loaded[i+3] = guest_arguments[i];
    loaded[count+3] = NULL;
    return execve(loaded[0], loaded, envp);
}
static void seed(int argc, char **argv) {
    int app = !strcmp(argv[1], "seed-app-anon-v1");
    require(argc >= 10 && !strcmp(argv[8], "--"), "seed ROOT UID MODE GUEST_PROBE LOADER LIBPATH -- EXEC_ARGV");
    require(!strcmp(argv[4], "direct") || !strcmp(argv[4], "loader"), "invalid seed mode");
    require(actual_uid() == number(argv[3]) && getuid() == number(argv[3]) && geteuid() == number(argv[3]), "seed must see actual expected UID");
    if (app) app_credentials(number(argv[3]), actual_gid());
    int root = open(argv[2], O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
    if (root < 0) fail("open seed root");
    struct stat root_stat = metadata(root);
    require(root_stat.st_uid == getuid() && !(root_stat.st_mode & 0022), "seed root ownership or mode");
    // Original flags11 in both modes; only explicit app mode accepts measured0666.
    int memory = (int)syscall(SYS_memfd_create, "dnfast-fd-feasibility", 1U | 2U | 8U);
    if (memory < 0) fail("memfd_create NOEXEC_SEAL");
    seed_step("memfd_create CLOEXEC|ALLOW_SEALING|NOEXEC_SEAL", memory);
    seed_metadata(memory, "after-create");
    struct stat initial = metadata(memory);
    if (app) {
        initial = app_memfd(memory, actual_uid(), actual_gid(), 1);
        android_app_label(memory);
        seed_step("app-anon-v1 initial contract", 32);
    }
    unsigned char content[16];
    ssize_t count_random = getrandom(content, sizeof(content), 0);
    if (count_random < 0) fail("getrandom seed payload");
    if (count_random != 16) { errno = EIO; fail("getrandom seed payload short read"); }
    seed_step("getrandom seed payload", count_random);
    if (!app) {
        if (fchmod(memory, 0600)) {
            int chmod_errno = errno;
            seed_metadata(memory, "after-fchmod-failure");
            errno = chmod_errno;
            fail("fchmod memfd mode0600");
        }
        seed_step("fchmod memfd mode0600", 0);
    }
    ssize_t count_written = write(memory, content, 16);
    if (count_written < 0) fail("write memfd payload");
    if (count_written != 16) { errno = EIO; fail("write memfd payload short write"); }
    seed_step("write memfd payload", count_written);
    if (fsync(memory)) fail("fsync memfd");
    seed_step("fsync memfd", 0);
    off_t offset = lseek(memory, 0, SEEK_SET);
    if (offset < 0) fail("lseek memfd SEEK_SET0");
    seed_step("lseek memfd SEEK_SET0", (long long)offset);
    if (fcntl(memory, F_ADD_SEALS, 15)) fail("fcntl memfd F_ADD_SEALS mask15");
    seed_step("fcntl memfd F_ADD_SEALS mask15", 0);
    struct stat memory_stat = metadata(memory);
    if (app) {
        memory_stat = app_memfd(memory, actual_uid(), actual_gid(), 0);
        same(initial, memory_stat, "app seed memfd identity changed");
        immutable(memory, content);
        seed_metadata(memory, "after-app-seal");
        seed_step("app-anon-v1 sealed contract", 47);
    }
    char values[8][48];
    snprintf(values[7],48,"%u",actual_gid());
    snprintf(values[0],48,"%u",getuid());
    snprintf(values[1],48,"%" PRIu64,(uint64_t)root_stat.st_dev);
    snprintf(values[2],48,"%" PRIu64,(uint64_t)root_stat.st_ino);
    snprintf(values[3],48,"%" PRIu64,(uint64_t)memory_stat.st_dev);
    snprintf(values[4],48,"%" PRIu64,(uint64_t)memory_stat.st_ino);
    int seals = fcntl(memory,F_GET_SEALS);
    if (seals < 0) fail("fcntl memfd F_GET_SEALS");
    seed_step("fcntl memfd F_GET_SEALS", seals);
    snprintf(values[5],48,"%d",seals);
    for (int i=0;i<16;++i) snprintf(values[6]+2*i,3,"%02x",content[i]);
    int safe_root = fcntl(root,F_DUPFD_CLOEXEC,10), safe_memory = fcntl(memory,F_DUPFD_CLOEXEC,10);
    if (safe_root < 0 || safe_memory < 0) fail("duplicate seed descriptors");
    close(root); close(memory);
    if (dup3(safe_root,3,0) < 0 || dup3(safe_memory,4,0) < 0) fail("seed fixed FD layout");
    close(safe_root); close(safe_memory);
    require(argv[5][0] == '/', "guest probe path must be absolute");
    char **command = calloc((size_t)argc + 18, sizeof(char *));
    if (!command) fail("calloc seed argv");
    int count=0;
    for (int i=9;i<argc;++i) command[count++]=argv[i];
    if (!strcmp(argv[4],"loader")) { command[count++]=argv[6]; command[count++]="--library-path"; command[count++]=argv[7]; }
    command[count++]=argv[5]; command[count++]=app ? "check-app-anon-v1" : "check";
    for (int i=0;i<7;++i) command[count++]=values[i];
    command[count++]=argv[4]; command[count++]=argv[6]; command[count++]=argv[7];
    if (app) command[count++]=values[7];
    command[count]=NULL;
    printf("{\"phase\":\"seed\",\"actual_uid\":%u,\"root_inode\":\"%s\",\"memfd_inode\":\"%s\",\"seals\":%s}\n",getuid(),values[2],values[4],values[5]); fflush(stdout);
    if (setenv("DNFAST_FD_PROBE_MARKER","present-before-native-handoff",1)) fail("setenv marker");
    execv(command[0], command); fail("exec seed command");
}
int main(int argc, char **argv) {
    if (argc > 1 && (!strcmp(argv[1],"seed") || !strcmp(argv[1],"seed-app-anon-v1"))) seed(argc,argv);
    int app = argc > 1 && app_phase(argv[1]);
    require((app && argc == 13) || (argc == 12 && (!strcmp(argv[1],"check") || !strcmp(argv[1],"received"))), "invalid guest probe argv");
    require(!strcmp(argv[9],"direct") || !strcmp(argv[9],"loader"), "invalid guest mode");
    inspect(argv);
    if (!strcmp(argv[1],"received") || !strcmp(argv[1],"received-app-anon-v1")) {
        require(getenv("DNFAST_FD_PROBE_MARKER") == NULL, "native environment clear failed");
        errno=0; require(fcntl(200,F_GETFD)==-1 && errno==EBADF,"close_range sentinel survived");
        puts("{\"phase\":\"complete\",\"native_compact_handoff\":true,\"close_range\":true,\"environment_cleared\":true,\"production_executor_invoked\":false}"); return 0;
    }
    int root=dnfast_executor_take_plan_fd(), memory=dnfast_executor_take_compact_fd();
    if (root < 0 || memory < 0) fail("native take inherited FDs");
    if (dup3(root,200,O_CLOEXEC) < 0) fail("create close_range sentinel");
    // Deliberately clear CLOEXEC so only close_range can remove the sentinel.
    if (fcntl(200,F_SETFD,0)) fail("clear sentinel CLOEXEC");
    guest_arguments=argv;
    dnfast_executor_exec_compact(root,memory,NULL,0,DNFAST_EXECUTOR_ASSUME_NO);
    fail("native compact handoff returned"); return 1;
}
