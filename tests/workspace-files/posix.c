#include <jni.h>
#include <errno.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/stat.h>
#include <limits.h>

static int number(JNIEnv *env, jobject fd) {
    jclass cls = (*env)->FindClass(env, "java/io/FileDescriptor");
    return (*env)->GetIntField(env, fd, (*env)->GetFieldID(env, cls, "fd", "I"));
}
static void failed(JNIEnv *env, const char *op) {
    int code = errno;
    jclass cls = (*env)->FindClass(env, "android/system/ErrnoException");
    jmethodID ctor = (*env)->GetMethodID(env, cls, "<init>", "(Ljava/lang/String;I)V");
    (*env)->Throw(env, (*env)->NewObject(env, cls, ctor, (*env)->NewStringUTF(env, op), code));
}
static jobject descriptor(JNIEnv *env, int raw) {
    if (raw < 0) { failed(env, "fd"); return NULL; }
    jclass cls = (*env)->FindClass(env, "java/io/FileDescriptor");
    jobject fd = (*env)->NewObject(env, cls, (*env)->GetMethodID(env, cls, "<init>", "()V"));
    (*env)->SetIntField(env, fd, (*env)->GetFieldID(env, cls, "fd", "I"), raw);
    return fd;
}
JNIEXPORT jobject JNICALL Java_android_system_Os_openNative(JNIEnv *env, jclass cls, jstring path, jint flags, jint mode) {
    const char *text = (*env)->GetStringUTFChars(env, path, NULL);
    int raw = open(text, flags, mode);
    (*env)->ReleaseStringUTFChars(env, path, text);
    return descriptor(env, raw);
}
JNIEXPORT jint JNICALL Java_android_system_Os_number(JNIEnv *env, jclass cls, jobject fd) { return number(env, fd); }
JNIEXPORT jlong JNICALL Java_android_system_Os_size(JNIEnv *env, jclass cls, jobject fd) {
    struct stat info;
    if (fstat(number(env, fd), &info) < 0) { failed(env, "fstat"); return -1; }
    return info.st_size;
}
JNIEXPORT jobject JNICALL Java_android_system_Os_dup(JNIEnv *env, jclass cls, jobject fd) { return descriptor(env, dup(number(env, fd))); }
JNIEXPORT jint JNICALL Java_android_system_Os_fcntlNative(JNIEnv *env, jclass cls, jobject fd, jint cmd, jint arg) {
    int result = fcntl(number(env, fd), cmd, arg);
    if (result < 0) failed(env, "fcntl");
    return result;
}
JNIEXPORT void JNICALL Java_android_system_Os_close(JNIEnv *env, jclass cls, jobject fd) {
    int raw = number(env, fd);
    jclass type = (*env)->FindClass(env, "java/io/FileDescriptor");
    (*env)->SetIntField(env, fd, (*env)->GetFieldID(env, type, "fd", "I"), -1);
    if (close(raw) < 0) failed(env, "close");
}
JNIEXPORT jint JNICALL Java_android_system_Os_statNative(JNIEnv *env, jclass cls, jobject fd) {
    struct stat info;
    if (fstat(number(env, fd), &info) < 0) { failed(env, "fstat"); return 0; }
    return info.st_mode;
}
JNIEXPORT jstring JNICALL Java_android_system_Os_readlinkNative(JNIEnv *env, jclass cls, jstring path) {
    const char *text = (*env)->GetStringUTFChars(env, path, NULL);
    char target[PATH_MAX+1];
    ssize_t size = readlink(text, target, PATH_MAX);
    (*env)->ReleaseStringUTFChars(env, path, text);
    if (size < 0) { failed(env, "readlink"); return NULL; }
    target[size] = 0;
    return (*env)->NewStringUTF(env, target);
}
