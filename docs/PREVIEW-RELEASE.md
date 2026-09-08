# TinyAgent 0.1.0-preview.2

비공개 테스트용 사전 릴리즈입니다. 저장소와 릴리즈 첨부 파일은 초대한 사용자에게만 제공됩니다.
검증한 v20 APK를 재빌드·재서명하지 않고 배포합니다.
Stock 준비와 앱 내부 무선 Developer 페어링을 추가했습니다.
[첫 연결과 최신 실기기 검증](WIRELESS-DEVELOPER.md)을 참고하세요.

## 설치

1. Releases에서 `TinyAgent-0.1.0-preview.2-arm64.apk`를 내려받습니다.
2. Android 설치 화면에서 설치 또는 업데이트를 승인합니다.
3. TinyAgent에서 **환경 준비하기 → 대화 시작하기**를 누릅니다.
4. 설정의 **공급자**에서 인증을 연결하고 모델을 선택합니다.

ARM64 Android용이며 실기기 검증은 Android 16의 Edge 40와 Nothing A142에서 수행했습니다.
Lyriq1에서 앱 자체 ADB 없이 최초 Fedora 준비를 확인했습니다. 제조사 순정 커널별 검증은 남아 있습니다. Fedora와 OpenCode는 앱 UID로 실행되며,
Root는 Android 관리 기능에만 선택적으로 사용합니다.

패키지: `io.github.gplaider.tinyagent.debug`
APK 내부 버전: `0.1.0-dev`, versionCode `1`.
GitHub 태그는 이 테스트 배포를 구분하는 `v0.1.0-preview.2`입니다.
서명은 기존 설치와 동일한 개발 인증서입니다. 정식 배포 키가 아닙니다.
키 파일은 저장소와 릴리즈에 포함하지 않습니다.

APK SHA256:
`0cfbd92efea5445df2d9ddedd1491f84d7a01151b4a3b48c184248cb4d405f3d`

인증서 SHA256:
`a3ef78ae0bfdfc30307e3448e138eca29adf39d966f89af116bbce151abc1ed2`

## 확인한 동선

- v20: 저장된 무선 페어링으로 재연결 3회, 앱 내부 TLS APK 설치 3회.
- Stock 복귀 후 Developer 요청 거부와 Fedora Git 실행 유지.
- v18: 실제 Android 페어링 창과 TinyAgent 알림 코드 입력, 동적 포트 변경 후 재연결 3회.
- v19: 실제 OpenCode/Fedora 도구에서 Android Developer UID2000·자기 기기 확인.
- v17: Git 누락 수정 후 명령 실행·세션 보존, 세션 터치·뒤로가기 3회와 앱 재시작.

아래는 이전 빌드에서 확인한 범위이며 전체 동선을 v20에서 반복했다는 뜻은 아닙니다.

- 로컬 백엔드 시작·중단 3회, 앱 재실행 자동 복구.
- 실제 작업 프로세스 중단 3회, 화면 꺼짐·앱 전환 후 세션 유지.
- Stock/ADB/Root UID 구분과 권한 불일치·다른 UID 접근 거부.
- 에이전트 Android 조사, Fedora 테스트 실패 → 파일 수정 → 테스트 성공.
- v14 새 세션·저장 세션·Android 뒤로가기 각 3회, 설정·입력창 회귀.
- 시스템 라이트·다크 연동, 기존 데이터 보존 업데이트.
- 이전 v12는 폰 Fedora 자체 빌드 후 동일 개발 서명으로 업데이트까지 확인.
  이번 v20 첨부 APK는 호스트 빌드입니다.

## 사용자가 이어서 확인할 항목

개인 OpenAI OAuth, 순정폰, 네트워크 전환, 장시간 대기·자원 사용, 한글 조합·긴 대화,
전체 동선 연속 3회는 미완료입니다. Android 임의 명령·Shizuku·SAF 작업공간 통합은 미구현입니다.
무선 페어링의 알림 거부/분할 화면·잘못된 코드 처리 동선은 별도 실기기 검증이 남아 있습니다.
모든 provider와 privileged ROM 설치 성공을 보장하지 않습니다.

문제 신고에는 앱 버전, 기기/Android 버전, 재현 순서, 오류 문구를 남겨 주세요.
API 키·OAuth 토큰·서명 키는 첨부하지 마세요.

## 소스와 의존성

이 저장소는 개발 소스 `9225ae95e968b821e81cc978715e37252c12cd78`의 스냅샷입니다.
원시 기기 로그·대화 이력은 제외했고, 테스트 스크립트의 기기 주소는 예시 값입니다.
실제 배포 APK의 앱 소스·하네스·업스트림 GUI 패치를 포함합니다.

OpenCode v1.18.29는 MIT, Dadb는 Apache-2.0이며,
PRoot/talloc/libandroid-shmem의 개별 라이선스는 `app/src/main/assets/licenses/`에 있습니다.
첨부 `TinyAgent-native-sources.zip`에는 검증한 네이티브 소스와 고정 Termux 레시피를 포함합니다.
이 네이티브 번들은 preview.1 첨부 파일을 그대로 사용합니다.
무선 연결은 `third_party/libadb/`에 고정 소스·라이선스를 포함한 LibADB Android BC와
BouncyCastle 1.84를 사용합니다. LibADB의 이중 라이선스 파일에는 Apache-2.0 선택을 적용합니다.
완전한 전이 의존성 재빌드·라이선스 검토는 미완료입니다.
TinyAgent 자체 소스의 별도 오픈소스 라이선스는 아직 지정하지 않았습니다.

## 빌드

JDK 17, Android SDK 36, Python 3.11+, Node.js, Bun 1.3.14, Git, gpgv가 필요합니다.
실행 전 Windows 전용 스크립트의 SDK/Python 경로를 자신의 환경으로 바꾸세요.

```text
python scripts/collect_upstream.py --output artifacts
python scripts/prepare-fedora.py artifacts
python scripts/stage-runtime-assets.py artifacts
python scripts/stage-proot.py
python scripts/collect-proot-sources.py
git clone --branch v1.18.29 https://github.com/anomalyco/opencode.git ../opencode
git -C ../opencode apply ../TinyAgent/patches/opencode-mobile-ux.patch
```

`../opencode`에서 `bun install --frozen-lockfile --filter @opencode-ai/app --ignore-scripts`,
`packages/app`에서 `bun run build`를 실행한 뒤 TinyAgent 폴더로 돌아옵니다.

```text
python scripts/stage-web-ui.py ../opencode
gradlew.bat --no-daemon :app:assembleDebug :app:lintDebug
python scripts/check-packaged-runtime.py
```

직접 빌드하면 자신의 개발 키로 서명됩니다. 배포 APK와 같은 서명이 필요하면 기존 키를
안전하게 별도 관리해야 합니다. 폰 빌드는 `scripts/self-build-complete-fedora.sh`를 참고하세요.
