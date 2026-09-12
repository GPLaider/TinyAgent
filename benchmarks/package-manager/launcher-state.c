#define _GNU_SOURCE
#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>

static unsigned long mkdir_calls, sync_calls;
static int counted_mkdirat(int fd, const char *name, mode_t mode) {
    ++mkdir_calls; return mkdirat(fd, name, mode);
}
static int counted_fsync(int fd) { ++sync_calls; return fsync(fd); }
#define mkdirat counted_mkdirat
#define fsync counted_fsync
#define main launcher_main
#ifndef LAUNCHER_SOURCE
#define LAUNCHER_SOURCE "../../native/dnfast-launch.c"
#endif
#include LAUNCHER_SOURCE
#undef main
#undef fsync
#undef mkdirat

static uint64_t now_ns(void) {
    struct timespec value; assert(clock_gettime(CLOCK_MONOTONIC, &value) == 0);
    return (uint64_t)value.tv_sec * 1000000000ULL + (uint64_t)value.tv_nsec;
}
int main(int argc, char **argv) {
    assert(argc == 4);
    char *end;
    long iterations = strtol(argv[3], &end, 10);
    assert(*argv[3] && !*end && iterations > 0 && iterations <= 100000);
    int warm = !strcmp(argv[2], "warm");
    assert(warm || !strcmp(argv[2], "first"));
    /* Caller supplies a disposable empty directory; state remains inside it. */
    int root = open_root(argv[1]);
    assert(flock(root, LOCK_EX | LOCK_NB) == 0);
    const char *id = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
    if (warm) {
        int state = state_directory(root, id); close(state);
    } else assert(iterations == 1);
    mkdir_calls = sync_calls = 0;
    uint64_t started = now_ns();
    for (long i = 0; i < iterations; ++i) {
        int state = state_directory(root, id); close(state);
    }
    uint64_t elapsed = now_ns() - started;
    close(root);
    printf("{\"iterations\":%ld,\"ns_per_traversal\":%.3f,\"mkdirat_per_traversal\":%lu,\"fsync_per_traversal\":%lu}\n",
           iterations, (double)elapsed / iterations,
           mkdir_calls / (unsigned long)iterations, sync_calls / (unsigned long)iterations);
    return 0;
}
