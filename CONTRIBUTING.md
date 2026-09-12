# Contributing to TinyAgent

TinyAgent에 관심을 가져주셔서 감사합니다. 이 프로젝트는 작은 변경, 실제 원인 수정,
재현 가능한 검증과 정확한 한계 기록을 선호합니다.

## 시작하기

1. 큰 기능이나 아키텍처 변경은 먼저 issue에서 범위와 검증 방법을 합의합니다.
2. 수정할 실행 경로와 기존 helper를 먼저 찾습니다.
3. 관련 없는 정리나 대규모 포맷 변경을 섞지 않습니다.
4. 실패 로그를 숨기지 말고 비밀만 제거한 최소 증거를 남깁니다.

## 개발 환경

- JDK 17
- Android SDK Platform 36 및 대응 build tools
- Python 3 — 패키지·source snapshot 검증
- ARM64 Android 11 이상 기기 — 실기기 기능을 변경하는 경우

Windows 기본 빌드:

```powershell
.\gradlew.bat :app:assembleDebug
.\gradlew.bat :app:testDebugUnitTest
```

Unix 계열 셸에서는 `./gradlew`을 사용합니다. 변경 범위에 맞는 기존 검사를 실행하고,
문서만 바꿨더라도 링크와 명령이 실제 파일·task를 가리키는지 확인하세요.

## Pull request 원칙

- 한 PR에는 한 가지 목적만 둡니다.
- 증상별 우회보다 공통 실행 경로의 원인을 수정합니다.
- 새 dependency와 abstraction은 기존 코드·표준 기능으로 해결할 수 없을 때만 추가합니다.
- Android 버전, ROM, 기기, 실행 UID와 사용한 APK 해시를 검증 기록에 포함합니다.
- “통과”는 실행한 명령과 관찰한 결과가 있을 때만 사용합니다.
- 서명키, `release.properties`, `.env`, API key, OAuth token과 개인 작업 로그를 commit하지 않습니다.

production signer는 maintainer 전용입니다. 기여 검증에는 debug APK로 충분하며, 공식
release로 오인될 수 있는 비공식 서명 산출물을 배포하지 마세요.

## 라이선스

별도 합의나 표기가 없는 기여는 제출과 함께
[GPL-3.0-or-later](LICENSE)로 제공됩니다. 가져온 제3자 코드는 원본 라이선스·출처와
필요한 NOTICE를 함께 보존해야 합니다.

보안 취약점은 PR이나 공개 issue 대신 [SECURITY.md](SECURITY.md)의 비공개 제보
경로를 사용하세요.
