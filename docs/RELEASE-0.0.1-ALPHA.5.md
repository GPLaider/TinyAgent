# TinyAgent 0.0.1 Alpha 5

휴대폰 파일과 앱 작업 폴더의 이미지·PDF·텍스트를 대화에 첨부하고,
작업 파일을 탐색·미리보기·저장·공유할 수 있는 Android ARM64 프리릴리스입니다.
기존 생산 패키지에 같은 인증서로 업데이트하며 앱 데이터는 삭제하지 않습니다.

## 설치 파일

- 파일: `TinyAgent-0.0.1-alpha.5-android-arm64.apk`
- 패키지: `io.github.gplaider.tinyagent`
- 버전: `0.0.1-alpha.5`, versionCode `9`
- 지원: Android 11 이상, API 30–36, `arm64-v8a`
- 크기: `145267343` bytes
- SHA-256: `e361ff206034d372cdf029001ddc5ec0ae5633031556b6f3d39c286f06ff7e01`
- 생산 인증서 SHA-256: `c34483dc3b7228cede2e128ccd66cab193e78804686a58ea25ba318568afc9d2`

alpha.4/code 8은 로컬 기기 검증용 후보였으며 이번 공개 버전은 alpha.5/code 9입니다.
다른 서명이나 `.debug`/`.preview` 패키지는 별도 앱입니다.

## 변경 내용

- 대화의 **+ → 이미지 및 파일**에서 **휴대폰 파일** 또는 **앱 작업 폴더** 선택.
- 휴대폰 파일 최대 16개, 작업 폴더 파일 한 개·32 MiB 이하 첨부.
- 첨부 삭제 버튼을 터치 화면에 항상 표시하고 여러 첨부를 줄바꿈.
- 상단 **파일**에서 폴더 탐색, 시스템 뒤로가기, 마지막 폴더 복원과 파일 메뉴 제공.
- 이미지·PDF는 지원 모델이 필요함을 선택 전에 안내. 모델 자동 변경은 하지 않음.
- 취소·대화 전환 시 첨부 콜백 정리, 선택기 출처와 URI·개수 검사.
- 공개 alpha.3의 로고, 패키지 관리자 선택, 명령 진행 표시, phone-use 기능 유지.
- 앱 업데이트 후 기존 런타임 자동 재개, VPN에 DNS가 없을 때 검증된 단일 물리망
  DNS 사용, 정확히 만료된 dnfast 설치 계획만 한 번 갱신·재시도.

dnfast HTTP 벤치마크 바이너리는 포함하지 않습니다. 기존 고정 dnfast1449710
런타임을 유지하므로 미검증 HTTP 런타임 이전을 일반 업데이트에 넣지 않았습니다.

## 두 기기의 실제 검증

동일한 위 APK를 `adb install -r`로 설치했습니다. 앱 삭제·데이터 초기화 없이
설치된 `base.apk` 해시, UID와 최초 설치 시각을 대조했습니다.

| 기기 | 시작 버전 | 업데이트 뒤 UID | Android | ADB 상태 |
|---|---|---|---|---|
| Nothing Phone (1), Spacewar A063 | alpha.4 / code 8 | 10213 유지 | 16 | 기존 UID 0 |
| Nothing Phone (2a), Pacman A142 | alpha.3 / code 7 | 10235 유지 | 16 | UID 2000 |

앱과 Fedora는 각 앱 UID로 실행합니다. ADB 권한은 시험 장치 제어에 사용한
상태이며 앱 사용의 root 요구사항이 아닙니다. 시험 중 root를 활성화하지 않았습니다.

두 기기 모두 Android WebView와 네이티브 선택기를 직접 조작해 다음을 확인했습니다.

- PNG·PDF·TXT 세 파일 다중 선택, 첨부 줄바꿈, 이미지·PDF 제거 후 TXT 전송.
- Big Pickle이 프롬프트에 넣지 않은 `ORCHID-ALPHA5-915` 코드를 읽고
  `/workspace/alpha5-915/notes/verified.txt`를 생성.
- 폴더 이동·시스템 뒤로가기·마지막 폴더 복원을 각각 3회 연속 확인.
- 생성 파일 미리보기, Android 문서 선택기로 저장, 시스템 공유창 표시 후 취소.
- 첨부 출처 선택 취소·작업 폴더 선택 취소·다시 열기를 각각 3회 확인.
- 작업 폴더 파일 재첨부와 실제 모델의 내용 읽기·`sha256sum` 실행.
- Muse Spark 1.3 Free가 PNG와 PDF 각각의 파란 사각형·주황 원·흰 배경을 설명.
- 작업 폴더 창의 가로 회전 후 현재 폴더·파일 유지. 휴대폰 선택기 회전 후
  Spacewar는 Activity 재생성으로 선택 취소, Pacman은 선택한 TXT 한 개 반환을 확인.
  두 기기 모두 이후 작업 파일 재첨부·제거에 성공했고 기존 회전 설정을 복원.
- 최종 설치 APK 해시 재확인, Big Pickle 선택·미전송 첨부 없음 확인.
  현재 앱 PID 대상으로 최근 500행을 요청한 logcat 결과(Spacewar 98행, Pacman 141행)에서
  `FATAL EXCEPTION`, `Uncaught`, `ERR_ACCESS_DENIED`, `SecurityException`, `ANR in` 일치 없음.
  이는 제한된 최근 로그 확인이며 장시간 무오류 보증은 아닙니다.

저장한 바이트는 모델이 만든 앱 내부 파일과 비교했습니다. 원래 첨부의 줄바꿈을
모델이 재작성하므로 원본 TXT와 생성 TXT의 일치 여부를 저장 기능의 기준으로 삼지 않습니다.

| 기기 | 앱 내부 생성 파일과 내보낸 파일의 SHA-256 |
|---|---|
| Spacewar | `673c55cdd0733f444b6e0d17c00e6986638c20712bab70e9ecec8620b82addfb` |
| Pacman | `74e80b1fc38870a2ea939bb99151ce1aa92b88f857769cd744524ebc4401bebd` |

## 호스트 검사

- 첨부 결과 22개, 실제 폴더·링크 13개, 패키지 관리자 19개, 서비스 수명주기 27개,
  DNS 10개, 패키지 계획 갱신 검사 통과.
- phone-use 20개 Windows 검사 통과. POSIX 권한은 Linux에서 별도 통과.
- Linux의 비특권 UID 65534로 FD 회귀 2034개, 복사 23개, export 수명주기·250회
  destination 실패 정리 검증 통과.
- release 빌드·lint 통과. lint 오류 0개·경고 59개.
- 서명 v2·16 KiB ZIP 정렬, GUI 952개·런타임 2개·native·harness·phone-use·license·bootstrap 검사 통과.

기존 회귀 스크립트의 Windows JDK 실행 파일 이름·UTF-8·POSIX 권한 조건을
플랫폼에 맞게 수정했습니다. Debian WSL에서는 loopback stream 시험 2개가
연결 거부로 실패했고, 같은 20개 전체 시험은 Windows에서 통과했습니다.
WSL의 네트워크 설정은 변경하지 않았습니다.

GUI는 공개 alpha.3 APK의 해시 검증된 자산을 재사용합니다. 해당 GUI 소스 변경은
이 릴리스에 통합된 `df39e9b` 기준과 같습니다. dnfast launcher와 debug probe는
현재 소스에서 빌드했고 debug probe는 생산 APK에 포함하지 않습니다.

첨부한 소스 ZIP의 `SOURCE-SNAPSHOT.json`은 각 파일의 실제 Git export 바이트와
위 APK 해시를 연결합니다. APK는 작업 트리에서 빌드한 후 고정해 검증했으며,
이후 문서·호스트 검사만 정리했습니다. clean checkout 재현 빌드 검증은 아닙니다.

## 알려진 범위

이미지·PDF 지원은 모델에 따라 다릅니다. 파일 이동·이름 변경·삭제·휴대폰 파일의
작업 폴더 가져오기는 제공하지 않습니다. 외부 앱에 공유를 실제로 전달하는 과정,
대용량 첨부, OS 프로세스 종료 복원, 모든 유료 공급자·인증 조합은 이번에 검증하지 않았습니다.

이번 검증은 기존 환경의 업데이트와 첨부·파일 동선입니다. 기기 초기화, clean
first-install 3회, Root 설치, production 폰 자체 빌드는 수행하지 않았습니다.
`check-release.py`의 7개 전체 journey × 3회 정식 gate 통과를 주장하지 않는
기능 범위가 명시된 프리릴리스입니다.

원본 증거는 작업 폴더 `.checks/release-alpha5/Spacewar`와 `Pacman`에 보관합니다.
시험 파일·대화는 보존하며 외부 공유창에서는 사람이나 다른 앱에 전송하지 않았습니다.
