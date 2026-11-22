# 서울 OSM 경사 등록 조사

2026-11-22에 Geofabrik 배포 상태와 MD5를 확인하고 한국 PBF 파일을 다시 내려받았다. 파일은 292,399,858바이트이며, 스냅샷 기준 시각은 2026-11-20 21:21:21 UTC(11-21 06:21:21 KST), 수집 완료 시각은 11-22 09:19:28 KST다. `latest`와 `261120`의 배포 MD5는 동일하고 `261121` 파일의 MD5 조회는 404를 반환했다. [배포 목록](https://download.geofabrik.de/asia/south-korea.html) · [원본 PBF](https://download.geofabrik.de/asia/south-korea-261120.osm.pbf) · [배포 시각](https://download.geofabrik.de/asia/south-korea-updates/state.txt)

SHA-256 `492ceebb946500fa54dd1b460b4ff923884dd9e673f65d3750e1d60122b85a8e`
배포 MD5 `85bf57c0652e9bb68e74e667e1f4fa13`

## 등록 경사 집계

이전 조사에서 확보한 서울시 OSM 행정경계와 교차하는 객체를 조사했다. 구 경계와 교차하는 선은 양쪽 구에서 집계될 수 있다. 원문 좌표는 EPSG:4326이며 현장 통행과 실측 여부는 확인되지 않았다. [서울 행정경계](https://www.openstreetmap.org/relation/2297418)

| 자료 범위 | 전체 | 수치 원문 | 방향만 | 크기 미상 태그 | 경사 태그 없음 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 이번 도로 선형 | 128,603 | 207 | 932 | 92 | 127,372 |
| 이번 보행 관련 선형 | 47,328 | 95 | 917 | 91 | 46,225 |
| 이번 보행 계열 선형에서 등록 계단 제외 | 39,251 | 87 | 103 | 50 | 39,011 |
| 이전 저장 보행 객체(면 포함) | 48,281 | 95 | 917 | 91 | 47,178 |

- 수치 원문 207개 중 명시적 퍼센트는 48개, 단위 없는 값은 158개, 도 단위는 1개다. 보행 관련 수치 95개는 각각 39개, 55개, 1개다. 방향만 표기한 `up`·`down`에는 기울기 크기가 없다. 크기 미상은 `yes` 원문이다. [OSM incline 태그 정의](https://wiki.openstreetmap.org/wiki/Key:incline)
- 보행 관련 수치가 있는 구는 25개 중 12개다. 관악구 39개, 송파구 18개, 종로구 17개 순이다. 도로 선형에 수치가 있는 구는 13개다.
- 이전 저장 보행 레이어의 선형은 47,318개다. 이번 판정과 10개 차이가 나며 차이는 경사 등록이 없는 항목으로 한정된다. 두 스캐너는 선·면 및 도로 클래스 판정이 다르며 원본 PBF는 같다. 수치와 방향, 크기 미상 등록 수는 이전 보행 레이어와 일치한다.
- 횡단경사 표기 `incline:across`가 75개 도로에 있다. 모두 종로구와 교차하며 그중 3개가 성북구에도 걸친다. 도로 분류는 서비스로 35개, 주거도로 24개, 보행로 14개, 계단 2개다. 75개 모두 횡단과 종단 태그에 단위 없는 수치가 있다. [횡단경사 키 등록 이력](https://taginfo.openstreetmap.org/keys/incline%3Aacross)
- Overpass로 당일 등록을 대조하는 과정에서 메인 서버가 406, 공개 미러가 시간 초과를 반환했다. 전국 PBF에 기반한 시군구 집계는 완료했다.

## 창신2동 횡단경사 등록 출처 대조

2026-11-22 09:23 KST에 공개 OSM API로 횡단경사 태그가 있는 75개 객체를 전량 다시 조회해 75개 모두 PBF의 종단·횡단 태그와 일치함을 확인했다. 73개 객체의 변경묶음은 2026-10-21~22 UTC에 창신2동 현장답사를 반영했다고 기록하며 출처에 현장조사, GPS 또는 항공영상을 적었다. 나머지는 직접 방문 기록 1개와 후속 수정 기록 1개다. 객체에는 별도 경사 측정 기기·측량일·정확도·단위·원자료가 명시되지 않았다. 창신2동의 기록은 현장답사 출처가 확인되는 커뮤니티 등록 참고 자료로 다룬다. [변경묶음 190859854](https://www.openstreetmap.org/changeset/190859854) · [190846150](https://www.openstreetmap.org/changeset/190846150) · [190843044](https://www.openstreetmap.org/changeset/190843044) · [190859593](https://www.openstreetmap.org/changeset/190859593) · [공개 API 대조 기록](osm-across-live-provenance.json)

## 현재 서울 도보 엔진과 비교

현재 엔진은 2026-11-09 21:22:17 UTC 스냅샷의 서울 포함 직사각형 등록망을 이용한다. 엔진에 보존된 176,600개 도로 객체 중 원문 수치 202개에서 200개 도로의 경사 값이 실제 연결망에 쓰인다. 길이와 원본 배열을 검증한 결과 963,670구간 중 903구간(0.0937%)에 숫자가 있으며, 등록 수치의 적용 거리는 전체 22,870.972km 중 16.681km(0.0729%)다. 방향만 표기된 2,715구간을 포함한 962,767구간에는 엔진에 쓰이는 수치 경사가 없다. 행정경계와 엔진 직사각형의 모집단은 서로 다르다. 현장 접근·노면을 새로 확인한 구간과 엔진에 승격한 수치 모두 0건이다.

## 파일

- [구별 CSV](osm-seoul-incline-districts.csv)
- [경사 태그 객체 GeoJSON gzip](osm-seoul-incline-tagged.geojson.gz) · [검사 JSON](osm-seoul-incline-summary.json)
- [재실행 스크립트](audit-osm-slopes.py). Python 패키지 `numpy`, `osmium`, `shapely`가 필요하다. 저장소 경로, PBF 경로, 배포 MD5 텍스트 경로, 출력 폴더를 차례대로 인자로 입력한다. [공개 OSM API 재조회 스크립트](check-across-live.py)는 산출 GeoJSON이 있는 폴더에서 실행한다.

© OpenStreetMap contributors, [ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/) · [OSM 저작권 및 표기](https://www.openstreetmap.org/copyright)
