# TinyAgent 0.0.1 Alpha 1

첫 공개 알파 기준선을 위한 ARM64 Android 프리릴리즈입니다. 과거
`0.1.0-preview.5` 공개 이력보다 SemVer 숫자는 낮지만 Android `versionCode`는
4에서 5로 증가하므로 같은 생산 패키지는 정상 업데이트할 수 있습니다.

## 설치 파일

- `TinyAgent-0.0.1-alpha.1-android-arm64.apk`
- 패키지: `io.github.gplaider.tinyagent`
- versionCode / versionName: `5` / `0.0.1-alpha.1`
- Android: 11 이상, API 30–36
- ABI: `arm64-v8a`
- SHA-256: `013f05727575620cb04aa9c3aec00098bf137d8652dd0d77ae6e3db3a04e1462`
- 생산 인증서 SHA-256:
  `c34483dc3b7228cede2e128ccd66cab193e78804686a58ea25ba318568afc9d2`

`.debug` 개발 패키지는 별도 앱입니다. 개발 패키지의 OAuth, 대화, 작업공간과
설정은 생산 패키지로 자동 이동하지 않습니다. 기존 생산 패키지는 삭제하지 말고
이 APK로 업데이트해야 데이터가 보존됩니다.

## 포함 범위

- 앱 권한으로 실행되는 Fedora 44 및 로컬 OpenCode
- Stock 상태의 소스 작성, Android 앱 빌드, 파일 미리보기·저장·공유 및
  사용자 승인을 거치는 APK 설치
- OpenAI, OpenCode 및 OpenCode Go 공급자 설정 UI
- 세션별 승인 모드, 백그라운드 작업 상태, 중단·재연결 복구
- 고정 입력으로 검증되는 PRoot, dnfast, ARM64 OpenCode runtime
- 선택적 LADB Developer 연결의 자기 기기·UID 2000 검증과 managed Android shell
- 별도 허용이 필요한 Root transport

## 검증 결과

- clean release build 및 lint: 55개 작업 통과
- OpenCode 관련 테스트: 108 pass, 17 skip, 0 fail
- APK Signature Scheme v2, RSA-4096 생산 서명 통과
- release manifest: package/version/API/ARM64 확인, debug probe 제외
- 정확한 생산 APK를 Lyriq1에 clean 설치해 설치된 `base.apk` 해시 일치,
  versionCode/versionName, cold start 및 resumed `AppActivity` 확인
- 패키지 입력: 하네스, GUI 952개 파일, 런타임 2개, PRoot, dnfast,
  native/source notices, bootstrap 10개 검증 통과
- Edge 40 runtime12 health, 실제 모델·Shell 도구 실행 통과
- 실제 모델 → managed client → LADB → Android UID 2000 shell 통과
- runtime12 LADB Developer에서 동일 해시의 무해한 8.5 KiB fixture APK를
  streaming 재설치해 UID 2000, PackageManager 확인, versionCode 1과 빈 stderr 확인
- 실행 중 Android job의 Fedora 관찰 프로세스를 중단한 뒤 같은 UUID로 재조회해
  UID 2000 작업 완료 확인; 별도 120초 작업은 실제 worker PID 소멸과 `cancelled` 확인
- 정확한 생산 APK의 첫 Fedora 준비를 앱 UID 10000으로 완료하고, clean production의
  기본 Big Pickle이 bash를 한 번 실행해 `/workspace`, `aarch64`, Fedora 44를 반환
- 생산 서명 원본과 별도 물리 디스크 백업의 해시·ACL, DPAPI properties 복원 및
  `keytool` alias 열기 검증 통과

## 알려진 제한

- 알파 버전이며 모든 Android 기기·공급자·장시간 작업 조합을 보장하지 않습니다.
- LADB는 같은 Wi-Fi와 Android 무선 디버깅이 필요합니다. Wi-Fi 밖에서는 Stock
  기능은 계속되지만 Developer shell/install은 사용할 수 없습니다.
- RADB/Tailscale 셀룰러 transport는 조사 단계이며 포함하지 않습니다.
- 대형 untracked 작업공간에서는 snapshot 준비에 약 35–37초의 Git 스캔이 남습니다.
- 첫 환경 준비에는 네트워크, 수 GB의 여유 공간과 기기에 따라 긴 시간이 필요합니다.
- 생산 패키지는 clean 설치·첫 준비·기본 공개 모델 1회만 확인했습니다. 유료 공급자 인증,
  장시간 작업·복구, 생산 동일 서명 업데이트와 phone self-build는 반복하지 않았습니다.
- 서명 백업은 별도 로컬 디스크이지만 Windows CurrentUser DPAPI에 의존합니다. 사용자
  프로필까지 잃는 재난에 대비한 off-host 백업은 별도로 필요합니다.

APK와 소스 ZIP은 함께 제공되는 `SHA256SUMS.txt`로 확인합니다. 비밀키와 OAuth
자격증명은 APK와 소스 묶음에 포함되지 않습니다.
