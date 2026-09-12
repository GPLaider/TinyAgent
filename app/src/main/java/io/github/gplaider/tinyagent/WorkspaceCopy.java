package io.github.gplaider.tinyagent;

import java.io.*;

/** A growing source must not extend an export indefinitely or hide truncation. */
final class WorkspaceCopy {
    static long copy(InputStream input, OutputStream output, long expectedSize) throws IOException {
        if (expectedSize < 0) throw new IOException("원본 파일 크기를 확인할 수 없습니다.");
        byte[] buffer = new byte[65536];
        long remaining = expectedSize;
        while (remaining > 0) {
            interrupted();
            int count = input.read(buffer, 0, (int)Math.min(buffer.length, remaining));
            if (count < 0) throw new IOException("저장 중 원본 파일이 작아졌습니다. 변경이 끝난 뒤 다시 저장하세요.");
            if (count == 0) throw new IOException("원본 파일 읽기가 진행되지 않습니다.");
            output.write(buffer, 0, count);
            remaining -= count;
        }
        interrupted();
        if (input.read() != -1)
            throw new IOException("저장 중 원본 파일이 커졌습니다. 변경이 끝난 뒤 다시 저장하세요.");
        return expectedSize;
    }

    private static void interrupted() throws InterruptedIOException {
        if (Thread.currentThread().isInterrupted()) throw new InterruptedIOException("파일 저장이 중단되었습니다.");
    }
}
