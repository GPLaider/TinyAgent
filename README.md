# TinyAgent

폰 내부 Fedora와 OpenCode를 사용하는 Android 개발 에이전트입니다.
현재는 실기기 통합 검증 중인 개발 빌드이며 정식 릴리즈가 아닙니다.
Preview 4 후보는 dnfast 결과 판정 수정과 ARM 실기기 빌드 검증을 반영합니다.
[현재 후보 검증 상태](docs/PRERELEASE-4-VALIDATION.md)를 먼저 확인하세요.
[무선 Developer 설정·검증 범위](docs/WIRELESS-DEVELOPER.md)와
[Stock 준비 수정](docs/STOCK-COMPATIBILITY.md)을 참고하세요.

## 시작

1. APK 설치 후 **환경 준비하기**를 누릅니다. Fedora와 로컬 백엔드는 앱 권한으로 실행됩니다.
2. 준비가 끝나면 **대화 시작하기**를 누릅니다.
3. 설정의 **공급자**에서 사용할 인증 방법을 연결하고 **모델**을 선택합니다.
   big-pickle과 OpenAI OAuth의 GPT-5.6 Luna 응답·도구 실행은 이전 실기기 후보에서 확인했습니다.
   모든 공급자·인증 갱신 방식의 검증을 뜻하지 않습니다.
4. 개발 작업에 필요한 도구는 에이전트가 다음 명령으로 준비할 수 있습니다.

```sh
/usr/bin/bash /root/.tinyagent/bootstrap/prepare-development.sh
```

이 명령은 네트워크가 필요합니다. Git·Java 17·Node와 ARM64 Android SDK를
준비하며 `development_prepare_exit=0`까지 확인합니다.
작업 파일은 `/workspace`, Android와 교환할 파일은 `/shared`에 둡니다.

Stock에서는 ADB가 필요하지 않습니다. Android shell 권한이 필요하면
**Developer 연결 설정 → 페어링 알림 켜기**를 사용하세요. Android 무선 디버깅의
페어링 창을 유지한 채 알림에 6자리 코드를 입력하면 포트를 자동으로 찾습니다.
기존 PC ADB나 Tailscale 연결은 필요하지 않습니다. 연결 실패 후에도 Fedora는 사용할 수 있습니다.

## APK 설치 경로

| 선택 | 실제 경로 | 조건 |
|---|---|---|
| Stock | Android PackageInstaller 승인 화면 | 사용자가 이 앱의 설치 요청을 허용하고 설치 승인 |
| Developer | 자기 기기 ADB streaming install | 인증된 ADB 연결, 실제 UID 2000 |
| Root | 자기 기기 root ADB PackageManager | Root 실행 허용, 자기 기기 검증, 실제 UID 0 |
| ROM 통합 | 직접 PackageInstaller | ROM에서 실제 INSTALL_PACKAGES 권한 부여 |

일반 APK 설치만으로 ROM 권한이 생기지는 않습니다. 서명이 다른 APK는
기존 앱의 업데이트가 될 수 없습니다. 자동 삭제나 권한 승격은 하지 않습니다.

## 중단·복구

작업 환경의 **진단 정보 → 로컬 백엔드 중단**으로 Fedora 프로세스를 중단합니다.
명시적으로 중단했다면 환경 준비하기로 다시 시작합니다. 실행 중이던 환경은
앱 재실행 시 복원합니다. 재연결 후에는 실제 작업 결과와 세션 상태를 먼저
확인하고, 완료 여부가 불명확한 쓰기 작업을 바로 반복하지 마세요.

로그는 앱 내부 `files/linux/backend.log`, 하네스는 Fedora의
`/root/.tinyagent/`에 있습니다. 진단에 API 키·OAuth 토큰을 포함하지 마세요.

## 소스·검증

- [현재 지원 범위](docs/CAPABILITIES.md)
- [빌드 및 폰 내부 자체 빌드 절차](docs/SELF-BUILD.md)
- [최신 통합 검증 결과](docs/INTEGRATION-V10-20260908.md)
- [모바일 UI 검증](docs/MOBILE-UX-20260908.md)
- [업스트림과 라이선스](docs/UPSTREAM.md)
- [남은 릴리즈 기준](docs/STATUS.md)
