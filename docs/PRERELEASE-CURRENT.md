# 현재 프리릴리즈 상태

`0.0.1-alpha.1`은 2026-09-12에 공개 GitHub 프리릴리즈로 게시됐습니다. 이전
Preview 문서는 당시 결과이며, 다음 기록을 현재 판정으로 사용합니다.

## 최신 후보 — 0.0.1 Alpha 1 / runtime12

- APK: `artifacts/TinyAgent-0.0.1-alpha.1-android-arm64.apk`
- SHA-256: `013f05727575620cb04aa9c3aec00098bf137d8652dd0d77ae6e3db3a04e1462`
- 크기 145216194 bytes; versionCode 5 / `0.0.1-alpha.1`; API 30–36;
  ARM64; runtime `1.18.29-tinyagent.12`; dnfast1449710; 하네스 20.
- clean release 빌드와 lint 55개 작업, 패키지 입력, 952 GUI 파일, 2개 런타임,
  PRoot, dnfast, 네이티브·소스 고지 및 10개 bootstrap 검사가 통과했습니다.
- APK Signature Scheme v2, RSA-4096 생산 인증서 SHA-256
  `c34483dc3b7228cede2e128ccd66cab193e78804686a58ea25ba318568afc9d2`를 확인했습니다.
- 같은 runtime12의 debug 패키지는 Lyriq1에서 데이터 보존 업데이트, ARM64 health,
  실제 모델·Shell 도구와 managed LADB Developer UID 2000 shell을 통과했습니다.
  최종 생산 서명 APK도 Lyriq1에 clean 설치해 설치된 `base.apk` 해시 일치,
  versionCode 5, versionName `0.0.1-alpha.1`, cold start와 resumed activity를 확인했습니다.
- runtime12 LADB Developer에서 동일한 8.5 KiB fixture APK의 streaming 재설치,
  관찰 중단 뒤 같은 UUID 완료 복구, 120초 작업의 실제 PID 소멸과 명시적 취소를
  모두 UID 2000으로 통과했습니다.
- clean production은 앱 UID 10000으로 첫 Fedora 준비를 완료했습니다. 기본 Big Pickle이
  실제 bash를 한 번 실행해 `/workspace`, `aarch64`, Fedora 44를 반환했고, `/etc/*`는
  한 번만 허용했습니다. production WebView debug socket이나 기존 debug 인증은 사용하지 않았습니다.
- 생산 서명은 D: 원본과 별도 물리 디스크 E: 백업의 해시·단일 사용자 ACL을 확인했고,
  DPAPI properties 복원과 백업 PKCS12의 `keytool` alias 열기를 통과했습니다. 이 백업은
  Windows 사용자 프로필 의존 로컬 복구본이며 off-host 재난 복구본은 아닙니다.
- `0.1.0-preview.5` 공개 이력 뒤 제품 버전선을 `0.0.1-alpha.1`로 재정의했습니다.
  Android 업데이트 순서는 증가한 versionCode 5로 유지됩니다.
- RADB/Tailscale 셀룰러 transport는 이번 릴리즈에 포함하지 않습니다. LADB는 같은
  Wi-Fi와 Android 무선 디버깅이 필요하며 Wi-Fi 이탈 시 Stock 기능만 계속됩니다.
- 유료 production 공급자 인증, 장시간 작업·복구, 동일 서명 업데이트와 production
  phone self-build는 이번 1회 smoke에서 검증하지 않았습니다.
- 게시된 프리릴리즈: `https://github.com/GPLaider/TinyAgent/releases/tag/v0.0.1-alpha.1`.
  자세한 범위는 `docs/RELEASE-0.0.1-ALPHA.1.md`와
  `evidence/snapshot12-dirty-submodule-optimization.md`를 참조합니다.

## 직전 후보 — runtime6 제외 파일 metadata 보존

- APK SHA-256: `936a3dc100ac5381ba090f3dac883eccf40902150151c827b85910c24bb316d3`
- 크기: 145214650 bytes; 하네스 19, 기존 배포 인증서 유지
- 내용이 같은 스냅샷 제외 파일을 다시 쓰지 않습니다. 수정 전 실패 재현,
  snapshot 55개 통과·Windows 제약 3개 skip, 타입 검사와 release 빌드·lint·패키지·서명 검사 통과.
- 2호기에는 같은 소스의 debug APK `1b05c458728b9d0622e8438708874b692aca9fa4d726798a1d7495cf06675f33`을 설치했습니다.
  실제 runtime6·dnfast1449710 ELF 해시, 기존 journal 52개 파일과 root ID 보존을 확인했습니다.
  runtime5에서는 짧은 확인 요청에 326초가 걸렸습니다.
  runtime6의 실기기 지연 개선은 아직 검증하지 않았습니다.
- dnfast1449710 실행 파일·소스·라이선스와 기록 보존 업그레이드를 앱에 통합했습니다.
  호스트 중단·재시도 검사와 2호기 기록 보존 업데이트 검사는 통과했습니다.
  기존 provider·세션으로 동일 8개 패키지 요청을 재실행 중이며 설치 결과는 아직 미확정입니다.
- 계획 이관 뒤 journal 상태를 검증하는 코드를 추가했습니다. 실제 Android에서
  미완료 상태를 허용하는 수정 전 실패와 수정 후 거부를 확인했습니다.
  이 검사는 전체 런타임 교체의 성공 증거는 아닙니다. `docs/DNFAST-UPGRADE.md` 참조.

## 직전 후보 — runtime5 중복 스냅샷 스캔 제거

- APK SHA-256: `7e67e87a38e5c1e45d8ead36adcf7eacd8ab495dcfa1a4248a18758a72d22890`
- 크기: 145211622 bytes; 하네스 19, 기존 배포 인증서 유지
- 단계 종료에서 이미 만든 스냅샷을 재사용해 변경 목록을 구합니다.
  동일 작업공간의 두 번째 스캔과 이후 쓰기의 혼입을 막습니다.
- 수정 전 실패 재현, snapshot 54개 통과·Windows 제약 3개 skip,
  diff/writer 동시성 검사·타입 검사·release 빌드·lint·패키지·서명 검사 통과.
- 1호기에 debug 후보를 데이터 보존 설치하고, 실제 runtime5 버전·해시·명령 실행·최종 답변을 확인했습니다.
  명령 종료 후 단계 정리는79.930초로 여전히 느립니다. 동일 조건 속도 개선 비교는 미완료입니다.
  `evidence/runtime5-apk-candidate.json`, `docs/SNAPSHOT-LATENCY.md` 참조.

## 직전 후보 — 하네스 19, 동일 크기 손상 파일 재검증 통과

- APK SHA-256: `78f32da60bb7831db7b59e1fc7f8742d71f768bdcc052020895f813a697f1a27`
- 크기: 145211586 bytes; runtime4, 기존 배포 인증서 유지
- 부분 다운로드 재개 시 크기만으로 재사용하지 않고 고정 Git blob ID를 검증하도록
  하네스에 반영했습니다. 사용자 수정 파일·진행 중 쓰기를 보존하며 검증 범위를 명시합니다.
- release 빌드·lint·패키지·서명 검증과 Pacman 데이터 보존 업데이트 통과.
  기존 DeepSeek V4.1 Flash 대화에서 하네스 19를 읽었고, 실제 Shell 출력으로
  잘못된 4바이트 캐시는 `wrong_cache_exit=3`, 정상 캐시는 `valid_cache_exit=0` 확인.
  `evidence/harness19-candidate.json`, `evidence/harness19-tool.xml` 참조.
- 이 검증은 동일 크기 손상 파일 사례에 한정합니다. 전체 소스 복구·모든 모델의
  일반적 준수나 남은 세 앱 빌드 완료를 뜻하지 않습니다.

## 직전 후보 — 측정 런타임 버전 수정, Pacman 재검증 통과

- APK SHA-256: `56f3267098dd3a55c61122ab4515ddc52cbbf714b52d5f45a07329b5b9637e6e`
- 크기: 145211282 bytes; runtime4, 하네스 18, 기존 배포 인증서 유지
- 환경 파일에 고정된 `tinyagent.2`를 쓰던 결함을 수정했습니다. 준비 단계의
  실제 `opencode --version` 출력을 기록합니다. 별도 root PreRoot 설치기의
  버전은 그 설치기에 고정된 아카이브를 설명하므로 함께 변경하지 않았습니다.
- 빌드·lint·포함 파일·서명 검증, Pacman 데이터 보존 업데이트와 기존 대화 복원 통과.
  DeepSeek의 실제 버전 명령은 `1.18.29-tinyagent.4`, exit 0이었으며 환경 파일과
  같은 값을 보고했습니다. `evidence/measured-version-candidate.json` 참조.

## 직전 후보 — 하네스 18, Pacman 모델 재검증 통과

- APK SHA-256: `c2ca323809840bbe48d0c25e25ce247b05a98a88340fdfdaa0e7a1d5f11a6623`
- 크기: 145210906 bytes; 기존 배포 인증서 유지
- release 빌드·lint·포함 런타임·하네스·GUI 해시 검증 통과
- 백그라운드 원본 종료코드 보존과 인증서 지문 비교 지침 추가
- Pacman 데이터 보존 설치 후 기존 DeepSeek V4.1 Flash 대화에서 하네스 18을 읽고,
  `set -e` 상태에서 원본 작업의 종료값 0·23을 보존했습니다. 실제 셸 출력의
  `launcher_reached_end rc0=0 rc1=23`과 인증서 SHA-256 비교 답변을 확인했습니다.
- 이 검사는 짧은 작업의 종료값 보존 검증이며, 모든 장시간 작업 복구 보장은 아닙니다.
- 증거: `evidence/harness18-candidate.json`, `evidence/harness18-ui-receipt.json`.

## 직전 runtime4 후보 — Pacman 기본 실행 검증 통과

- APK SHA-256: `7eb19fad10ee35a867df18544f6cab054ef74c5af78e0ccf57003f734a98c469`
- 크기: 145210658 bytes; 기존 배포 서명 유지
- 런타임: `1.18.29-tinyagent.4`, [스냅샷 잠금 수정](SNAPSHOT-WRITER-ISOLATION.md)
- release 빌드, lint, 서명, 포함 런타임·하네스·GUI 해시 검증 통과
- Pacman에 데이터 보존 업데이트 후 기존 대화·공급자 복원, DeepSeek V4.1 Flash
  응답, 실제 ARM 런타임 버전·해시·종료 코드 0, 파일 작성·수정과 경로 터치→열기
  미리보기의 `after`를 검증했습니다. 증거: `evidence/snapshot4-apk-candidate.json`.
- 장시간 빌드와 스냅샷 경합의 실기기 성능 검증은 별도이며 아직 미완료입니다.
- 아래 Pacman 실기기 결과는 직전 후보의 결과이며, 새 APK의 통과로 간주하지 않습니다.

## 직전 실기기 검증 APK

- 패키지: `io.github.gplaider.tinyagent`
- 아직 유지 중인 버전: `0.1.0-preview.5`, versionCode `4`
- SHA-256: `c7b3fecb341eb382e1ba2d5612e9561ad0f10b812685b43d1c23b124a607f2cf`
- 크기: 145210678 bytes
- 서명: [배포 서명과 빌드 방법](RELEASE-SIGNING.md)의 기존 RSA4096 인증서
- 호스트 release 빌드·lint·서명·포함 런타임 검증 통과

Pacman에서 배포용 앱의 초기 Fedora 준비, OpenCode Go 키 입력, DeepSeek V4.1
Flash 선택, 실제 Fedora 명령·파일 작성·읽기, 파일 경로 터치와 열기, 앱·백엔드
재실행 후 대화·모델·파일·공급자 재사용을 실제 UI로 확인했습니다. 앱 자체는
Stock 권한으로 실행했고 USB ADB는 외부 관찰·설치에 사용했습니다.

위 기본 동선은 이전 후보에서 확인했고, 현재 후보는 그 앱을 데이터 보존 업데이트한
뒤 종료 진단을 추가 검증했습니다. Pacman의 유휴 앱에 오류 종료를 한 번 유도한 후,
Android의 동일 PID 종료 기록(reason 4)과 재실행한 진단 화면의 날짜·앱 오류 안내를
대조했습니다. 현재 Fedora 준비 완료 상태는 별도로 표시됩니다.
증거: `evidence/exit-history-ui-receipt.json`, `evidence/exit-history-diagnostic.xml`.
실제 메모리 부족 종료의 새 UI 검증은 Lyriq 1 작업 종료 후 남아 있습니다.

추가 수정: 대화 백엔드 연결 대기를 취소하고 작업 환경을 열 때 ADB 진단까지
"연결 확인 중단"으로 덮어쓰던 오류를 제거했습니다. 연결 방식 해석도 실행 경로와
같은 함수를 사용합니다. Pacman 업데이트 후 동일 동선에서 Stock 안내와 기존
오류 종료 기록의 동시 표시를 확인했습니다.
증거: `evidence/neutral-adb-diagnostic-fixed.json`, `evidence/neutral-adb-diagnostic.xml`.

검증용 `.debug` 앱과 배포용 앱은 별도 저장소를 사용합니다. OAuth·세션 자동
이동을 지원한다고 해석하면 안 됩니다. 동일 패키지는 같은 서명으로 업데이트하세요.

## 에이전트 빌드 검증

| 기기 | 앱 | 현재 판정 |
|---|---|---|
| Pacman | AntennaPod | 새 APK 빌드 및 독립 해시·ZIP 검증 통과 |
| Pacman | Termux | 첫 결과 재사용 오류 후 수정, 새 APK 5종 독립 검증 통과 |
| Lyriq 1 | Tailscale Android | APK 빌드 후 Android 저장 동선·USB 회수·독립 해시/서명/16KB ZIP 정렬 통과. 설치·실행 미검증 |
| Lyriq 1 | Organic Maps | 소스·자산 확보 진전. 메모리 부족 종료 후 Tailscale 복구 동안 대기 |
| Lyriq 2 | VLC Android | APK 빌드·독립 해시·ZIP·서명·16KB ZIP 정렬 통과; 네이티브 AAR 사용 |
| Lyriq 2 | AppFlowy | VLC 종료 확인 후 DeepSeek 4.1 Flash 투입, 도구 실행 확인 |

VLC는 두 번의 Android 메모리 부족 종료 후 runtime4 데이터 보존 업데이트와
감독자 재개를 거쳐 APK를 생성했습니다. Gradle 힙 1536MiB, Kotlin in-process,
worker 1을 사용했습니다. 네이티브 라이브러리는 기존 AAR을 패키징했으므로
전체 Autotools/NDK 소스 빌드 성공이나 일반적인 메모리 문제 해결로 간주하지 않습니다.
증거: `evidence/vlc-independent-apk-verification.json`,
`evidence/lyriq2-snapshot4-usb-update.json`, [빌드 사례](ARM-BUILD-CASEBOOK.md).
AppFlowy 제출 기록은 `evidence/go-campaign/lyriq2-appflowy-run.json`이며,
관찰 기록은 `lyriq2-appflowy-first-observation.json`입니다. APK 산출은 4/6(VLC는 위 AAR 범위);
나머지 앱과 발견 결함의 재검증이 끝난 상태는 아닙니다.

Lyriq1의 통신 복구 시험은 빌드 캠페인과 별도입니다. 설치된 Tailscale의 동일
버전 재설치와 1.102.4 업데이트 모두 데이터는 보존했지만 VPN 연결은 복구하지
못했습니다. USB를 통한 TinyAgent 세션 조회는 가능합니다. 업데이트가 원인이라고
확정하지 않으며, 인증서 검증을 비활성화하지 않았습니다.

이번 DeepSeek 캠페인의 결과와 개입은
[관찰 기록](DEEPSEEK-CAMPAIGN-OBSERVATIONS.md)에 연결되어 있습니다.
이전 빌드를 이번 캠페인 성공으로 합산하지 않습니다. 사용자가 별도 3회 동선
반복 대신 이 여섯 작업과 발견 결함의 수정·재검증을 릴리즈 기준으로 지정했습니다.

## 수정과 남은 범위

- 앱 업데이트 시 dnfast 실행 지문 변경을 감지해 안전하게 재계획합니다.
  Pacman에서 새 패키지 설치와 다음 업데이트의 캐시 무효화까지 확인했습니다.
- 하네스 14는 SDK 버전 위장, Fedora ADB 목록과 앱 자체 연결의 혼동을 방지합니다.
  실제 DeepSeek 응답에서 지침 준수를 확인했습니다.
- 하네스 15 업데이트 후 Pacman의 기존 배포 대화에서 DeepSeek가 파일을 다시 읽고,
  관찰 대기 30초 제한과 기존 작업 유지 지침을 정확히 확인했습니다.
  증거: `evidence/release-harness15-ui.xml`. 장시간 실제 작업 준수까지 증명한 것은 아닙니다.
- 하네스 16은 실패한 캐시의 증거 보존, 내용·체크섬 검증, 최소 범위 복구를 명시합니다.
  Pacman 배포 앱 업데이트 후 기존 공급자·대화에서 지침을 읽고 설명했습니다.
  첫 버전 답변은 15로 틀렸고, 실제 `head` 명령 재검증에서 16과 종료값 0을 확인했습니다.
  증거: `evidence/harness16-response.xml`, `evidence/harness16-version-probe.xml`.
- Root Android 명령·설치는 Lyriq 2에서 모델 실행까지 검증됐습니다.
- 하네스 17은 생성한 보조 스크립트의 실패 종료값, 실패·성공 검사와 완료 표식 검증을
  요구합니다. Pacman의 기존 배포 앱·DeepSeek 대화에서 실제 보조 스크립트를 만들고
  정상 0·실패 1·실패를 숨긴 파이프라인 0을 도구 출력으로 확인했습니다.
  증거: `evidence/harness17-candidate.json`, `evidence/harness17-tool-*.xml`.
  이 검사는 Organic Maps의 별도 다운로드 스크립트가 수정됐다는 증거는 아닙니다.
  Developer 전체 실행·설치 성공은 현재 후속 검증이 남았습니다.
- 모든 공급자, 모든 Stock 기기, 장시간 잠금·네트워크 전환을 통과했다고
  주장하지 않습니다. Flip7 후속 범위와 생산 서명으로 폰 자체 빌드·업데이트도 남았습니다.
- Lyriq 1에서 Android `LOW_MEMORY`로 WebView와 앱이 종료돼 Go·Git 작업이
  중단됐습니다. 백엔드 재기동 후 대화는 보존됐고 미완료 턴은 중단으로 표시됐습니다.
  감독자가 같은 두 세션에 복구를 요청했으며, 작업 자동 재개나 무중단 실행을
  보장하지 않습니다. 증거: `evidence/lyriq1-low-memory-recovery.json`.

## 소스 재현

GUI 기준은 OpenCode `16747470f976aca3d362ad730bcd3fe82ecc2c9a`와
`patches/opencode-mobile-ux.patch`입니다. `scripts/export-gui-patch.py`는
실제 인덱스를 변경하지 않고 기준 소스에 패치를 적용해 현재 GUI 소스와 일치하는지
검사합니다. 폰 자체 빌드 스크립트의 GUI 채널도 검증된 호스트 빌드와 맞췄습니다.
이 소스 일치 검사는 폰 전체 빌드 성공이나 APK 바이트 단위 재현을 대신하지 않습니다.
`TinyAgent-current-source.zip`의 `SOURCE-SNAPSHOT.json`에 기록된 APK 해시가
위 후보와 일치하는지 확인해야 합니다. 묶음 검증 결과는
`evidence/source-candidate-verification.json`에 기록했습니다. 게시된 source ZIP은
468개 파일과 APK 해시 결합 검증을 통과했습니다.
