# 동행길 Android 시연 APK

2026-11-19 배포판 **1.0.6 (versionCode 7)**은 보행 경로의 접근 거리, 대략적인 GPS, 메뉴 복귀 버튼을 개선했습니다. 패키지는 `app.donghaeng.gill.demo`입니다. [변경과 검증](../docs/endpoint-approaches-2026-11-19.md) · [설치 ZIP](https://github.com/seokhr1234/donghaeng-gill/archive/refs/tags/android-demo-v1.0.6-download.zip)

2026-11-19 배포판 **1.0.5 (versionCode 6)**는 API 설정을 **더보기(⋯)**에서 엽니다. 패키지는 `app.donghaeng.gill.demo`입니다. [모바일 개선과 검증](../docs/mobile-layout-2026-11-19.md) · [Android 1.0.5 설치 ZIP](https://github.com/seokhr1234/donghaeng-gill/archive/refs/tags/android-demo-v1.0.5-download.zip)

2026-11-17 기록: **1.0.4/versionCode5**는 밤하늘 고대비, 컬러 지도 유지와 숫자 안쪽 사각 테두리 제거를 포함합니다. [정정·검사·게시](../docs/night-sky-2026-11-17.md). 최종 빌드에는 **API 설정 → Gemini API 키 입력·변경**과 대중교통 내장 키 상태/복원을 추가했습니다. [사용법·비밀 분리·검사](../docs/android-gemini-settings-2026-11-17.md). 개인 Gemini 키가 없으면 기존 서버를 사용합니다. 공개 배포판은 키를 내장하지 않으며 API 설정에서 ODsay·Gemini 키를 기기에 입력합니다. 키 포함 공개 업로드는 자동 승인 검토가 거부해 제외했습니다. [1.0.4 설치 ZIP](https://github.com/seokhr1234/donghaeng-gill/archive/refs/tags/android-demo-v1.0.4-download.zip)을 내려받아압축을풀고설치하세요. 아래1.0.3의 흑백 디자인 기록은 이전 상태입니다.

2026-11-17 최신: **1.0.3/versionCode4**에 고대비 버튼과 색상 외 지도 구분을 추가했습니다. [검사·설치 파일 게시 기록](../docs/high-contrast-2026-11-17.md). 기존1.0.2와 같은 패키지/서명/네이티브 키를 사용합니다. [설치ZIP](https://github.com/seokhr1234/aiaiaiaiaiaiaiai/archive/refs/tags/android-demo-v1.0.3-download.zip)을 내려받아 압축을 풀고 설치하세요. GitHub 로그인이 필요합니다.

공통 소스는 `../dist/`, 웹 공개판은 도보 전용이며 Android 자산 빌드만 대중교통을 활성화한다.
2026-11-17: **1.0.2/versionCode3**는 청주오스코 주변 지도·공식 안내·등록 지물을 포함하며 해당 지역으로 시작합니다. 키와 서명은 기존1.0.1 Release 설정을 유지합니다. [앱 연결·검사·게시 기록](../docs/osco-app-integration-2026-11-17.md). 청주 도보 계산은 미지원이며 네이티브 대중교통 참고 검색과 구분합니다. [설치용1.0.2 APK ZIP](https://github.com/seokhr1234/aiaiaiaiaiaiaiai/archive/refs/tags/android-demo-v1.0.2-download.zip)을 내려받아 압축을 풀고 설치하세요. 비공개 GitHub 로그인이 필요합니다.

패키지명: **app.donghaeng.gill.demo**, Android 7(API24) 이상, targetSdk36.

## 설치 후 사용

2026-11-15 디버그 APK는 키가 없으며, 오른쪽 위 **교통 키**에서 ODsay **Android용 키**를 입력한다.
2026-11-16의 1.0.1 Release APK는 사용자가 제공한 Android 키를 네이티브 빌드에 포함한다.
새 설치에서는 키를 다시 입력할 필요가 없으며 같은 버튼으로 교체/삭제할 수 있다.
ODsay 애플리케이션의 Android 플랫폼에 위 패키지명을 등록한다. Server 키의 IP 제한을 우회하지 않는다.
키는 네이티브 앱의 비공개 설정에 저장하며 JS/HTML/로그로 반환하지 않는다. 삭제 버튼으로 지울 수 있다.
1.0.1 키의 실제 공급자 샘플 검색은 빌드 환경에서 1회 성공했다. 실기기 설치·네이티브 통신·GPS 검사는 별도다.
1.0 디버그판과 1.0.1 Release판은 서명이 달라 이전 디버그판을 삭제해야 설치할 수 있다. 삭제하면 기기 내 앱 데이터도 지워진다.

ODsay 직접 요청은 Android 네이티브 통신부에서 수행하며 기기별 KST 일일20회·동시2개 제한을 둔다.
계정 전체 한도는 ODsay 설정에서 관리해야 한다. 조회 전 좌표 전송을 안내하며 자동 재시도는 없다.
기존 조건 정규화/후보·도보·전체 여정 검사를 그대로 재사용한다. 실측 경사/출입구/시간표/접근성 검증을
승격하지 않고, GPS 품질 필터는 기기 위치 소스만 네이티브로 교체한다.

서울 보행 계산·Gemini 해석 등은 기존 `https://donghaeng-gill.vercel.app`의 API를 사용한다.
ODsay 키는 Vercel로 보내지 않는다. 인터넷 연결이 필요하며 전체 기능 오프라인 APK가 아니다.

## 과거 비공개 키 포함 빌드 안내

현재 공개 빌드는 `key.properties`가 있어도 기본적으로 키를 APK에 포함하지 않습니다. 공개용은 `-PdonghaengEmbedOdsayKey=false`와 공개 APK 검사를 사용하며, ODsay/Gemini 키는 앱의 API 설정에서 입력합니다. 아래는 이전 비공개 빌드 설정 파일의 형식 기록입니다.

Git에 포함하지 않는 `key.properties`를 이 폴더에 만들고 다음 형식으로 입력한다.

```properties
ODSAY_ANDROID_KEY=발급받은_Android용_키
```

빈 키 예제는 `key.properties.example`이다. 실제 키를 채팅/공개 GitHub/웹 빌드에 넣지 않는다.
APK에 넣은 키는 추출 가능하며 시연용 키와 공급자 계정의 호출 한도를 사용한다.

## 재현 빌드

Node22+, JDK21, Android SDK36/build-tools36, Android Studio 또는 Android SDK가 필요하다.

```sh
npm ci --prefix donghaeng-nav/mobile
npm run sync --prefix donghaeng-nav/mobile
cd donghaeng-nav/mobile/android
./gradlew assembleDebug
```

SDK 경로는 Android Studio의 로컬 설정 또는 ANDROID_HOME에 둔다. local.properties/키/keystore와
생성된 www·Android public 자산·build는 추적하지 않는다. 생성 APK는
`android/app/build/outputs/apk/debug/app-debug.apk`다.
Android의 gzip 자산 이름 충돌 때문에 원본 JSON만 패키징하며 APK ZIP이 압축한다.
원래 dist의 JSON/gzip은 그대로 보존한다. 고정 IP 서버는 필요하지 않다.

## 서명된 Release 빌드

로컬에서 서명용 keystore를 생성하고 `signing.properties.example`을 `signing.properties`로 복사해
keystore 파일명·별칭·비밀번호를 설정한다. 둘 다 Git 제외 대상이며 업데이트 APK에는 동일한 서명키가 필요하다.
`storeFile`은 이 mobile 폴더를 기준으로 해석한다. 설정이 없으면 Gradle은 설치용 서명이 없는 APK를 만든다.

```sh
npm run sync --prefix donghaeng-nav/mobile
cd donghaeng-nav/mobile/android
./gradlew -PdonghaengEmbedOdsayKey=false assembleRelease
```

출력은 `android/app/build/outputs/apk/release/app-release.apk`다. 최신 버전1.0.4/versionCode5, 패키지는
`app.donghaeng.gill.demo`로 유지한다. 실제 키·서명 설정·keystore는 소스 커밋/로그에 넣지 않는다.
키가 포함된 APK의 GitHub Release 업로드는 저장소가 비공개인지 확인한 후 수행한다.
이번 작업과 게시 상태는 [Release 기록](../docs/android-release-2026-11-16.md)을 참고한다.

검증: `npm run prepare:web --prefix donghaeng-nav/mobile` 뒤 이 디렉터리에서
`node scripts/test-native-frontend.mjs`. OS 브리지는 모의이고 보행 API는 실제 보존 망을 사용한다.
서명·패키지 검사는 `docs/android-apk-build-results.json`, 화면/연결 검사는 `docs/android-demo-results.json`에 있다.
