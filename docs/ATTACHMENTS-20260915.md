# 파일 첨부 로컬 구현·검증 — 2026-09-15

작업 위치: `C:/Users/Administrator/orca/workspaces/tinyagent-audit-85c4cef/codex-prompt-rework`.
기준 커밋: `85c4cef`, 브랜치: `GPLaider/codex-prompt-rework`.

`D:/TinyAgent-work/tinyagent-audit-85c4cef`의 9월 14일 첨부·탐색 구현만 가져왔습니다.
원본 작업 트리에는 쓰지 않았습니다. 이 브랜치에서 모델 지원 안내,
대화 이동 시 콜백 취소, 선택기 출처 일치, 작업 폴더 단일 선택 제한을 보완했습니다.
사용법과 경계는 [WORKSPACE-FILES.md](WORKSPACE-FILES.md)에 있습니다.

## 이번에 직접 확인한 결과

| 검사 | 결과 |
|---|---|
| `check-attachment-results.py` | 생산 결과 처리 메서드 22개 통과 |
| `check-workspace-listing.py` | 실제 파일·심볼릭 링크 13개 통과 |
| `:app:assembleDebug :app:lintDebug --offline --no-daemon` | 성공, 최종 실행 48개 task 중 18개 실행·30개 최신 |
| lint XML | 오류 0개, 경고 58개. API annotation·문자열 국제화 등 경고 잔존 |
| `check-packaged-runtime.py` | 통과: 첨부 CSS 원본 바이트, GUI 952개 해시, 런타임 2개, native·dnfast·harness·license·bootstrap 검증 |
| `apksigner verify --verbose` | APK Signature Scheme v2 검증 통과 |
| `zipalign -c -P 16 4` | 종료 코드 0 |
| `git diff --check` | 통과 |

## APK

- 경로: `app/build/outputs/apk/debug/app-debug.apk`
- 패키지: `io.github.gplaider.tinyagent.debug`
- 버전: 기존 `0.0.1-alpha.2-rc.1` / code 6 유지
- ABI: `arm64-v8a`, min SDK 30, target SDK 36
- 크기: `149003554` bytes
- SHA-256: `9e1513668d94b1fa428c26ec72eb312d64d4f3cfd45333346a63397a8db93e08`

개발용 debug APK이며 생산 패키지의 업데이트 APK가 아닙니다.

이 worktree에 빠져 있던 GUI·런타임 자산은 로컬 보관 후보
`D:/TinyAgent-work/release-artifacts/TinyAgent-0.0.1-alpha.2-rc.1-android-arm64.apk`에서
재사용했습니다. GUI는 고정 upstream `16747470f976aca3d362ad730bcd3fe82ecc2c9a`와
manifest의 952개 파일 해시를 확인했습니다. 런타임·PRoot는 이 브랜치의 고정 해시를
확인했습니다. dnfast overlay는 이 브랜치의 33개 고정 파일을 검증해 staging했고,
Android launcher·debug probe는 현재 C 소스와 설치된 고정 NDK로 다시 빌드했습니다.
GUI 자체는 이번에 소스에서 재빌드하지 않았습니다.

## 검증 한계

이번 APK는 기기에 설치하지 않았습니다. 실제 선택기 표시, 화면 회전·OS 프로세스 종료,
대용량 파일, 모델의 실제 첨부 읽기, 외부 공유 수신은 미검증입니다.
안내는 모델에 따라 이미지·PDF 지원이 다름을 설명하며 선택된 모델의 자동 판정은 아닙니다.
Linux 전용 FD 회귀 검사는 이번에 실행하지 않았고 기존 파일 열기 구현은 유지했습니다.
다른 작업 트리의 Spacewar 검증 기록을 이번 APK의 실기기 결과로 취급하지 않습니다.

미러 비교·dnfast/dnf5 실기기 측정, 런타임 이전, 파일 이동·이름 변경·삭제·가져오기,
배포 작업은 이번 첨부 구현에 포함하지 않습니다.
