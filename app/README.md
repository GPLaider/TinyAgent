# TinyAgent Android 앱

이 모듈은 TinyAgent의 Android UI, 수명주기, 로컬 Linux 런타임과 자기 기기 ADB
연결을 담당합니다. 공개 기준 버전은 `0.0.1-alpha.1`, package는
`io.github.gplaider.tinyagent`, 개발 package는 `.debug` 접미사를 사용합니다.

## 요구사항

- JDK 17
- Android SDK Platform 36 및 대응 build tools
- Gradle wrapper 8.13
- min SDK 30, target SDK 36
- production 패키지 대상은 `arm64-v8a`

`ANDROID_HOME`을 설정하거나, Git에 포함되지 않는 `local.properties`에 `sdk.dir`을
지정합니다.

## 개발 빌드

```powershell
.\gradlew.bat :app:assembleDebug
.\gradlew.bat :app:testDebugUnitTest
```

생성 파일:

```text
app/build/outputs/apk/debug/app-debug.apk
```

Unix 계열 셸에서는 `./gradlew`을 사용합니다.

## release 빌드

production release는 저장소 밖의 전용 PKCS12와 `release.properties`를 사용합니다.
서명키·비밀번호·OAuth 자격증명을 저장소에 추가하면 안 됩니다. 서명 설정 없이 만든
APK를 공식 release로 취급하지 않습니다.

```powershell
.\gradlew.bat :app:clean :app:assembleRelease :app:lintRelease --offline --no-daemon
python scripts/check-packaged-runtime.py --variant release --apk app/build/outputs/apk/release/app-release.apk
```

공식 배포 전에는 Android SDK `apksigner verify --verbose --print-certs`로 인증서가
문서화된 생산 지문과 같은지 독립적으로 확인합니다. 전체 절차는
[`docs/RELEASE-SIGNING.md`](../docs/RELEASE-SIGNING.md)를 따릅니다.

## 주요 경계

- Stock 런타임은 앱 UID로 실행하며 ADB나 root를 요구하지 않습니다.
- LADB Developer는 사용자가 페어링한 자기 기기만 허용하고 UID 2000을 확인합니다.
- unrestricted root는 기본적으로 꺼져 있으며 자기 기기 nonce 검증 뒤에만 허용됩니다.
- WebView의 내부 origin은 loopback OpenCode backend로 제한합니다.
- 외부 HTTP(S)는 시스템 브라우저로 보내고 `file:`·`content:` 접근은 허용하지 않습니다.
- ADB 개인키, backend secret과 공급자 자격증명은 로그나 UI에 출력하지 않습니다.

## 런타임 입력

대형 GUI·runtime·native 산출물은 저장소에 직접 커밋하지 않고 검증된 manifest와
staging 스크립트로 패키징합니다. `.gitignore`의 runtime asset 규칙을 우회해 로컬
빌드 결과를 추가하지 마세요.

패키지 검증기는 고정 하네스, PRoot, dnfast, bootstrap, GUI manifest, 네이티브 고지와
압축 runtime의 해시를 확인합니다. 이 검사는 라이선스 법률 검토나 여러 기기에서의
실행 검증을 대신하지 않습니다.

## 관련 문서

- [프로젝트 README](../README.md)
- [Android 실행 통합](../docs/ANDROID-EXECUTION-INTEGRATION.md)
- [지원 기능](../docs/CAPABILITIES.md)
- [현재 상태](../docs/STATUS.md)
- [기여 안내](../CONTRIBUTING.md)
