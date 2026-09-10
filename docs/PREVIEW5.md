# TinyAgent 0.1.0 Preview 5

Android 폰 안에서 OpenCode 에이전트와 Fedora 개발환경을 실행하는 비공개 프리릴리즈입니다.
versionCode는 4이며 Android 11 이상, ARM64를 대상으로 합니다. 모든 기기에서의 호환성을 검증한 정식 릴리즈는 아닙니다.

## 설치 파일

- `TinyAgent-0.1.0-preview.5-release.apk`: 일반 설치용. 패키지 `io.github.gplaider.tinyagent`, 배포용 서명.
- `TinyAgent-0.1.0-preview.5-debug-update.apk`: 기존 `.debug` 테스트 앱 업데이트용. 기존 개발 서명을 유지합니다. 기존 OAuth·세션을 보존하려면 앱 삭제 없이 이 APK로 업데이트하세요.

두 패키지는 별도 앱입니다. release 앱이 debug 앱의 OAuth·세션을 자동으로 가져오지 않습니다.
두 앱의 로컬 백엔드를 동시에 실행하지 마세요. 기존 앱의 작업을 마친 뒤 작업 환경에서 백엔드를 중단하고 다른 앱을 사용하세요.
SHA256SUMS.txt로 파일 해시를 확인할 수 있습니다. 소스 ZIP은 SOURCE-SNAPSHOT.json의 파일 해시 목록과 연결됩니다.

## 현재 포함된 기능

- 기본 앱 권한으로 준비·실행되는 Fedora 및 로컬 OpenCode. Stock 사용에 ADB 페어링은 필요하지 않습니다.
- 선택적인 무선 디버깅 페어링, 자기 기기·실행 UID 확인, 별도 Root 허용 설정.
- 모바일 대화, 모델·공급자 설정, 세션별 에이전트 승인 모드, 파일 설치·저장·공유와 이미지·영상 보기.
- 작업 준비 알림, 런타임 중단·복구, Android/Fedora 환경을 설명하는 고정·실측 하네스.
- PRoot 부모 종료 시 자식 프로세스 정리와 중단된 OpenCode 도구 상태 복구.
- 자체 빌드는 설치된 APK의 고정 해시 런타임을 재사용합니다. GUI와 APK를 폰에서 컴파일하며 OpenCode 백엔드 바이너리는 고정된 prebuilt 의존성입니다.
- SDK/NDK 준비 스크립트에 파일별 다운로드 바이트·퍼센트, 검증·압축 해제 단계 표시 추가.

## 확인된 검증과 범위

Preview 5의 release/debug APK 모두 clean 빌드와 lint, 기존 서명 검증,
포함된 런타임·하네스·GUI·라이선스 파일 검사를 통과했습니다.
진행 중인 실기기 빌드를 보존하기 위해 Preview 5 자체의 실기기 재설치 검증은 아직 수행하지 않았습니다.

이번 버전 기반인 `6dd6715457d7ec2355e0656a206f6bf1ffafd73dc4512bc14670476aa4885d73` APK의 Lyriq1 검증:

- 업데이트 후 기존 45개 세션 ID, OpenAI/OpenCode 공급자 연결, 다크 설정 유지.
- 기존 OAuth의 GPT-5.6 Luna가 실제 도구로 설치 APK의 Fedora/OpenCode 해시와 쓰기 거부를 확인. Stock 실행 UID10042 확인.
- WebView 연결 중단 중 Luna 도구 실행·응답 완료 후 화면 복구 1회 통과. 실제 Wi-Fi/모바일망 전환 검증과는 다릅니다.

이전 후보의 PRoot 종료·중단 상태 복구 반복 결과와 production 첫 실행 검증은 각 문서에 별도로 기록되어 있습니다.
이전 후보 결과를 Preview 5의 핵심 동선 연속 3회 통과로 합산하지 않습니다.

Pacman 폰 내부 빌드에서 AntennaPod, Termux, Organic Maps, Tailscale APK 생성 확인.
처음 세 앱은 설치·화면 확인까지 진행했습니다. Organic Maps 성공 실행은 캐시를 재사용한 재검증입니다.

## 아직 남은 항목

- 현재 소스로 TinyAgent APK를 폰에서 다시 만드는 전체 빌드는 진행 중입니다. 산출 APK·자체 업데이트 성공은 아직 확인되지 않았습니다.
- VLC 빌드 진행 중, AppFlowy 재검증 미완료. dnfast/dnf5의 동일 초기 조건 성능 비교도 미완료입니다.
- 최신 APK의 전체 핵심 동선 연속 3회, 실제 네트워크 전환·인증 잠금·장시간 사용 검증 미완료입니다.
- Android 에이전트 브리지는 현재 읽기 전용 진단입니다. 임의 Android shell 작업의 스트리밍·중단·재시작 복구는 완성되지 않았습니다.
- 하단 프로젝트 탭과 긴 출력 등 모바일 UI 개선이 남아 있습니다. 이미지·영상 검증은 제한된 샘플 범위입니다.
- 새 release 패키지는 별도 OAuth 설정이 필요합니다. 폰 내부 production 서명 키 준비와 동일 서명 자체 업데이트 검증은 미완료입니다.

## 사용과 진단

앱 실행 → 환경 준비 → 대화 시작 → 공급자 로그인/설정 순서로 진행하세요.
처음 준비에는 네트워크와 저장공간이 필요하며 수 분 이상 걸릴 수 있습니다.
작업 환경의 진단 정보에서 실제 오류를 확인하고, 작업을 중단한 경우 환경 준비로 런타임을 다시 시작하세요.
생성 파일은 대화의 파일 액션 또는 작업 환경의 파일 내보내기를 사용하세요. `/workspace`와 `/shared`는 앱 내부 경로입니다.

빌드·서명은 README.md, RELEASE-SIGNING.md와 self-build 스크립트에 기록되어 있습니다.
비밀키와 OAuth 자격증명은 릴리즈에 포함하지 않습니다. OpenCode 및 네이티브 의존성의 라이선스·출처는 소스와 APK에 포함됩니다.
