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

## 최종 APK 검사와 게시 대기

커밋 `90192f716c6d2dbd89732391ea87b95763fb6e30`에서 `assembleRelease`를 완료했다. 일반 샌드박스에서는 Gradle의 소켓 초기화가 실패해 로컬 네트워크 권한으로 오프라인 재빌드했으며 빌드 자체는 통과했다.

- 파일: `donghaeng-android-demo-1.0.1.apk`, **16,851,545 bytes**
- SHA256: `e0088e808f467e79932044340550e1a44435ae2f50264de1f4089874216ed20f`
- 실제 Release 서명(v2)·ZIP CRC·패키지/버전/API24–36·비디버그 설정 통과.
- 새 Android 키는 네이티브DEX에만 있고 웹 자산·소스 커밋·빌드 로그에는 없다. key.properties/signing.properties/keystore는 APK 및 Git에 없다.
- 검사기의 aapt2 최소SDK 필드명(sdkVersion/minSdkVersion) 차이를 수정해 확인했으며 제품 코드는 변경하지 않았다. APK에는 VCS 메타데이터가 없고 빌드한 커밋은 별도 보고서에 기록했다.
- [검사 결과](android-release-apk-results-2026-11-16.json). 이전 디버그APK/검사 기록은 보존했다.

저장소PRIVATE 상태를 재확인한 뒤 [기존 Release 초안](https://github.com/seokhr1234/aiaiaiaiaiaiaiai/releases)을 만들었다. 태그명은 `android-demo-v1.0.1`이며 sourceCommit을 대상으로 한다. **첨부0개·미게시**다.

`gh release upload`와 공식 Bearer 인증 업로드는 모두 `uploads.github.com`에서 HTTP401을 반환했다. 핵심 API/소스 푸시는 성공한다. `api.github.com`의 같은 경로는 업로드를 지원하지 않아404였다. 연결된 GitHub 플러그인에도 Release 첨부 도구가 없다. 비밀 값이나 keystore를 다른 서비스·소스에 우회 업로드하지 않았다.

다음 작업은 기존 초안에 준비된 APK와 SHA256(선택: 빌드JSON)을 첨부하고 업로드본 해시를 확인한 뒤 게시하는 것이다. GitHub 로그인 UI에서 첨부하거나 업로드 호스트 인증을 복구한 연결로 재개해야 하며 새 Release를 중복 생성하지 않는다. 로컬 전달 파일은 `/workspace/artifacts/`에 있다. 이 단계는 **미완료**다.

웹main/운영 소스는 변경하지 않았고 Android 빌드 소스·문서만 새 브랜치에 반영한다. 실제 기기 설치·네이티브 호출·GPS·현장 통행은 미검증이다.
