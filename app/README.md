# TinyAgent Android shell — 0.1.0-dev (code 1)

현재는 **실제 self ADB 연결을 확인하고 별도로 준비된 로컬 OpenCode를 여는 개발용 앱 소스**다.
APK 빌드·설치, 실기기 self root-ADB, 별도 Fedora 진단 환경의 로컬 OpenCode GUI 연결까지 확인했다. Provider 응답·작업 완주·자동 설치는 미완료이며 정식 릴리즈가 아니다.

## 구현 범위

- Java 17, AGP 8.13.2, Gradle 8.13, compile/target SDK 36, min SDK 30.
- 기본 패키지 `io.github.gplaider.tinyagent`, 개발 설치는 `.debug` 접미사를 쓴다. Kotlin/Compose 플러그인 없는 native Android Views.
- 앱 전용 RSA 2048 ADB 키를 `no_backup/adb-identity`에 생성한다. 개인/공개 키는 모드 `0600`, 디렉터리는 `0700`; Android 백업을 끈다. 키쌍 생성은 임시 디렉터리 후 같은 파일시스템의 atomic rename으로 게시한다. 손상된 기존 키를 자동 교체하지 않는다.
- Dadb `dev.mobile:dadb:1.2.10`으로 loopback과 이 폰에 할당된 IPv4 주소를 확인한다. 외부 기기는 검색하지 않는다. 포트는 1~65535, 기본값 5555. Edge 40의 Tailscale 주소에만 바인딩된 adbd로 실기기 검증했다.
- 고정 명령 `pwd`, `getprop ro.serialno`, `getprop ro.product.device`, `id`의 출력·종료 코드를 표시한다. 앱 쪽 `Build.DEVICE`와 대상 device가 맞아야 한다.
- `Unrestricted root 연결 허용`은 기본 꺼짐. 사용자가 켠 경우 UID 0에 더해 앱 비공개 nonce 파일을 root ADB로 읽어 비교한다. nonce·개인 키를 로그/UI에 출력하지 않는다. 다른 Android에 연결한 loopback 프록시를 자기 기기라고 오인하지 않게 한다.
- TCP 연결 거부·ADB 승인 필요·UID 불일치·잘못된 대상·진단 중단에 오류/재시도 동선을 제공한다. 기기의 adbd를 자동으로 켜거나 root로 재시작하지 않는다.
- 자기 기기 root 확인 후 `http://127.0.0.1:4096/global/health`를 별도로 확인한다. `healthy: true`와 문자열 `version`을 요구한다. HTTP 401은 인증 필요로 표시하고 WebView의 native HTTP 인증 창을 연다. 백엔드 미설치/응답 실패를 성공 처리하지 않는다.
- WebView의 내부 URL은 `http://127.0.0.1:4096`만 허용한다. 외부 HTTP(S) 탐색은 시스템 브라우저로 보낸다. `file:`/`content:` 접근과 native JavaScript bridge는 없다. JavaScript·DOM storage는 켜고 제3자 쿠키는 끈다.
- 시스템 bar/IME inset을 반영한다. 뒤로가기는 키보드 → WebView history → 연결 화면 → 종료 순서다. Android 13의 back callback은 별도 클래스에 두어 min SDK 30에서 초기화하지 않는다.
- WebView state는 Activity 상태 bundle에 저장/복원한다. 복원 시 자기 기기와 백엔드를 다시 확인한다. 웹 프로세스 종료와 페이지 연결 실패 후 재시도를 제공한다.

## 아직 구현·검증하지 않은 것

- 앱 안에서 OpenCode/Bun/Node/Preroot/Fedora를 내려받고 설치·기동하는 흐름.
- 런타임 foreground service, 실제 작업 프로세스 중단/복구, 패키지 업데이트와 환경 준비 진행률.
- **root 스위치는 현재 진단 클라이언트의 비공개 파일 확인에만 적용된다. 기존 WebView나 별도 OpenCode 백엔드의 실행 권한·이미 실행 중인 작업에는 반영되지 않는다.** 설정 변경으로 root 작업이 중단됐다고 판단하면 안 된다.
- 초기 연결의 ADB RSA 승인에는 Android 시스템의 사용자 승인이 필요할 수 있다. TLS 기반 무선 디버깅 페어링을 구현하지 않았다.
- Provider·API key·custom endpoint·모델 선택은 별도 OpenCode GUI/백엔드에 맡기는 구조다. 이 Android 셸에서 실제 설정 반영이나 응답을 검증하지 않았다.
- WebView activity state 복원은 Android가 저장 bundle을 돌려주는 경우에 해당한다. 완전한 앱 강제종료 이후 native 자동 진입, 긴 작업의 백그라운드 지속, 대화 스크롤과 세션 복원은 실기기 검증이 필요하다.
- 한글 IME, 잠금, 네트워크 전환, 앱/백엔드 재시작, 앱 업데이트 보존 및 핵심 동선 연속 3회 통과는 모두 미검증이다.
- Dadb binary와 전이 의존성 resolve 및 빌드는 통과했다. 전이 의존성 license/NOTICE 목록은 릴리즈 전에 확정해야 한다.
- Release signer는 미설정이다. debug signer와 release signer를 공유하지 않는다. 서명된 release APK는 아직 없다.

## 오프라인 정책 검사

JDK 17만 필요하다. Gradle, 네트워크, Android SDK, 기기 없이 실행된다.

```powershell
powershell -NoProfile -File .\scripts\check-android-policy.ps1
```

2026-09-08 관측 결과: `LocalPolicyCheck: 58 checks passed`, exit 0.
검사 대상은 포트 입력, loopback/backend URL 경계, 외부 브라우저 URL, UID 파싱, shell 경로, root/device/nonce 일치다.
이 결과는 Android 앱 컴파일이나 기기 연결의 증거가 아니다.

## Android 빌드 절차 — 실행 확인

JDK 17, Android SDK platform 36 및 관련 build tools를 준비한다. `ANDROID_HOME` 또는 저장소에 커밋하지 않을 `local.properties`의 `sdk.dir`로 SDK 경로를 연결한다.
AGP 및 Dadb/전이 라이브러리를 정상적인 의존성 저장소에서 확보해야 한다. 네트워크가 차단돼 있고 해당 artifact가 캐시되지 않았다면 진행할 수 없다.

```powershell
pwsh -NoProfile -File .\scripts\build-android.ps1
```

캐시가 모두 갖춰진 뒤에는 `--offline`을 추가할 수 있다. 현재 Dadb source JAR은 의존성 binary 캐시를 대신하지 않는다.
Debug APK 경로: `app/build/outputs/apk/debug/app-debug.apk`.
Release는 프로젝트 전용 서명키와 인증서 지문을 정한 뒤 빌드한다. 현재 설정으로 `assembleRelease`를 실행해도 release 서명을 갖지 않는다.

Gradle wrapper는 기존 SIMShim 프로젝트에서 복사만 했다. Gradle distribution 8.13의 SHA256 검증 값은 wrapper properties에 포함돼 있다.
실기기 검증과 인증서·APK 해시는 `../evidence/SELF-ADB-20260908.md`에 기록했다.

## 라이선스와 고정 API 근거

앱 assets의 `licenses/dadb-LICENSE.txt`, `licenses/opencode-LICENSE.txt`, `licenses/THIRD-PARTY-NOTICES.txt`를 포함했다.
Dadb 1.2.10 소스 API 근거와 출처/hash는 `../dependencies/dadb-1.2.10-API.md`에 기록했다.
OpenCode MIT 사본은 이미 확보된 공식 upstream checkout의 LICENSE에서 복사했다.
이번 앱 셸은 OpenCode frontend/backend binary를 번들하지 않는다.
