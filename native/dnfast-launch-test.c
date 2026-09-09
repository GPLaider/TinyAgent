#define main launcher_main
#include "dnfast-launch.c"
#undef main
#include <assert.h>
#include <sys/wait.h>

static int root;
static void bad_id(void) { char id[65]; root_id(root, id); }
static void bad_link(void) { (void)child_directory(root, "link"); }
static void bad_mode(void) { private_directory(root); }
static void rejected(void (*operation)(void)) {
    pid_t pid = fork(); assert(pid >= 0);
    if (!pid) { operation(); _exit(0); }
    int status; assert(waitpid(pid, &status, 0) == pid);
    assert(WIFEXITED(status) && WEXITSTATUS(status) != 0);
}
int main(void) {
    char path[] = "/tmp/tinyagent-launch-test-XXXXXX";
    assert(mkdtemp(path)); root = open_root(path);
    assert(mkdirat(root, "traverse", 0700) == 0);
    int traverse = openat(root, "traverse", O_RDONLY | O_DIRECTORY);
    assert(traverse >= 0 && mkdirat(traverse, "leaf", 0700) == 0);
    assert(fchmod(traverse, 0100) == 0);
    char leaf[4096]; snprintf(leaf, sizeof(leaf), "%s/traverse/leaf", path);
    int visited = open_root(leaf); assert(visited >= 0); close(visited);
    assert(fchmod(traverse, 0700) == 0); close(traverse);
    assert(flock(root, LOCK_EX | LOCK_NB) == 0);
    int competitor = open_root(path);
    assert(flock(competitor, LOCK_EX | LOCK_NB) == -1 && errno == EWOULDBLOCK);
    close(competitor);
    char first[65], second[65]; root_id(root, first); root_id(root, second);
    assert(!strcmp(first, second) && hex64(first));
    int state = state_directory(root, first); close(state);
    int memory = sealed_context("{\"schema_version\":1}", 20);
    assert(fcntl(memory, F_GET_SEALS) == 47);
    assert(pwrite(memory, "x", 1, 0) == -1 && errno == EPERM);
    assert(ftruncate(memory, 0) == -1 && errno == EPERM); close(memory);
    assert(symlinkat("/tmp", root, "link") == 0); rejected(bad_link);
    assert(fchmod(root, 0777) == 0); rejected(bad_mode); assert(fchmod(root, 0700) == 0);
    int id = openat(root, ".tinyagent-root-id", O_WRONLY | O_TRUNC); assert(id >= 0); close(id);
    rejected(bad_id); /* Interrupted/corrupt identity is never silently replaced. */
    close(root);
    printf("PASS root_lock stable_id nofollow mode corrupt_id nonexec_immutable_context; fixture=%s\n", path);
}
