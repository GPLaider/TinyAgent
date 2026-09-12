<p align="center">
  <img src="app/src/main/res/drawable-nodpi/tinyagent_robot.png" width="180" alt="TinyAgent robot">
</p>

<h1 align="center">TinyAgent</h1>

<p align="center">
  <strong>Android 폰 안에서 Fedora와 OpenCode를 실행하는 온디바이스 개발 에이전트.</strong><br>
  Your phone is the workstation.
</p>

<p align="center">
  <a href="https://github.com/GPLaider/TinyAgent/releases/tag/v0.0.1-alpha.1"><img alt="Release" src="https://img.shields.io/github/v/release/GPLaider/TinyAgent?include_prereleases&sort=semver"></a>
  <a href="LICENSE"><img alt="GPL-3.0-or-later" src="https://img.shields.io/badge/license-GPL--3.0--or--later-blue"></a>
  <img alt="Android 11+" src="https://img.shields.io/badge/Android-11%2B-3DDC84?logo=android&logoColor=white">
  <img alt="ARM64" src="https://img.shields.io/badge/ABI-arm64--v8a-0B7285">
</p>

<p align="center">
  <a href="https://github.com/GPLaider/TinyAgent/releases/tag/v0.0.1-alpha.1">다운로드</a> ·
  <a href="#빠른-시작">빠른 시작</a> ·
  <a href="docs/RELEASE-0.0.1-ALPHA.1.md">검증 기록</a> ·
  <a href="SECURITY.md">보안 제보</a> ·
  <a href="CONTRIBUTING.md">기여</a>
</p>

> [!WARNING]
> 현재 버전은 `0.0.1-alpha.1`입니다. 중요한 데이터의 유일한 작업 환경으로 사용하지
> 말고, 앱 업데이트 전 `/workspace`를 별도로 백업하세요. 지원 범위와 알려진 한계는
> [현재 상태](docs/STATUS.md)에 기록합니다.

## TinyAgent란?

TinyAgent는 ARM64 Android 기기 안에 Fedora 44 사용자 공간과 OpenCode를 준비하고,
Android 앱의 모바일 UI에서 실제 셸·파일·개발 도구를 사용하는 에이전트입니다.
Stock 모드는 ADB나 root 없이 앱 UID로 동작하며, 더 높은 Android shell 권한이 필요한
작업만 사용자가 명시적으로 연결한 LADB Developer 모드로 분리합니다.

- 폰 내부 `/workspace`에서 소스 편집, 빌드 및 에이전트 작업
- PRoot 기반 Fedora 44 ARM64 환경과 버전 고정 OpenCode 런타임
- OpenCode 공급자·모델 선택과 실제 도구 호출
- Android Wireless debugging을 이용한 자기 기기 LADB shell
- APK streaming install, 장시간 Android job 관찰·복구·취소
- 실행 결과와 릴리스 입력을 증거·해시로 검증하는 배포 방식

TinyAgent는 기기를 자동으로 root 처리하거나 `adbd`를 임의로 켜지 않습니다. 모델
공급자 사용과 최초 환경 준비에는 네트워크가 필요할 수 있습니다.

## 실제 production 동작

다음 화면은 GPLaider 생산키로 서명된 정확한 `0.0.1-alpha.1` APK를 clean 설치한 뒤,
기본 모델이 Fedora 안에서 bash를 한 번 호출해 `/workspace`, `aarch64`, Fedora 44를
반환한 실기기 결과입니다.

<p align="center">
  <img src="https://github.com/GPLaider/TinyAgent/releases/download/v0.0.1-alpha.1/lyriq1-alpha1-production-model-tool.png" width="460" alt="TinyAgent production model and bash tool validation on Android">
</p>

## 실행 구조

```mermaid
flowchart LR
    UI[Android UI] <--> OC[OpenCode]
    UI --> PR[PRoot]
    PR --> F[Fedora 44 ARM64]
    OC --> F
    F --> WS[/workspace]
    UI --> LB[LADB Developer bridge]
    LB --> AD[Android Wireless debugging<br/>UID 2000 shell]
```

| 모드 | 현재 상태 | 권한과 조건 |
|---|---|---|
| **Stock** | Alpha 1 실기기 통과 | 일반 앱 UID, ADB·root 불필요 |
| **LADB / Developer** | 같은 Wi-Fi 실기기 통과 | Android Wireless debugging 페어링, UID 2000 |
| **Root** | 구현 포함 | 이미 root된 자기 기기에서 사용자가 명시적으로 허용 |
| **RADB** | 미구현 | Tailscale 기반 셀룰러 transport는 후속 목표 |

LADB는 같은 Wi-Fi와 Wireless debugging에 의존합니다. Wi-Fi 영역을 벗어나면 Stock
기능은 계속 사용할 수 있지만 Developer ADB 연결은 유지되지 않습니다.

## 빠른 시작

### 1. APK 받기

[TinyAgent `0.0.1-alpha.1` Release](https://github.com/GPLaider/TinyAgent/releases/tag/v0.0.1-alpha.1)에서
`TinyAgent-0.0.1-alpha.1-android-arm64.apk`를 받습니다.

요구사항:

- Android 11 이상, API 30–36
- ARM64 (`arm64-v8a`)
- 최초 환경 준비와 모델 공급자 연결을 위한 네트워크
- 약 145 MB APK와 Fedora 작업공간을 위한 여유 저장공간

APK SHA-256:

```text
013f05727575620cb04aa9c3aec00098bf137d8652dd0d77ae6e3db3a04e1462
```

GPLaider 생산 인증서 SHA-256:

```text
c34483dc3b7228cede2e128ccd66cab193e78804686a58ea25ba318568afc9d2
```

다운로드한 APK는 Release의 `SHA256SUMS.txt`로 확인할 수 있습니다.

```powershell
Get-FileHash -Algorithm SHA256 .\TinyAgent-0.0.1-alpha.1-android-arm64.apk
```

```sh
sha256sum TinyAgent-0.0.1-alpha.1-android-arm64.apk
```

### 2. 환경 준비

1. APK를 설치하고 TinyAgent를 엽니다.
2. **환경 준비하기**를 눌러 Fedora와 로컬 OpenCode 환경을 준비합니다.
3. 준비 완료 후 **대화 시작하기**를 누릅니다.
4. OpenCode 설정에서 사용할 공급자와 모델을 연결합니다.
5. 작업 파일은 `/workspace`, Android와 교환할 파일은 `/shared`에 둡니다.

개발 도구가 더 필요하면 에이전트가 Fedora 안에서 다음 버전 고정 bootstrap을 사용할
수 있습니다.

```sh
/usr/bin/bash /root/.tinyagent/bootstrap/prepare-development.sh
```

### 3. Developer 연결은 필요할 때만

Android shell 권한이 필요한 경우 **Developer 연결 설정 → 페어링 알림 켜기**를
사용합니다. Android 무선 디버깅 페어링 창을 유지한 채 알림에 6자리 코드를 입력하면
TinyAgent가 자기 기기의 포트를 찾고 연결합니다. 일반 에이전트 사용에는 필요하지
않습니다. 자세한 경계는 [무선 Developer 문서](docs/WIRELESS-DEVELOPER.md)를
참조하세요.

## Alpha 1에서 확인한 것

- clean release build와 lint 55개 작업 통과
- OpenCode 관련 테스트 108 pass, 17 skip, 0 fail
- APK Signature Scheme v2, RSA-4096 생산 서명 검증
- 패키지 `io.github.gplaider.tinyagent`, versionCode 5, ARM64 확인
- 하네스, PRoot, dnfast, 10개 bootstrap, GUI 952개 파일과 런타임 2개 검증
- 정확한 production APK의 clean 설치, cold start와 첫 Fedora 준비
- 실제 모델 → bash 도구 → Fedora 결과 반환
- LADB UID 2000 shell과 fixture APK streaming install
- 관찰 연결 중단 뒤 같은 job UUID 복구 및 명시적 process-group 취소
- 468개 파일 source ZIP과 APK 해시 결합 검증

상세한 재현 근거와 한계는 [Alpha 1 릴리스 기록](docs/RELEASE-0.0.1-ALPHA.1.md)에
있습니다.

## 아직 하지 않은 것

- RADB/Tailscale 셀룰러 transport
- 모든 유료 공급자 인증·OAuth 갱신 조합 검증
- production 장시간 작업과 반복 복구 스트레스 테스트
- 다음 버전의 동일 서명 데이터 보존 업데이트 검증
- 여러 제조사·ROM·Android 버전의 반복 release journey
- Windows 사용자 프로필과 독립된 off-host 생산키 재난 복구

이 목록은 숨은 성공 주장 대신 검증 경계를 분명히 하기 위한 것입니다.

## 소스 빌드

기본 Android 빌드에는 JDK 17, Android SDK Platform 36과 대응 build tools가
필요합니다. production 서명키는 저장소에 포함되지 않으며 일반 기여자는 debug APK를
빌드하면 됩니다.

```powershell
.\gradlew.bat :app:assembleDebug
.\gradlew.bat :app:testDebugUnitTest
```

Unix 계열 셸에서는 `./gradlew`을 사용합니다. release APK의 런타임·라이선스 입력
검증 방법은 [배포 서명 문서](docs/RELEASE-SIGNING.md)를 참조하세요.

## 문서

- [현재 구현 및 남은 위험](docs/STATUS.md)
- [Alpha 1 릴리스와 검증 범위](docs/RELEASE-0.0.1-ALPHA.1.md)
- [지원 기능](docs/CAPABILITIES.md)
- [무선 Developer 설정](docs/WIRELESS-DEVELOPER.md)
- [폰 내부 자체 빌드](docs/SELF-BUILD.md)
- [업스트림·제3자 라이선스](docs/UPSTREAM.md)
- [Android 실행 통합](docs/ANDROID-EXECUTION-INTEGRATION.md)

## 기여와 보안

작은 수정과 재현 가능한 증거를 선호합니다. 작업 방법은 [CONTRIBUTING.md](CONTRIBUTING.md),
취약점 제보는 [SECURITY.md](SECURITY.md)를 확인하세요. API 키, OAuth 토큰, production
서명키와 개인 작업 로그를 issue나 commit에 올리지 마세요.

## 라이선스

별도 표기가 없는 TinyAgent 원본 코드는
[GNU General Public License v3.0 or later](LICENSE), 즉 `GPL-3.0-or-later`로
배포합니다. 기여 코드는 제출과 함께 같은 라이선스로 제공됩니다.

OpenCode, PRoot, Dadb, Fedora 패키지와 기타 제3자 구성요소는 각자의 라이선스를
유지합니다. 배포 APK에 포함된 사본과 고지는
[`app/src/main/assets/licenses`](app/src/main/assets/licenses)에서 확인할 수 있습니다.
