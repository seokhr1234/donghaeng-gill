# 청주오스코에서 서울까지 보행·휴식·건물 자료

2026-11-21 KST에 청주오스코와 오송역 주변을 먼저 수집하고, 같은 기준으로 월곡역 주변과 서울 25개 구로 확대했다. 지도 도형은 등록 자료이며 현장 통행·좌석·출입·운영은 미확인이다. 조사 브랜치는 `research/osco-seoul-walk-2026-11-21`이다.

오스코 반경은 운영사 계열 갤러리 지도의 시설 대표점, 월곡 반경은 프로젝트의 월곡역 시연 기준점에서 잰다. 도형까지의 직선 거리를 EPSG:5186으로 계산해 1km와 3km를 집계했다. 오송역·행사장 핵심 사각형은 경도·위도 `[127.315,36.61,127.35,36.64]`, 이전 조사와 같은 광역 사각형은 `[127.28,36.59,127.39,36.67]`이다. 광역에는 세종 쪽 도형도 들어가며 서울 전역에는 서울시 경계와 교차하는 도형을 사용했다. [기존 청주 조사](../cheongju-osco-2026-11-16/README.md) · [실제 OSM 서울 경계 대조](seoul/osm/seoul-boundary-check.json)

## 청주오스코

### 등록 보행로와 주변 시설

| OSM 등록 항목 | 1km | 3km | 광역 사각형 |
| --- | ---: | ---: | ---: |
| 보행 관련 도형 | 15 | 132 | 2,383 |
| 건물·건물 부분 면 | 466 | 1,112 | 4,700 |
| 휴식 참고 객체 | 33 | 120 | 415 |
| 횡단·진입·차단물 등 접근 관련 객체 | 6 | 59 | 1,787 |
| 정류장·역 등 교통 등록 객체 | 10 | 49 | 156 |

청주오스코 3km 안의 보행 관련 도형 132개에는 보행로 82개, 경로 29개, 보행자 전용 공간 9개, 계단 6개, 보행 표기가 있는 자전거도로·서비스도로 6개가 있다. 포장 종류 표기는 21개에 있다. 폭·경사·휠체어 태그는 이 범위에서 비어 있다. 휴식 참고 객체 120개에는 공원 32개, 개별 벤치 표기 1개, 의자 있음 표기 17개, 그늘막 등 쉼터 있음 표기 19개가 포함된다. 같은 객체에 의자와 쉼터가 함께 표시될 수 있다. 운영시간 표기는 확인되지 않았다. 만수공원·새싹어린이공원·봉산공원 등은 공간 도형으로 남겼다. [OSM 상세 집계](osco/osm/summary.json)

- [보행로](osco/osm/osm-pedestrian.geojson.gz) · [도로](osco/osm/osm-road_context.geojson.gz) · [횡단·접속](osco/osm/osm-access.geojson.gz)
- [휴식시설·공원](osco/osm/osm-rest.geojson.gz) · [건물](osco/osm/osm-buildings.geojson.gz) · [역·정류장](osco/osm/osm-transit.geojson.gz) · [지원시설](osco/osm/osm-support.geojson.gz)

### 청주시 공개 GIS

23개 레이어에서 광역 유효 도형 **11,145개**, 핵심 유효 도형 **4,698개**를 확보했다. 원본은 EPSG:5186이며 열람용 GeoJSON은 WGS84 경도·위도다. 수집일은 11월 21일이다. 각 행의 등록·수정·설치 필드와 자료 전체 기준일은 구분한다. 이번 원본에서 전체 기준일, 측량 축척, 재배포 조건은 확인되지 않았다. [청주시 교통지리정보시스템](https://www.cjtgis.go.kr/map/mapMain.do) · [요청과 검증 기록](osco/municipal/municipal-review-summary.json)

| 중요한 항목 | 광역 | 핵심 |
| --- | ---: | ---: |
| 인도 | 1,518 | 614 |
| 횡단보도 | 1,085 | 438 |
| 도로면 | 936 | 465 |
| 신호등 | 2,190 | 983 |
| 점자블록 | 1,236 | 600 |
| 음향신호기 | 294 | 163 |
| 횡단보도 조명 | 335 | 136 |
| 승강장 | 259 | 68 |

- [23개 레이어 전체 집계](osco/municipal/municipal-layer-counts.csv) · [인도 GeoJSON](osco/municipal/municipal-derived/GT_A003_A.geojson) · [횡단보도 GeoJSON](osco/municipal/municipal-derived/GT_A004_A.geojson) · [공개 WFS 원본과 요청 기록 TAR.GZ](osco/municipal/wfs-originals.tar.gz)
- 공개 요청 49건을 기록했다. 인도 원본 1,557개 중 비유효 38개와 분석 사각형 밖 1개를 제외했다. 전체 비유효 도형 69개를 원본에 보존하고 검토용 도형에서 제외했다. 점자블록은 북동쪽 소구역 한 곳이 미확보이며, 보행등 보조장치 `GT_A112_P`는 서버에서 해당 유형을 제공하지 않았다. [실패·보류 내역](osco/municipal/municipal-review-summary.json)
- 같은 핵심 범위의 횡단보도 438개, 도로면 465개, 점자블록 600개, 음향신호기 163개 등은 11월 16일 수집본과 ID·도형이 일치했다. 이번에 처음 확보한 인도 폴리곤 614개는 등록된 면 도형이다. 같은 범위 OSM에는 `footway=sidewalk` 전용 표기가 0개였고, 횡단보도 선 9개와 점 1개 중 8개가 시 등록 횡단 도형에서 10m 이내였다. 거리 대조는 자료의 위치 차이를 살피는 데 사용했다. [같은 범위의 겹침 결과](osco/source-overlay.json)

### 건물 보강과 현장 우선 확인 지점

Overture의 2026-11-18.0 배포본에서 같은 광역 사각형의 건물 면 **11,903개**를 확보했다. OSM 계통 4,544개와 East Asian Building Vector Data 계통 7,359개를 원천 필드로 식별했다. 최신 OSM과 ID가 같은 4,528개를 확인했고, 비OSM 계통 중 7,245개는 최신 OSM 건물 면과 면적이 겹치지 않았다. Overture의 오스코 건물과 OSM `way/1423171859`는 같은 원천이다. 충북 공식 건물 SHP는 다운로드 서버 오류로 미확보다. [두 원천 대조 결과](osco/buildings/latest-source-comparison.json) · [Overture 건물 GeoJSON](osco/buildings/overture-buildings-study.geojson.gz) · [GeoParquet](osco/buildings/overture-buildings-study.parquet) · [Overture 이용조건](https://docs.overturemaps.org/attribution/) · [비OSM 원천](https://zenodo.org/records/8174931)

- 운영사는 **오송역 8번 출구에서 약 10분**으로 안내한다. OSM 철도역 대표점, 8번 출구 표기, 버스정류장 **오송역8 (517번)**은 서로 다른 객체다. 행사장 지도점은 건물 내부의 대표점이다. 최신 OSM의 등록 노드만으로 8번 출구→오스코, 오스코→오송호수공원 두 동선을 연결 확인하지 못했다. [운영사 교통안내](https://osco.or.kr/traffic/traffic_guidance/) · [기준점 원본](osco/anchors/source-review.json) · [동선 검토 결과](osco/corridor-review.json)
- 오송호수공원은 오스코 대표점에서 직선 약 1.19km다. 한국관광공사 안내에서 수변 데크·무단차 접근·상시 개방 표기를 확인했다. 공원 안내점과 오송역 인근 민간 카페 안내점을 기록했다. 민간 카페의 고객 외 이용과 공원 좌석·출입문 좌표는 미확인이다. [한국관광공사 열린관광공원 페이지](https://access.visitkorea.or.kr/ms/detail.do?cotId=b1136625-007e-4c71-b9c0-5b8800c41e66) · [운영·출입 근거](osco/rest-evidence/official-rest-context.json)
- 청주시 도시공원 파일과 관계 기관의 휴식시설 원본에 대한 실패 기록을 보관했다. 원본 확인이 가능한 장소와 OSM 휴식 표기를 근거로 정리했다. [공개 조회·결측 기록](osco/rest-evidence/official-rest-context.json) · [공공·민간 대표점 GeoJSON](osco/rest-evidence/kto-osong-reference-points.geojson)
- 현장 확인 순서는 8번 출구에서 지상 보도로 이어지는 지점, 오스코까지의 횡단부, 행사장 외곽 보도와 실제 출입문, 호수공원 진입부와 휴식 지점이다. 인도 폴리곤·건물 외곽으로 진입문, 무단차 연결, 유효폭, 경사를 자동 확정하지 않는다.

## 서울 확대

### 1단계 월곡

| 최신 OSM 등록 항목 | 월곡역 1km | 월곡역 3km |
| --- | ---: | ---: |
| 보행 관련 도형 | 265 | 3,182 |
| 건물·건물 부분 등록 객체 | 877 | 9,260 |
| 휴식 참고 객체 | 46 | 577 |
| 접속 관련 객체 | 329 | 4,544 |
| 역·정류장 등 교통 등록 객체 | 65 | 803 |

[월곡 보행로](seoul/osm/osm-pedestrian.geojson.gz) · [건물](seoul/osm/osm-buildings.geojson.gz) · [휴식 장소](seoul/osm/osm-rest.geojson.gz) · [세부 집계](seoul/osm/summary.json)

서울 공식 횡단보도 OA-22906에서 반경 1km **288개**, 3km **2,942개**를 추출했다. 레코드 기준일은 2026-03-20이다. OA-23081과 구·관리번호로 연결된 112개와 1,496개의 보행등 표기는 모두 일치했다. OA-23081의 XY 좌표계는 공식 확인이 안 돼 OA-22906 원본 경도·위도를 지도에 사용했다. 보도 통계 OA-22240에서 월곡로·종암로·화랑로 표기 49개 중 폭 값이 있는 37개를 보관했다. 주소·도로명 표로 기록된 폭이며 보도 도형이나 최소 유효폭 실측값으로 사용하지 않았다. 공식 파일 세 건은 11월 21일 재다운로드했고 10월 31일 보존본과 파일 해시가 같았다. [서울시 공식 횡단보도](https://data.seoul.go.kr/dataList/OA-22906/S/1/datasetView.do) · [월곡 횡단보도 GeoJSON](seoul/official/wolgok-official-crossings-3km.geojson.gz) · [보도 통계 CSV](seoul/official/wolgok-official-sidewalk-reference-no-coordinates.csv)

서울시 S-MAP 도로명주소 건물 `seoul:tl_spbd_buld`에서 3km 외접 사각형과 교차하는 70,879개를 모든 페이지에서 수집했다. 고유 ID 70,879개와 유효 도형을 확인했다. 월곡역 반경 1km에는 **4,678개**, 3km에는 **56,179개**가 걸친다. 공식 WFS의 원본 좌표계는 EPSG:5186이다. 레이어 전체 자료 기준일과 재배포 조건은 미확인이다. [서울 S-MAP](https://smap.seoul.go.kr/) · [수집·체크섬 보고](seoul/official/smap-local/smap-building-summary.json) · [3km 건물 GeoJSON](seoul/official/smap-local/wolgok-smap-buildings.geojson.gz) · [WFS 원본과 요청 기록](seoul/official/smap-local/wfs-originals.tar.gz)

별도 2021년 OA-15554 원본의 EPSG:5186 횡단보도 폴리곤에서 월곡 1km **285개**, 3km **2,767개**를 추출했다. 외접 사각형에서 비유효 24개를 보류했고 이 중 13개는 원본 SHP의 닫히지 않은 링이었다. 원본 ZIP의 다른 파일에는 교통안전시설물 부착대도 있다. [서울시 OA-15554](https://data.seoul.go.kr/dataList/OA-15554/S/1/datasetView.do) · [횡단보도 폴리곤](seoul/official/wolgok-2021-official-crossing-polygons.geojson.gz) · [원본 ZIP](seoul/official/raw/oa15554-crossing-facilities-2021.zip) · [원본과 파생 검증](seoul/official/oa15554-polygon-review.json)

기존 프로젝트 정밀지도 16도엽에서도 같은 두 원을 점검했다. 보도 선 610개와 798개, 건물 선 8,161개와 10,979개가 범위에 걸친다. 이 도형의 취득일과 범위는 신규 OSM 자료와 다르며 건물 선 수를 건물 수로 바꾸지 않는다. [공식 자료와 기존 정밀지도 검토](seoul/official/seoul-official-evidence.json)

동선 검토를 월곡으로 확대해 OSM 등록 월곡역 4번 출구와 월곡꿈그림도서관 대표점을 비교했다. 등록된 보행로에 한정한 선형은 약 410m이고 생활도로를 포함하면 약 389m다. 끝 연결 노드에서 도서관 대표점까지 13.1m는 이 길이에 포함되지 않는다. 이 검토는 OSM 원래 노드 연결만 사용하며, 계단·실내·교량·터널 등을 제외한 범위의 참고 결과다. [월곡 동선과 출입 참고점](seoul/corridor-review.geojson) · [검토 수치](seoul/corridor-review.json)

### 2단계 서울 25개 구

11월 21일 **06:21 KST 기준** OSM 원본에서 보행 관련 **48,281개**, 휴식 참고 **10,523개**, 건물 등록 **171,939개**를 추출했다. 건물 등록은 면 **171,576개**와 점 **363개**다. 구 경계를 건너는 개별 도형은 둘 이상의 구 집계에 포함될 수 있다. 서울 공식 횡단보도는 25개 구에서 유효한 원본 위치 **40,281개**를 확인했다. [서울 구별 OSM 집계](seoul/osm/seoul-citywide-summary.json) · [공식 횡단보도 구별 집계 CSV](seoul/official/crossing-counts-seoul.csv)

- [서울 전역 보행 GeoJSON](seoul/osm/seoul-citywide-pedestrian.geojson.gz) · [휴식 GeoJSON](seoul/osm/seoul-citywide-rest.geojson.gz) · [건물 GeoJSON](seoul/osm/seoul-citywide-buildings.geojson.gz)
- [OSM 25개 구 집계 CSV](seoul/osm/seoul-district-counts.csv)
- 서울시 공식 보행 네트워크 OA-21208은 코드표와 공개 API 샘플 5행을 확보했다. 샘플 응답의 서버 전체 행 수는 원본 확보량에 포함하지 않았다. [공식 보행 네트워크 카탈로그](https://data.seoul.go.kr/dataList/OA-21208/S/1/datasetView.do) · [보존한 공개 샘플](seoul/official/raw/raw-21208-sample.json)
- [기존 25개 구 무더위쉼터·국가도서관통계 자료](../seoul-rest-2026-11-20/README.md). 이 자료의 수집·운영 기준일이 오늘 새로 바뀌지는 않았다.

## 원본, 좌표계와 사용 범위

OSM 원본은 292,399,858바이트이며 Geofabrik 게시 MD5를 확인했다. 원좌표와 선형의 순서 있는 OSM 노드 참조를 보존했다. 오스코 핵심 범위에서 독립 OSM API로도 확인된 1,654개 객체는 버전·태그·좌표열·way 참조가 일치했다. 지리 좌표는 경도·위도(EPSG:4326), 거리 및 면적 대조는 EPSG:5186이다. 신규 경사값이나 검증된 연결로 승격한 항목은 없다. [Geofabrik 원본 PBF](https://download.geofabrik.de/asia/south-korea/south-korea-261120.osm.pbf) · [원본 해시와 수집 시각](osco/osm/summary.json) · [OpenStreetMap 저작권·ODbL](https://www.openstreetmap.org/copyright)

큰 국가 단위 원본은 배포 주소와 해시로 참조한다. 지역 편집용 `*.geojson.gz`는 압축을 풀면 GeoJSON을 읽을 수 있다. `review_corridors.py`, `compare_osco_sources.py`, `compare_buildings.py`는 수집 후 검토를 재현한다. 청주시와 서울시 S-MAP WFS 원본과 변환 도형은 로컬 연구용으로 보관했다. 현장 개방·보행 가능성 확인과 앱 경로 연결 단계에는 별도 검증이 필요하다. [OSM 무결성 검사](verification.json) · [공식 원본 체크섬·도형 검사](official-source-validation.json)

### 2026-11-22 앱 반영

**시설·지도 → 조사 지도**에서 청주오스코의 OSM 보행로·건물·휴식·편의시설과 서울 전역의 OSM 휴식 장소, 월곡역 3km의 보행로·건물 윤곽을 선택할 수 있습니다. 지도는 등록 원문의 도형·객체 식별자·태그를 유지합니다. 서울 전역 보행로·건물 대조 결과는 이 연구 폴더에서 확인할 수 있습니다. 지자체 재이용 조건 확인이 필요한 원본·도형과 일부 확인용 응답은 수집 환경에 보존합니다. 현장 통행·시설 운영 확인은 미실시입니다.
