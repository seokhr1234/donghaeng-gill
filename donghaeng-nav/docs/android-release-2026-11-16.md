# Android 시연 1.0.1 Release — 2026-11-16 KST

사용자 요청은 Android용 키를 APK에 포함하고 GitHub 저장소를 비공개로 전환한 뒤 Release에 APK를 게시하는 것이다.
처음 전달받은 키 대신 후속으로 지정한 Android용 키만 사용한다. 키 값은 이 문서·Git·JS·로그에 기록하지 않는다.

- 소스 브랜치: `release/walk-web-android-demo`
- 앱 패키지/ODsay 등록명: **`app.donghaeng.gill.demo`**
- 버전: **1.0.1**, versionCode **2**, Android **7(API24)** 이상, targetSdk **36**
- 웹 운영판의 대중교통 차단과 원본 연구·보행 자료는 유지한다.
- 키: 무시된 `mobile/key.properties` → 네이티브 BuildConfig. 새 설치에서는 별도 입력이 필요 없으며 기기 내 `교통 키`에서 교체·삭제할 수 있다.
- 서명: 무시된 `mobile/signing.properties`와 로컬 keystore로 `assembleRelease`를 실행한다. 동일 서명키를 보관해야 후속 APK로 업데이트할 수 있다.
- 이전 디버그1.0과 Release1.0.1은 서명이 달라 이전 앱을 삭제해야 설치할 수 있다. 삭제하면 앱의 기기 내 데이터도 지워진다.

## 실제 키와 게시 권한 확인

2026-11-16 빌드 환경에서 공개 장소(서울역–성북구청)의 대표 좌표를 사용한 ODsay HTTPS 검색1회가 HTTP200·후보21개로 성공했다.
실제 키·키가 포함된 URL·공급자 원본 응답은 저장하지 않았다. `android-key-provider-results-2026-11-16.json`에 비밀을 제외한 결과만 기록했다.
이는 공급자 인증·응답 검사이며 실기기 네이티브 호출/GPS/현장 통행 검증을 의미하지 않는다.

GitHub CLI는 인증되지만 저장소 설정 수정은 연결 앱의 관리 권한 부족으로403을 반환했다.
그 후 별도 `gh repo view` 조회에서 **PRIVATE**를 확인했다. Release 생성·키 포함 APK 업로드 직전에 다시 확인한다.
실제 APK·서명·게시 결과는 완료 후 아래에 추가한다.

## 호출 방식 근거

ODsay의 [SDK 종료 공지](https://lab.odsay.com/community/noticeView?seq=229)는 REST 호출로 전환하도록 안내한다.
[공식 관리자 답변](https://lab.odsay.com/community/boardView?seq=628)은 Android/iOS 키와 패키지 등록, 특수문자 인코딩을 설명한다.
현재 네이티브 HTTPS 구현은 키를1회 URL 인코딩하며 임의 패키지 헤더나 종료된 SDK를 추가하지 않는다.
사용자가 승인한 지정 기기 시연 방식으로 APK에 키를 포함한다. 비공개 저장소여도 APK에서 키를 추출할 수 있다는 한계는 유지한다.
