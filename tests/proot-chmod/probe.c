#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <unistd.h>

static int mode(const char *p) { struct stat s; return stat(p, &s) ? -1 : s.st_mode & 0777; }
int main(int argc, char **argv) {
    if (argc != 2) return 9;
    if (!strcmp(argv[1], "heartbeat")) {
        FILE *status = fopen("/proc/self/status", "r");
        char line[256]; int tracer = 0;
        if (!status) return 22;
        while (fgets(line, sizeof(line), status)) if (sscanf(line, "TracerPid: %d", &tracer) == 1) break;
        fclose(status);
        if (tracer <= 1) return 23;
        FILE *pidfile = fopen("/probe/tracer.pid", "w");
        if (!pidfile) return 24;
        fprintf(pidfile, "%d\n", tracer); fclose(pidfile);
        for (unsigned i = 0; i < 200; i++) {
            FILE *file = fopen("/probe/heartbeat", "w");
            if (!file) return 20;
            fprintf(file, "%u\n", i);
            fclose(file);
            usleep(100000);
        }
        return 21;
    }
    int candidate = !strcmp(argv[1], "candidate");
    if (mkdir("/probe/owned", 0700) || chmod("/probe/owned", 0700)) return 10;
    errno = 0;
    long absolute = syscall(452, AT_FDCWD, "/probe/owned", 0750, 0);
    int error = errno, actual = mode("/probe/owned");
    printf("absolute return=%ld errno=%d mode=%o\n", absolute, error, actual);
    if (candidate ? (absolute || actual != 0750) : (absolute != -1 || error != ENOENT || actual != 0700)) return 11;
    int fd = open("/probe", O_RDONLY | O_DIRECTORY);
    if (fd < 0 || syscall(452, fd, "owned", 0700, 0) || mode("/probe/owned") != 0700) return 12;
    close(fd);
    puts("relative PASS");
    if (candidate) {
        if (symlink("owned", "/probe/link")) return 13;
        errno = 0;
        long link = syscall(452, AT_FDCWD, "/probe/link", 0777, AT_SYMLINK_NOFOLLOW);
        printf("nofollow return=%ld errno=%d target_mode=%o\n", link, errno, mode("/probe/owned"));
        if (mode("/probe/owned") != 0700) return 14;
        errno = 0;
        if (syscall(452, AT_FDCWD, "/probe/owned", 0777, 0x40000000) != -1 || errno != EINVAL) return 15;
        if (mode("/probe/owned") != 0700) return 16;
        unlink("/probe/link");
        puts("invalid flags PASS");
    }
    rmdir("/probe/owned");
    puts(candidate ? "PASS candidate" : "PASS baseline defect reproduced");
    return 0;
}
