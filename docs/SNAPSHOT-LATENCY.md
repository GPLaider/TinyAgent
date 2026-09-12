# 단계 종료 지연 수정 후보

1호기에서 도구 종료 후 다음 응답까지 긴 공백을 관측했다. USB에서 실제 Git
스냅샷 프로세스도 확인했으나, 모든 지연을 스냅샷 하나로 설명하지 않는다.
모델 응답·네트워크·작업공간 스캔 시간을 분리해 측정해야 한다.

현재 `processor.ts`의 step-finish는 `snapshot.track()`으로 완료 트리를 만든 뒤
`snapshot.patch()`에서 작업공간을 다시 스캔하고 stage했다. runtime5 후보는
완료 트리를 patch에 넘겨 두 불변 트리 사이에서 변경 파일을 구한다.
완료 트리가 없는 중단 정리 경로는 기존 스캔 동작을 유지한다.

새 회귀 테스트는 완료 트리 뒤에 쓰인 파일이 앞 단계 patch에 섞이는 것을
수정 전 실패로 재현했다. 수정 후 snapshot 54개 통과, Windows 제약 3개 skip,
실패 0개. 별도 diff/writer 동시성 테스트와 타입 검사도 통과했다.
`evidence/snapshot5-host-checks.json`에 후보 해시와 검증 범위를 기록했다.

**1호기 수정 APK 설치 완료. 속도 향상 수치 미측정.** 새 서명 후보 APK는 runtime5를 포함하며
패키지·서명·lint 검증을 통과했다. 1호기 ZY22J58799에 데이터 보존 업데이트했고,
설치된 APK SHA256은 `cd72a752c8839cf470bf5087e605077f051c951f656ade33fd344d9e878fe19d`다.
`evidence/lyriq1-runtime5-update.json`에 설치 직전 전체 세션 idle과 앱 UID의
빌드 프로세스 부재를 기록했다. 유지보수 응답만 정상 abort했으며 빌드는 죽이지 않았다.
기존 대화에서 버전 `1.18.29-tinyagent.5`, 실제 ELF SHA256
`0e3c1f383300842b6e5817cc379c2f743e6d003b8b43e5550825f9ba643b63df`를
명령 출력으로 확인했고 최종 답변 후 세션 idle까지 확인했다.
명령 종료 → 해당 assistant 단계 완료는 79.930초였다. 요청 생성 → 최종
답변 완료는 326.497초다. 이전 관측 151초와는 서로 다른 명령이므로 성능
향상률을 주장하지 않는다. 여전히 긴 지연이며 전체 작업공간 검사와 모델
대기를 더 분리해야 한다. 원본 타임스탬프는 `evidence/runtime5-phone-probe.json`에 있다.
확인 후 기존 Tailscale 작업을 한 번 재개했다. 변경 diff와 복구의 추가 회귀,
동일 조건의 도구 종료 후 지연 비교는 남아 있다.
UI는 도구의 running 상태에 따라 기존 번역의 명령 실행·검색·수정 상태를
선택하도록 수정했다. 도구 완료 후에는 다음 단계 검토 표시로 전환한다.
session-ui 84개 검사와 타입 검사 통과. 최초 GUI build가 APK를 바꾸지 않아
추적한 결과, 모바일은 별도 `message-timeline.tsx` 경로를 사용했다. 이 경로도
같은 상태 함수에 연결했고 app 타입 검사와 타임라인 31개 검사를 통과했다.
모바일 폭 412x915의 production Chromium 검사에서 접근성 라벨 기준
Running commands → Considering next steps → idle 시 표시 제거를 통과했다.
기존 shimmer는 시각 효과용 텍스트 2개가 있으므로 raw textContent를 상태
검증에 사용하지 않는다. 실제 화면 캡처도 확인했다.
새 GUI debug APK SHA256은
`007db8fc9d365741b180615502e68377d985febe3dbaa853ad843dbfb675062b`.
빌드·lint·서명·GUI 952개 자산 해시 검증 통과. 실기기 설치·표시 검증은
남았다. 서버 내부 스냅샷 구간을 측정하는 기능은 아니다.

수정 전 기존 320턴/160 delta 벤치마크는 스트리밍 측정에 진입하기 전
waitForStableGeometry에서 480초 timeout으로 실패했다. 비교 가능한 속도
수치는 없다. 실패 캡처에는 현재 turn의 edit만 보이고 추가 text part가
보이지 않는다. fixture/SSE/조회 응답 일관성 추적이 필요하며 원인은 아직
확정하지 않았다. `evidence/thinking-timeline-before.log`에 원본을 보존했다.

후속 runtime6 후보는 내용이 같은 `info/exclude`를 다시 쓰지 않는다.
기존 코드는 매 검사마다 제외 파일의 metadata를 바꿨다. 새 회귀 검사는
수정 전 mtime 변경으로 실패했고 수정 후 보존에 성공했다. 실제 제외 규칙
변경을 포함한 snapshot 55개 통과, Windows 제약 3개 skip, 타입 검사 통과.
ARM ELF와 압축 archive도 생성·검증했다. `evidence/snapshot6-host-checks.json`에
고정 해시를 기록했다. runtime6는 2호기에 데이터 보존 업데이트했고 실제 ELF와
기존 52개 작업 journal의 바이트 보존을 검증했다. Git 캐시 효율이나
실제 지연 개선 정도는 측정 전이다. 모든 대기를 해결했다고 주장하지 않는다.

runtime6 후속 관측: 2호기의 업데이트 후 재개 요청에 속하는 assistant
메시지 4개에서 마지막 도구 종료→메시지 단계 완료는 각각 86/66/49/29ms다.
업데이트 전 대화는 재개 user message ID로 제외했다.
`evidence/runtime6-observed-latency.json`에 원본 message ID·시각을 기록했다.
40분 관찰 명령 timeout 1건도 포함하며, 이는 사용자 요청→최종 응답 전체
시간이나 provider 첫 토큰 지연을 측정한 것이 아니다. 1호기와의 동일 조건
비교가 아니므로 runtime6 성능 개선율을 주장하지 않는다.

2호기의 별도 장기 대기 조사: package job
`19d1060c-fcf4-40a8-8718-d22a7b2788e0`는 native PID 19061이 살아 있었으며,
14분 36초 경과 / CPU 8초, syscall 207(fd14), 연결된 HTTPS socket을 관측했다.
이는 모델 계산 대기가 아니라 해당 시점의 native network 수신 대기다.
동일 read가 전체 시간 동안 지속됐다는 증거는 아니다. dnfast 담당 기존
세션에 timeout 구현 검토를 전달했다. job은 중단·중복 실행하지 않았다.
원본은 `evidence/inspect-dnfast-wait.json`과 `read-lyriq2-package-job.json`.
