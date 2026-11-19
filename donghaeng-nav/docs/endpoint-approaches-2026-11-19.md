# 보행 경로의 출발·도착 연결 비교

2026-11-19 KST · Android 1.0.6 / 웹

월곡 상세 다익스트라는 같은 등록 연결의 가까운 후보를 출발과 도착 각각 최대 4개까지 비교한다. 경로 비용에 핀 접근 거리를 포함하며, 휠체어의 기존 노면 미확인 구간 우선순위, 계단 제외, 경사 제한, 운영시간 기준 휴식 경유를 적용한다. 휴식 경로는 기존 단일 접속점 흐름을 사용한다. 건물 겹침이 없는 후보를 먼저 비교하며, 연결 심사 실패는 기존 검토용 흐름으로 표시한다. 평행 도로의 연결이 모호하면 핀 재지정을 요청한다. [실제 월곡 그래프 비교](route-choice-real-results.json)

서울 참고 A*는 가장 가까운 적격 노드에 연결된 등록 선분으로 핀을 투영하고, 선분의 양 끝에서 출발하거나 도착하는 비용을 하나의 탐색에서 비교한다. 선택한 등록 선분의 일부를 지도와 거리 계산에 반영한다. 핀에서 등록 도로까지의 간격은 미확인 접근 거리로 따로 표시한다. 그래프의 도로나 횡단을 추가하지 않았다. 서로 단절된 그래프는 연결 실패를 반환한다.

서울 고정 좌표 13쌍의 계단 회피 조건을 동일하게 적용했다. 기존·변경 후 모두 경로 있음 10쌍, 연결 실패 3쌍이었다. 강남 표본은 접근 포함 1,058m에서 1,019m로 바뀌었고, 마포 표본은 등록 선분을 따라서 계산한 접근을 포함해 1,591m에서 1,619m로 바뀌었다. 월곡 루나밸리 부근 도로 기준점의 회귀 검사에서 후보 다양성을 유지했다. 원래 사용자의 정확한 핀과 현장 통행은 별도 확인이 필요하다. [서울 전후 비교](endpoint-approaches-results-2026-11-19.json) · [Node와 Vercel 진입점 검사](city-walk-api-results.json)

모의 선분에서는 불필요한 되돌아가기가 줄어 접근 포함 159m에서 123m로 바뀌었다. 조건을 위반하는 계단, 경사 미등록, 연결 없는 그래프를 검사했다. 원본 11개와 연구 자료, 서울 그래프는 같은 해시를 유지했다. [재현 검사](../scripts/test-endpoint-approaches.mjs)

Android 1.0.6에는 대략적인 GPS 위치 표시와 **더보기 → API 설정 → ← 메뉴로** 버튼 개선도 포함된다. 앱 ID는 `app.donghaeng.gill.demo`이고 1.0.5와 서명이 같다. 공개용 빌드에는 고정 키가 없다. Android 모의 브리지와 Chromium을 검사했다. 실제 휴대폰에서 이 APK를 설치해 이동하는 시험은 남아 있다. [APK 확인 결과](endpoint-approaches-apk-results-2026-11-19.json)

## 배포

소스 `fd23f77`를 `feature/cheongju-osco-demo`와 `main`에 푸시했다. 연결된 Vercel 두 프로젝트가 배포에 성공했고, 운영 자산 8개 해시 일치와 강남 표본 1,019m 정상 응답, 웹 대중교통 차단을 확인했다. [운영 확인](endpoint-approaches-production-results-2026-11-19.json)

공개 ZIP은 다운로드 태그 `2bc8b42`에서 제공한다. GitHub에서 실제 받은 ZIP의 CRC와 내부 APK SHA-256을 원본과 대조했다. [설치 ZIP](https://github.com/seokhr1234/donghaeng-gill/archive/refs/tags/android-demo-v1.0.6-download.zip) · [Release](https://github.com/seokhr1234/donghaeng-gill/releases/tag/android-demo-v1.0.6)
