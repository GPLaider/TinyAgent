# Security Policy

## 지원 범위

TinyAgent는 현재 alpha 소프트웨어입니다. 최신 공개 프리릴리즈인
`0.0.1-alpha.1`과 `main`에 재현되는 문제를 우선 확인합니다. 과거 Preview APK와
개별 개발 snapshot에는 보안 수정이 소급 적용되지 않을 수 있습니다.

## 취약점 비공개 제보

보안 취약점은 공개 issue에 올리지 말고 GitHub의
[비공개 취약점 제보](https://github.com/GPLaider/TinyAgent/security/advisories/new)를
사용하세요. 다음 내용을 포함하면 확인이 빨라집니다.

- 영향을 받는 TinyAgent 버전과 APK SHA-256
- Android 기기·OS·ROM 및 실행 모드(Stock, LADB, Root)
- 재현 단계와 기대 결과·실제 결과
- 공격자가 필요로 하는 권한과 예상 영향
- 비밀을 제거한 최소 로그 또는 PoC

API 키, OAuth token, ADB 개인키, production 서명키, 개인 대화나 전체 작업공간을
제보에 첨부하지 마세요. 필요한 최소 부분만 삭제·마스킹해 제공하세요.

## 특히 중요한 보안 경계

- 다른 Android 기기를 자기 기기로 오인하지 않아야 합니다.
- Stock 작업이 앱 UID 경계를 벗어나지 않아야 합니다.
- UID 2000 또는 root 실행은 사용자가 연결·허용한 자기 기기에만 적용돼야 합니다.
- ADB identity, backend secret과 공급자 자격증명이 UI·로그·artifact에 노출되지 않아야 합니다.
- WebView가 loopback backend 외의 임의 origin에 privileged access를 제공하지 않아야 합니다.
- APK 업데이트는 문서화된 GPLaider 생산 인증서로 서명돼야 합니다.

본인이 소유하거나 명시적으로 테스트 권한을 받은 기기와 계정만 사용하세요. 외부
시스템을 대상으로 한 능동 테스트 권한을 이 저장소가 부여하지는 않습니다.

## 공식 APK 확인

공식 APK는 GitHub Release에서만 배포합니다. `0.0.1-alpha.1`의 생산 인증서
SHA-256은 다음과 같습니다.

```text
c34483dc3b7228cede2e128ccd66cab193e78804686a58ea25ba318568afc9d2
```

APK 파일 해시는 각 Release의 `SHA256SUMS.txt`와 대조하세요.
