#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/file.h>
#include <sys/random.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <sys/xattr.h>
#include <unistd.h>

/* Same-UID launcher, not an authority boundary against other app-owned code. */
static void die(const char *operation) { perror(operation); exit(1); }
static void require(int ok, const char *operation) {
    if (!ok) { errno = EINVAL; die(operation); }
}
static struct stat metadata(int fd) {
    struct stat value;
    if (fstat(fd, &value)) die("fstat");
    return value;
}
static void private_directory(int fd) {
    struct stat value = metadata(fd);
    require(S_ISDIR(value.st_mode) && value.st_uid == getuid() && value.st_gid == getgid() && !(value.st_mode & 0022), "app-owned directory UID/GID");
}
static int child_directory(int parent, const char *name) {
    require(*name && !strchr(name, '/') && strcmp(name, ".") && strcmp(name, ".."), "directory component");
    int fd = openat(parent, name, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
    if (fd < 0 && errno == ENOENT) {
        if (mkdirat(parent, name, 0700) && errno != EEXIST) die("mkdirat state");
        fd = openat(parent, name, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
    }
    if (fd < 0) die("openat state directory");
    private_directory(fd);
    /* Also sync existing entries: they may come from an interrupted mkdir. */
    if (fsync(parent)) die("fsync state parent");
    return fd;
}
static int open_root(const char *path) {
    require(path[0] == '/' && strlen(path) < 4096, "absolute root path");
    char copy[4096]; strcpy(copy, path);
    /* Android permits ancestor traversal, not directory listing. Keep each
       component anchored and nofollow; only the app-owned leaf needs reading. */
    int fd = open("/", O_PATH | O_DIRECTORY | O_CLOEXEC);
    if (fd < 0) die("open slash");
    char *save = NULL;
    for (char *part = strtok_r(copy, "/", &save); part; part = strtok_r(NULL, "/", &save)) {
        require(strcmp(part, ".") && strcmp(part, ".."), "root component");
        int next = openat(fd, part, O_PATH | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
        if (next < 0) {
            int saved = errno;
            fprintf(stderr, "root ancestor=%s path=%s\n", part, path);
            errno = saved; die("openat root ancestor");
        }
        close(fd); fd = next;
    }
    int readable = openat(fd, ".", O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
    if (readable < 0) die("open app root");
    close(fd);
    private_directory(readable);
    return readable;
}
static int hex64(const char *value) {
    return strlen(value) == 64 && strspn(value, "0123456789abcdef") == 64;
}
static void actual_credentials(void) {
    FILE *input = fopen("/proc/self/status", "r");
    if (!input) die("open process status");
    char line[1024]; unsigned long a, b, c, d; unsigned long long caps; int seen = 0;
    while (fgets(line, sizeof(line), input)) {
        if (sscanf(line, "Uid: %lu %lu %lu %lu", &a, &b, &c, &d) == 4) {
            require(a == getuid() && a == b && a == c && a == d, "kernel UID mismatch"); seen |= 1;
        } else if (sscanf(line, "Gid: %lu %lu %lu %lu", &a, &b, &c, &d) == 4) {
            require(a == getgid() && a == b && a == c && a == d, "kernel GID mismatch"); seen |= 2;
        } else if (sscanf(line, "CapEff: %llx", &caps) == 1) {
            require(caps == 0, "unexpected effective capabilities"); seen |= 4;
        }
    }
    fclose(input); require(seen == 7, "incomplete process identity");
}
static void write_all(int fd, const char *bytes, size_t size) {
    while (size) {
        ssize_t count = write(fd, bytes, size);
        if (count < 0 && errno == EINTR) continue;
        if (count <= 0) die("write");
        bytes += count; size -= (size_t)count;
    }
}
static void root_id(int root, char value[65]) {
    const char *name = ".tinyagent-root-id";
    int fd = openat(root, name, O_RDONLY | O_NOFOLLOW | O_CLOEXEC);
    if (fd < 0 && errno == ENOENT) {
        unsigned char random[32];
        require(getrandom(random, sizeof(random), 0) == sizeof(random), "root ID random");
        for (size_t i = 0; i < sizeof(random); i++) snprintf(value + i * 2, 3, "%02x", random[i]);
        char temporary[96]; snprintf(temporary, sizeof(temporary), ".tinyagent-root-id.stage-%s", value);
        fd = openat(root, temporary, O_RDWR | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0600);
        if (fd < 0) die("stage root ID");
        write_all(fd, value, 64);
        if (fsync(fd)) die("sync staged root ID");
        if (syscall(SYS_renameat2, root, temporary, root, name, 1U)) die("publish root ID without replacement");
        if (fsync(root)) die("sync root ID directory");
    } else if (fd < 0) die("open root ID");
    struct stat info = metadata(fd);
    require(S_ISREG(info.st_mode) && info.st_uid == getuid() && (info.st_mode & 07777) == 0600 && info.st_nlink == 1 && info.st_size == 64, "root ID metadata; never regenerate invalid ID");
    require(pread(fd, value, 64, 0) == 64, "read root ID");
    value[64] = 0;
    require(hex64(value), "root ID encoding");
    close(fd);
}
static int state_directory(int root, const char *id) {
    int fd = fcntl(root, F_DUPFD_CLOEXEC, 10);
    if (fd < 0) die("duplicate root");
    const char *parts[] = {"var", "lib", "dnfast", "app-proot", id};
    for (size_t i = 0; i < sizeof(parts) / sizeof(parts[0]); i++) {
        int next = child_directory(fd, parts[i]);
        close(fd); fd = next;
    }
    require((metadata(fd).st_mode & 07777) == 0700, "private state mode0700");
    return fd;
}
static void app_label(int fd) {
#ifdef __ANDROID__
    char label[512], context[512];
    ssize_t count = fgetxattr(fd, "security.selinux", label, sizeof(label) - 1);
    if (count < 0 || count == sizeof(label) - 1) die("memfd SELinux label");
    label[count] = 0;
    FILE *input = fopen("/proc/self/attr/current", "r");
    if (!input) die("process SELinux context");
    require(fgets(context, sizeof(context), input) != NULL && strlen(context) < sizeof(context) - 1, "process context length");
    fclose(input); context[strcspn(context, "\n")] = 0;
    const char *process = "u:r:untrusted_app:", *object = "u:object_r:appdomain_tmpfs:";
    require(!strncmp(context, process, strlen(process)) && !strncmp(label, object, strlen(object)) &&
            !strcmp(context + strlen(process), label + strlen(object)), "app SELinux domain/category");
#else
    (void)fd; /* Linux unit controls do not attest Android labels. */
#endif
}
static int sealed_context(const char *json, size_t size) {
    require(size > 0 && size <= 16384, "context length");
    int fd = (int)syscall(SYS_memfd_create, "tinyagent-dnfast-context", 11U);
    unsigned mode = 0666;
    int initial_seals = 32;
    if (fd < 0 && errno == EINVAL) {
        /* Legacy kernels seal bytes/size, but cannot freeze execution bits.
           Same-UID app data only; no permission-error fallback or chmod. */
        fd = (int)syscall(SYS_memfd_create, "tinyagent-dnfast-context", 3U);
        mode = 0777;
        initial_seals = 0;
    }
    if (fd < 0) die("memfd_create context");
    struct stat before = metadata(fd);
    require(S_ISREG(before.st_mode) && (before.st_mode & 07777) == mode && before.st_uid == getuid() &&
            before.st_gid == getgid() && before.st_nlink == 0 && before.st_size == 0 && fcntl(fd, F_GET_SEALS) == initial_seals, "initial anonymous context");
    app_label(fd);
    write_all(fd, json, size);
    if (fsync(fd) || lseek(fd, 0, SEEK_SET) < 0 || fcntl(fd, F_ADD_SEALS, 15)) die("seal context");
    struct stat after = metadata(fd);
    require(before.st_dev == after.st_dev && before.st_ino == after.st_ino && after.st_size == (off_t)size &&
            after.st_uid == before.st_uid && after.st_gid == before.st_gid && after.st_mode == before.st_mode &&
            after.st_nlink == 0 && fcntl(fd, F_GET_SEALS) == (initial_seals | 15), "sealed context identity");
    return fd;
}
int main(int argc, char **argv) {
    require(argc >= 9 && !strcmp(argv[7], "--"), "ROOT UID RUNTIME_HASH BINDS_HASH DNFAST_HASH EXECUTOR_HASH -- PROOT ARGS");
    char *end = NULL;
    errno = 0; unsigned long expected = strtoul(argv[2], &end, 10);
    require(!errno && end != argv[2] && !*end && expected >= 10000 && expected <= UINT32_MAX &&
            getuid() == expected && geteuid() == expected && getgid() == getegid(), "actual app identity");
    actual_credentials();
    for (int i = 3; i <= 6; i++) require(hex64(argv[i]), "pinned hash encoding");
    int root = open_root(argv[1]);
    if (flock(root, LOCK_EX | LOCK_NB)) die("Fedora root busy");
    char id[65]; root_id(root, id);
    int state = state_directory(root, id);
    struct stat r = metadata(root), s = metadata(state);
    /* Fixed ASCII-only schema, sorted keys: matches dnfast-core JCS encoding. */
    char json[2048];
    int length = snprintf(json, sizeof(json),
        "{\"binding\":{\"actual_gid\":%ju,\"actual_uid\":%ju,\"backend\":\"app-proot-v1\",\"binds_sha256\":\"%s\",\"dnfast_sha256\":\"%s\",\"executor_sha256\":\"%s\",\"root_id\":\"%s\",\"runtime_sha256\":\"%s\",\"schema_version\":1},\"root_dev\":%ju,\"root_ino\":%ju,\"schema_version\":1,\"state_dev\":%ju,\"state_ino\":%ju}",
        (uintmax_t)getgid(), (uintmax_t)getuid(), argv[4], argv[5], argv[6], id, argv[3],
        (uintmax_t)r.st_dev, (uintmax_t)r.st_ino, (uintmax_t)s.st_dev, (uintmax_t)s.st_ino);
    require(length > 0 && (size_t)length < sizeof(json), "context encoding");
    int context = sealed_context(json, (size_t)length);
    int safe_root = fcntl(root, F_DUPFD_CLOEXEC, 10), safe_context = fcntl(context, F_DUPFD_CLOEXEC, 10);
    if (safe_root < 0 || safe_context < 0) die("duplicate launch FDs");
    close(root); close(context); close(state);
    if (dup3(safe_root, 5, 0) < 0 || dup3(safe_context, 6, 0) < 0) die("publish launch FDs");
    close(safe_root); close(safe_context);
    execv(argv[8], argv + 8);
    die("exec pinned runtime");
    return 1;
}
