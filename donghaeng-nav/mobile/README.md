# 동행길 Android 시연 APK

공통 소스는 `../dist/`, 웹 공개판은 도보 전용이며 Android 자산 빌드만 대중교통을 활성화한다.
패키지명: **app.donghaeng.gill.demo**, Android 7(API24) 이상, targetSdk36.

## 설치 후 사용

디버그 APK를 지정한 기기에 설치하고 오른쪽 위 **교통 키**에서 ODsay **Android용 키**를 입력한다.
ODsay 애플리케이션의 Android 플랫폼에 위 패키지명을 등록한다. Server 키의 IP 제한을 우회하지 않는다.
키는 네이티브 앱의 비공개 설정에 저장하며 JS/HTML/로그로 반환하지 않는다. 삭제 버튼으로 지울 수 있다.
제공한 APK에는 실제 키가 없다. 실제 인증·실기기 GPS는 사용자가 키를 설정한 기기에서 별도 검사해야 한다.

ODsay 직접 요청은 Android 네이티브 통신부에서 수행하며 기기별 KST 일일20회·동시2개 제한을 둔다.
계정 전체 한도는 ODsay 설정에서 관리해야 한다. 조회 전 좌표 전송을 안내하며 자동 재시도는 없다.
기존 조건 정규화/후보·도보·전체 여정 검사를 그대로 재사용한다. 실측 경사/출입구/시간표/접근성 검증을
승격하지 않고, GPS 품질 필터는 기기 위치 소스만 네이티브로 교체한다.

서울 보행 계산·Gemini 해석 등은 기존 `https://donghaeng-gill.vercel.app`의 API를 사용한다.
ODsay 키는 Vercel로 보내지 않는다. 인터넷 연결이 필요하며 전체 기능 오프라인 APK가 아니다.

## 실제 키를 빌드에 포함할 때

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

검증: `npm run prepare:web --prefix donghaeng-nav/mobile` 뒤 이 디렉터리에서
`node scripts/test-native-frontend.mjs`. OS 브리지는 모의이고 보행 API는 실제 보존 망을 사용한다.
서명·패키지 검사는 `docs/android-apk-build-results.json`, 화면/연결 검사는 `docs/android-demo-results.json`에 있다.
