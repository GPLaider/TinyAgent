# TinyAgent 0.1.0-preview.1

비공개 테스트용 사전 릴리즈입니다. 저장소와 릴리즈 첨부 파일은 초대한 사용자에게만 제공됩니다.
검증한 v14 APK를 재빌드·재서명하지 않고 배포합니다.

## 설치

1. Releases에서 `TinyAgent-0.1.0-preview.1-arm64.apk`를 내려받습니다.
2. Android 설치 화면에서 설치 또는 업데이트를 승인합니다.
3. TinyAgent에서 **환경 준비하기 → 대화 시작하기**를 누릅니다.
4. 설정의 **공급자**에서 인증을 연결하고 모델을 선택합니다.

ARM64 Android용이며 실기기 검증은 Android 16의 Edge 40와 Nothing A142에서 수행했습니다.
순정폰 최초 설치는 아직 확인하지 않았습니다. Fedora와 OpenCode는 앱 UID로 실행되며,
Root는 Android 관리 기능에만 선택적으로 사용합니다.

패키지: `io.github.gplaider.tinyagent.debug`
APK 내부 버전: `0.1.0-dev`, versionCode `1`.
GitHub 태그는 이 테스트 배포를 구분하는 `v0.1.0-preview.1`입니다.
서명은 기존 설치와 동일한 개발 인증서입니다. 정식 배포 키가 아닙니다.
키 파일은 저장소와 릴리즈에 포함하지 않습니다.

APK SHA256:
`b59bd21ffbab819f3d6b88e545b0327bf1d6a43443fe28659e10b77d8087377a`

인증서 SHA256:
`a3ef78ae0bfdfc30307e3448e138eca29adf39d966f89af116bbce151abc1ed2`

## 확인한 동선

- 로컬 백엔드 시작·중단 3회, 앱 재실행 자동 복구.
- 실제 작업 프로세스 중단 3회, 화면 꺼짐·앱 전환 후 세션 유지.
- Stock/ADB/Root UID 구분과 권한 불일치·다른 UID 접근 거부.
- 에이전트 Android 조사, Fedora 테스트 실패 → 파일 수정 → 테스트 성공.
- v14 새 세션·저장 세션·Android 뒤로가기 각 3회, 설정·입력창 회귀.
- 시스템 라이트·다크 연동, 기존 데이터 보존 업데이트.
- 이전 v12는 폰 Fedora 자체 빌드 후 동일 개발 서명으로 업데이트까지 확인.
  이번 v14 첨부 APK는 호스트 빌드입니다.

## 사용자가 이어서 확인할 항목

개인 OpenAI OAuth, 순정폰, 네트워크 전환, 장시간 대기·자원 사용, 한글 조합·긴 대화,
전체 동선 연속 3회는 미완료입니다. Android 임의 명령·무선 페어링·Shizuku는 미구현입니다.
모든 provider와 privileged ROM 설치 성공을 보장하지 않습니다.

문제 신고에는 앱 버전, 기기/Android 버전, 재현 순서, 오류 문구를 남겨 주세요.
API 키·OAuth 토큰·서명 키는 첨부하지 마세요.

## 소스와 의존성

이 저장소는 개발 소스 `65af6e9008e1fb8244772dd629f74aebfb580911`의 스냅샷입니다.
원시 기기 로그·대화 이력은 제외했고, 테스트 스크립트의 기기 주소는 예시 값입니다.
실제 배포 APK의 앱 소스·하네스·업스트림 GUI 패치를 포함합니다.

OpenCode v1.18.29는 MIT, Dadb는 Apache-2.0이며,
PRoot/talloc/libandroid-shmem의 개별 라이선스는 `app/src/main/assets/licenses/`에 있습니다.
첨부 `TinyAgent-native-sources.zip`에는 검증한 네이티브 소스와 고정 Termux 레시피를 포함합니다.
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
