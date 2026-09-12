# 기존 환경 업데이트

dnfast의 `app-runtime check`는 상태 조회다. exit 0이어도 `message` 안의
journal 상태에 `started`나 `rpm_result`가 남을 수 있다. 이를 설치 완료나
교체 가능의 증거로 쓰지 않는다.

TinyAgent는 계획 binding 변경 시 기존 `check → migrate` 뒤에 상태 검증을
추가했다. 새 계획을 만들기 전에 모든 남은 journal이 `reconciled`여야 한다.
이전 revision과 불일치해도 성공·실패로 끝난 기록은 허용하며 수정하지 않는다.
중복 ID, 잘못된 자료형, 알 수 없는 상태는 거부한다.

`DnfastResultCheck.main`을 Pacman의 Android JSON 구현에서 실행해, 수정 전
미완료 상태 수락 실패와 수정 후 정상 거부를 확인했다. 증거는
`evidence/dnfast-journal-gate.json`이다. APK나 RPM 상태를 바꾸는 검사는 아니다.

1449710 런타임 교체를 앱에 연결했다. APK 설치 경로가 binding에 포함되므로
기존 작업의 recovery는 기존 앱·runtime·bind 설정이 실제로 일치할 때 수행해야 한다.
교체 직전 root lock에서 journal 목록과 내용이 바뀌지 않았는지 재확인해야 하며,
미완료 journal을 지우거나 해시를 위장하지 않는다. 새 runtime에서는
check → migrate → 검증 → refresh 후 새 계획을 생성한다.

43b 실행 파일이 남아 있으면 실제 이전 CLI/executor 해시로 새 authenticated
launcher 요청을 만들어 `check`한다. 여기서 Prepared/Reconciled만 허용한다.
검사 전 상태 스냅샷과 교체 직전 root lock 안의 스냅샷이 같아야 하며, journal은
다시 쓰지 않는다. 미완료 기록의 자동 복구를 새 binding으로 시도하지 않는다.

교체 전 원본 ELF를 백업하고 각 디렉터리 생성·파일·rename을 fsync한다.
부분 staging이 정확한 새 payload의 접두부일 때만 이어 쓰고, 다른 내용이면
보존 후 거부한다. 양쪽 ELF 교체 뒤 중단돼도 체크포인트가 남아 있으면
다음 실행에서 migrate/verify를 재개한다. verify 성공 뒤 체크포인트를 해제한다.

Linux 호스트에서 빈 상태와 기록이 있는 상태의 보존, 기록 변경 거부,
부분 staging·publication 중단 후 재시도, 백업·root ID 보존 검사가 통과했다.
실제 전원 손실과 폰 내부 전체 업데이트의 성공은 이 호스트 검사로 증명하지 않는다.
