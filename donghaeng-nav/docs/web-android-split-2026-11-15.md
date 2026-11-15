# 도보 공개판과 Android 시연판 분리

2026-11-15 KST. 기준 main `d7b1361`, 새 브랜치 `release/walk-web-android-demo`.
사용자 요청으로 Vercel은 대중교통 없는 공개판, Android APK는 직접 교통 API를 쓰는 시연판이다.

- 웹: `dist/build-profile.js`의 web-walk. 도보3단계 질문, 대중교통 선택/확장 선택지 제외.
  `services/web-profile.mjs`가 Node/Vercel의 교통 검색·교통 도보 검토·여정 API를404로 차단한다.
  상태 API는 unavailable_in_web_build다. 키가 설정되어 있어도 업체를 호출하지 않는다.
- Android: 공통 dist를 별도 www로 복사해 android-demo 프로필과 네이티브 런타임을 번들한다.
  공통 ODsay 정규화·이동 조건·도보/전체 여정 검사 코드를 재사용한다. native plugin이 Android 키로
  직접 ODsay에 요청하고, 보행/AI 등은 기존 Vercel API를 사용한다. Android 플랫폼의 실제 인증은 미검증이다.
- 키: 사용자가 APK 내 키 포함을 명시적으로 선택했다. 로컬 key.properties의 빌드 주입을 지원하며,
  미제공 키는 만들어 넣지 않는다. 제공 APK에는 실제 키가 없고 설치 후 교통 키 대화창에 입력할 수 있다.
  공개 GitHub/JS/HTML/로그로 키를 내보내지 않는다. APK의 키 추출 가능성은 남는다.
- UI: 출발 검색 결과가 커져도 시설·지도 버튼이 가려지지 않도록 모바일 말풍선 최대 높이를 조정했다.
- 보존: 원본9개/gzip9개, research·기존 도시/검토/경사 자산과 경로/GPS 알고리즘은 그대로다.
  공통 실행HTML5개는 도보 공개판으로 갱신한다. APK에는 원본 JSON을 넣고 자체 ZIP 압축을 쓴다.

[Android 설정·키·재현 빌드](../mobile/README.md), [웹 검사](web-walk-results.json),
[단일 HTML](web-walk-bundle-results.json), [Android 연결 모의 검사](android-demo-results.json),
[실제 APK 빌드·서명](android-apk-build-results.json).

APK: app.donghaeng.gill.demo, minSdk24/targetSdk36, 디버그 서명. 현재 실제 Android 키/실기기 GPS·현장
검증은 하지 않았다. 화면·네이티브 브리지는 모의, 보행 계산은 보존한 실제 망이다. 공급자 실제 호출0건.
전체 여정/실시간 접근성·현장 검증의 기존 미완료를 완료로 바꾸지 않는다.

공개 운영 반영은 새 브랜치를 푸시하고 main의 예상 SHA를 확인한 뒤 이력을 보존해 반영한다.
별도 Vercel 프로젝트/도메인 설정은 변경하지 않고 Git 연결 배포를 사용한다. 배포 뒤 공개 URL의
도보 전용 화면과 교통 API 차단을 확인한다.
