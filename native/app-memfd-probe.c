#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <sys/utsname.h>
#include <sys/xattr.h>
#include <unistd.h>

/* Run before PRoot as the app UID. Only anonymous, disposable FDs are changed. */
int main(void) {
    struct utsname kernel;
    if (uname(&kernel)) return 1;
    printf("kernel=%s uid=%u euid=%u gid=%u\n", kernel.release,
           (unsigned)getuid(), (unsigned)geteuid(), (unsigned)getgid());
    const unsigned flags[] = {11, 3};
    for (unsigned i = 0; i < sizeof(flags) / sizeof(flags[0]); i++) {
        errno = 0;
        int fd = (int)syscall(SYS_memfd_create, "dnfast-memfd-probe", flags[i]);
        int error = errno;
        printf("flags=%u create=%d errno=%d (%s)\n", flags[i], fd, error, strerror(error));
        if (fd < 0) continue;
        struct stat st;
        if (fstat(fd, &st)) return 1;
        printf("initial mode=%04o uid=%u gid=%u links=%lu size=%lld seals=%d\n",
               st.st_mode & 07777, (unsigned)st.st_uid, (unsigned)st.st_gid,
               (unsigned long)st.st_nlink, (long long)st.st_size, fcntl(fd, F_GET_SEALS));
        char label[512];
        ssize_t n = fgetxattr(fd, "security.selinux", label, sizeof(label) - 1);
        if (n >= 0) { label[n] = 0; printf("label=%s\n", label); }
        if (write(fd, "{}", 2) != 2 || fsync(fd)) return 1;
        errno = 0;
        int rc = fcntl(fd, F_ADD_SEALS, 15);
        error = errno;
        printf("add_seals15=%d errno=%d final_seals=%d\n", rc, error, fcntl(fd, F_GET_SEALS));
        errno = 0; rc = (int)pwrite(fd, "x", 1, 0); error = errno;
        printf("pwrite=%d errno=%d\n", rc, error);
        errno = 0; rc = ftruncate(fd, 0); error = errno;
        printf("shrink=%d errno=%d\n", rc, error);
        errno = 0; rc = ftruncate(fd, 3); error = errno;
        printf("grow=%d errno=%d\n", rc, error);
        errno = 0; rc = fcntl(fd, F_ADD_SEALS, 16); error = errno;
        printf("add_after_seal=%d errno=%d\n", rc, error);
        errno = 0;
        void *mapping = mmap(NULL, 2, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
        error = errno;
        printf("shared_write_map=%s errno=%d\n", mapping == MAP_FAILED ? "failed" : "allowed", error);
        if (mapping != MAP_FAILED) munmap(mapping, 2);
        /* Independent metadata probe; no production code relies on chmod. */
        errno = 0; rc = fchmod(fd, 0600); error = errno;
        if (fstat(fd, &st)) return 1;
        printf("chmod0600=%d errno=%d mode=%04o\n", rc, error, st.st_mode & 07777);
        close(fd);
    }
    return 0;
}
