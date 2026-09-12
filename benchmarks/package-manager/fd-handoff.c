#define _GNU_SOURCE
#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/resource.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

/* Rootless host microbenchmark, not an Android or privilege-boundary test.
   Only the native euid gate and final destination are substituted. FD syscalls,
   clearenv, allocation and close_range execute normally in disposable processes. */
static unsigned long fcntl_calls, dup_calls, exec_calls;
static int fail_dup_at = -1, do_exec, expected_count, expected_approval;
static uid_t presented_euid;
static int measured_fcntl(int fd, int command, ...) {
    ++fcntl_calls;
    if (command == F_GETFD) return fcntl(fd, command);
    va_list args; va_start(args, command);
    int value = va_arg(args, int); va_end(args);
    return fcntl(fd, command, value);
}
static int measured_dup3(int oldfd, int newfd, int flags) {
    if ((int)dup_calls++ == fail_dup_at) { errno = EIO; return -1; }
    return dup3(oldfd, newfd, flags);
}
static uid_t host_test_euid(void) { return presented_euid; }
static int intercepted_exec(const char *, char *const [], char *const []);
#define fcntl measured_fcntl
#define dup3 measured_dup3
#define geteuid host_test_euid
#define execve intercepted_exec
#ifndef EXECUTOR_SOURCE
#define EXECUTOR_SOURCE "../../native/fd-gate/executor_fd.c"
#endif
#include EXECUTOR_SOURCE
#undef fcntl
#undef dup3
#undef geteuid
#undef execve

static int intercepted_exec(const char *path, char *const argv[], char *const envp[]) {
    ++exec_calls;
    if (!do_exec) { errno = ENOENT; return -1; }
    assert(!strcmp(path, "/usr/libexec/dnfast-executor"));
    assert(!strcmp(argv[1], "--plan-fd") && !strcmp(argv[2], "3"));
    assert(!strcmp(argv[3], "--compact-fd") && !strcmp(argv[4], "4"));
    assert(!strcmp(argv[5], "--artifact-fd-base") && !strcmp(argv[6], "5"));
    assert(!strcmp(argv[7], "--artifact-count") && atoi(argv[8]) == expected_count);
    if (!expected_approval) assert(argv[9] == NULL);
    else {
        assert(!strcmp(argv[9], expected_approval == 1 ? "--assumeyes" : "--assumeno"));
        assert(argv[10] == NULL);
    }
    assert(envp[0] && !strcmp(envp[0], "LANG=C.UTF-8") && envp[1] == NULL);
    assert(umask(0077) == 0077);
    /* A real exec proves target descriptors survive CLOEXEC processing. */
    char count[32]; snprintf(count, sizeof(count), "%d", expected_count);
    char *const next[] = {"fd-handoff", "--received", count, NULL};
    return execve("/proc/self/exe", next, envp);
}

static uint64_t now_ns(void) {
    struct timespec value; assert(clock_gettime(CLOCK_MONOTONIC, &value) == 0);
    return (uint64_t)value.tv_sec * 1000000000ULL + (uint64_t)value.tv_nsec;
}
static int number(const char *text, int maximum) {
    char *end; errno = 0; long value = strtol(text, &end, 10);
    assert(!errno && end != text && !*end && value >= 0 && value <= maximum);
    return (int)value;
}
static void receive(int count) {
    for (int i = 0; i < count + 2; ++i) {
        int value = -1;
        assert(pread(i + 3, &value, sizeof(value), 0) == sizeof(value));
        assert(value == count + 1 - i); /* Deliberately reversed source layout. */
        assert(fcntl(i + 3, F_GETFD) == 0);
    }
    assert(fcntl(count + 5, F_GETFD) == -1 && errno == EBADF);
    assert(fcntl(4096, F_GETFD) == -1 && errno == EBADF);
    assert(getenv("FD_HANDOFF_SENTINEL") == NULL);
}
static void success_case(int count, int approval) {
    assert(syscall(SYS_close_range, 3U, UINT_MAX, 0U) == 0);
    for (int i = 0; i < count + 2; ++i) {
        int fd = (int)syscall(SYS_memfd_create, "fd-handoff-test", 1U);
        assert(fd == i + 3);
        assert(write(fd, &i, sizeof(i)) == sizeof(i));
    }
    assert(dup3(3, 4096, 0) == 4096);
    int artifacts[1024];
    for (int i = 0; i < count; ++i) artifacts[i] = count + 2 - i;
    assert(setenv("FD_HANDOFF_SENTINEL", "must disappear", 1) == 0);
    do_exec = 1; expected_count = count; expected_approval = approval;
    dnfast_executor_exec_compact(count + 4, count + 3, artifacts, (size_t)count, (uint8_t)approval);
    assert(!"handoff must exec");
}
static void failure_case(int kind) {
    assert(syscall(SYS_close_range, 3U, UINT_MAX, 0U) == 0);
    assert(open("/dev/null", O_RDONLY | O_CLOEXEC) == 3);
    int artifacts[] = {3, -1};
    int result;
    if (kind == 0) result = dnfast_executor_exec_compact(3, 3, NULL, 1025, 0);
    else if (kind == 1) result = dnfast_executor_exec_compact(3, 3, NULL, 1, 0);
    else if (kind == 2) result = dnfast_executor_exec_compact(-1, 3, NULL, 0, 0);
    else if (kind == 3) { presented_euid = 1000; result = dnfast_executor_exec_compact(3, 3, NULL, 0, 0); }
    else if (kind == 4) result = dnfast_executor_exec_compact(3, 3, artifacts, 2, 0);
    else if (kind == 5) {
        fail_dup_at = 1;
        result = dnfast_executor_exec_compact(3, 3, artifacts, 1, 0);
    } else {
        struct rlimit limit = {6, 6}; assert(setrlimit(RLIMIT_NOFILE, &limit) == 0);
        result = dnfast_executor_exec_compact(3, 3, NULL, 0, 0);
    }
    assert(result == -1 && exec_calls == 0);
    assert(fcntl(3, F_GETFD) >= 0);
    /* No temporary duplicates may leak on a failed duplication/remap. */
    for (int fd = 5; fd < 32; ++fd) assert(fcntl(fd, F_GETFD) == -1 && errno == EBADF);
    if (kind < 4) assert(fcntl_calls == 0 && dup_calls == 0);
}
static void wait_success(pid_t pid) {
    int status; assert(pid >= 0 && waitpid(pid, &status, 0) == pid);
    assert(WIFEXITED(status) && WEXITSTATUS(status) == 0);
}
static void tests(void) {
    const int counts[] = {0, 1, 16, 256, 1024};
    for (size_t i = 0; i < sizeof(counts) / sizeof(counts[0]); ++i) {
        for (int approval = 0; approval < 3; ++approval) {
            pid_t pid = fork(); assert(pid >= 0);
            if (!pid) { success_case(counts[i], approval); _exit(1); }
            wait_success(pid);
        }
    }
    for (int kind = 0; kind < 7; ++kind) {
        pid_t pid = fork(); assert(pid >= 0);
        if (!pid) { failure_case(kind); _exit(0); }
        wait_success(pid);
    }
    puts("PASS 15 real-exec FD layouts/approval/environment/close_range cases; 7 rejection/cleanup cases");
}
static void benchmark(int count, int iterations) {
    assert(iterations > 0);
    assert(syscall(SYS_close_range, 3U, UINT_MAX, 0U) == 0);
    assert(open("/dev/null", O_RDONLY | O_CLOEXEC) == 3);
    int artifacts[1024];
    for (int i = 0; i < count; ++i) artifacts[i] = 3;
    /* Reuse one harmless source. Native duplication/remapping/close_range is real.
       Warm up allocator/env and FD table; setup and process startup are excluded. */
    for (int i = 0; i < 20; ++i)
        assert(dnfast_executor_exec_compact(3, 3, artifacts, (size_t)count, 0) == -1);
    fcntl_calls = dup_calls = exec_calls = 0;
    uint64_t start = now_ns();
    for (int i = 0; i < iterations; ++i)
        assert(dnfast_executor_exec_compact(3, 3, artifacts, (size_t)count, 0) == -1);
    uint64_t elapsed = now_ns() - start;
    assert(exec_calls == (unsigned long)iterations);
    printf("{\"artifacts\":%d,\"iterations\":%d,\"ns_per_handoff\":%.3f,"
           "\"fcntl_per_handoff\":%lu,\"dup3_per_handoff\":%lu}\n",
           count, iterations, (double)elapsed / iterations,
           fcntl_calls / (unsigned long)iterations, dup_calls / (unsigned long)iterations);
}
int main(int argc, char **argv) {
    if (argc == 2 && !strcmp(argv[1], "--test")) tests();
    else if (argc == 3 && !strcmp(argv[1], "--received")) receive(number(argv[2], 1024));
    else if (argc == 4 && !strcmp(argv[1], "--bench")) benchmark(number(argv[2], 1024), number(argv[3], 1000000));
    else { fprintf(stderr, "usage: %s --test | --bench ARTIFACTS ITERATIONS\n", argv[0]); return 2; }
    return 0;
}
