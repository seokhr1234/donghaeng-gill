# 서울 25개 구 휴식 장소 자료

2026-11-20 KST에 서울시 공개 목록과 OSM 원본을 확인했다. 개별 행은 등록 또는 지도 표기이며, 현장의 개방 여부·의자 수·휠체어 진입·보행망 연결을 확인한 곳은 0건이다.

## 수집 결과

| 자료 | 건수 | 데이터 기준 및 수집 | 사용 범위 |
| --- | ---: | --- | --- |
| OSM 벤치 | 2,538 | Geofabrik `261119` PBF. 복제 기준 11월 20일 06:22:20 KST, 수집 11월 20일 KST | `amenity=bench` 객체 |
| OSM 좌석 표시 시설 | 1,509 | 같은 PBF | `bench=yes` 또는 `leisure=picnic_table`. 시설 기준 위치이며 개별 의자 수 미확인 |
| OSM 쉼터 | 673 | 같은 PBF | `amenity=shelter`. 종류 미기재 316건. 실내·냉난방·착석·일반 출입 여부 미확인 |
| 서울시 무더위쉼터 OA-21065 | 4,092 | 2026년도. 기존 공식 CSV 수집 11월 5일 KST, 이번 비교 11월 20일 KST | 시설 기준점. 등록 운영시간과 시설 구분 확인 가능 |
| 강북구 한파쉼터 | 96 | 2026~2027년 운영 명단. 11월 20일 KST 원본 확보 | 주소, 시설 구분, 요일별 운영시간. 좌표는 원본에 없음 |
| 서울 공공도서관 | 214 | 국가도서관통계시스템 2025년 실적. 11월 20일 KST 수집 | 25개 구 주소와 좌표, 운영시간 209건, 정기 휴관일 211건. 쉼터 지정·개별 좌석 확인은 별도 |

- [OSM·무더위쉼터 25개 구별 집계 CSV](derived/district-counts.csv)
- [OSM 목록 CSV](derived/osm-rest.csv) · [지도용 GeoJSON](derived/osm-rest.geojson) · [서울시·자치구 경계 GeoJSON](derived/osm-boundaries.geojson)
- [서울시 무더위쉼터 CSV](derived/seoul-cooling-shelters.csv) · [지도용 GeoJSON](derived/seoul-cooling-shelters.geojson) · [기존 서울시 원본 CSV](../round4-2026-11-05/raw/seoul-shelter-csv/response.bin)
- [기존 자치구 공식 휴식시설 CSV](derived/official-local-rest.csv)
- [강북구 한파쉼터 CSV](derived/gangbuk-cold-shelters.csv) · [공식 원본 PDF](raw/gangbuk-cold-shelters-2026-2027.pdf) · [자치구 한파 운영 공지 CSV](official-winter-schedules.csv)
- [서울 공공도서관 CSV](derived/seoul-public-libraries-2025.csv) · [지도용 GeoJSON](derived/seoul-public-libraries-2025.geojson) · [조회 요청·자치구 집계·검증 JSON](derived/seoul-public-libraries-2025-summary.json)
- [수량과 대조 결과 JSON](derived/summary.json) · [OSM 객체 ID 대조 CSV](derived/osm-comparison.csv) · [출처·수집일·체크섬·요청 결과](sources.json)

서울시 자료와 OSM은 같은 장소를 각각 포함할 수 있다. 두 자료의 건수를 합쳐 고유 장소 수로 계산하지 않는다. OSM 좌표와 GeoJSON은 WGS84 경도·위도 순서다. OSM 노드는 등록 좌표를 사용했고, 선·면 객체는 서울 경계와 교차하는 도형 안에서 대표점을 계산했다. 구별 분류에는 동일 PBF의 서울시 relation `2297418`과 자치구 경계를 사용했다. [Geofabrik 원본](https://download.geofabrik.de/asia/south-korea/south-korea-261119.osm.pbf) · [OpenStreetMap 저작권·ODbL 안내](https://www.openstreetmap.org/copyright)

서울시 원본의 GPS 열과 EPSG:5186 XY를 비교했고, 4,092건 모두 두 좌표의 축별 차이가 0.00005도 이하였다. 구 집계는 공식 주소를 따랐다. 수명산SK뷰아파트경로당(사립) 1건은 주소의 양천구와 좌표상의 강서구가 달라 자료에 두 값을 함께 보존했다. [서울시 무더위쉼터 OA-21065](https://data.seoul.go.kr/dataList/OA-21065/S/1/datasetView.do)

자치구 공식 자료는 10월 29일 수집해 기존 앱 파일에 포함된 450건이다. 의자·벤치 등이 명시된 6개 구의 공원 213곳, 강남구 벤치 설치 주소 15곳, 구로구 안양천 벤치 설치 지점 16곳, 성동구 스마트쉼터·냉온열의자 시설 206곳을 모았다. 같은 CSV에 원본 기준일과 좌표 종류를 기록했다. 공원·주소·정류장 기준 좌표의 개별 의자 위치 및 개수는 미확인이다. [전국도시공원 표준데이터](https://www.data.go.kr/data/15012890/standard.do) · [강남구 벤치 설치 현황](https://www.data.go.kr/data/15127620/fileData.do) · [구로구 안양천 주요 시설물](https://map.seoul.go.kr/smgis2/seoulMap?theme_id=1663564614080) · [스마트 성동지도](https://map.sd.go.kr/sdmap3/sMap.jsp)

공공도서관 원본은 별도 문화체육관광부 통계 시스템에서 받았다. 응답에 좌표계 이름이 명시돼 있지 않아 수치가 경도·위도 형식이고 214건 모두 원본에 기재된 자치구 경계 안에 드는지 확인했다. 같은 좌표를 공유하는 서로 다른 시설 ID 2쌍을 보존했다. 원본 응답의 검수 담당자 항목을 제외하고 공개 시설 필드와 출처를 저장했다. 데이터 재배포 조건은 조회 페이지에서 확인하지 못했다. [문화체육관광부 국가도서관통계시스템](https://www.libsta.go.kr/libsta/statistics/public/stat)

## 운영시간과 현재 개방

- 무더위쉼터 4,092건 모두 기본 운영 요일·시작·종료 시간이 있다. 연장 운영 `Y` 732건 중 718건, 추가 운영 `Y` 974건 중 973건에 유효한 요일·시간이 모두 있다. 기본·연장·추가 운영 원문을 CSV와 GeoJSON 양쪽에 보존했다.
- 현 앱의 월곡 후보 로직은 공식 운영시간 밖이거나 운영시간 근거가 충돌하는 쉼터를 자동 경유에서 제외한다. 기존 자료의 운영시간 근거 충돌 2건을 새 목록에서도 표시했다. OSM은 4,720건 중 `opening_hours` 태그가 4건에 있다. [앱 운영시간 판단](../../../donghaeng-nav/dist/engine.js#L71) · [공식 근거 충돌 기록](../round4-2026-11-05/README.md)
- 서울시는 2025년 변경에서 무더위쉼터의 계절 운영 시작일·종료일을 공개 컬럼에서 뺐다. 2026년 11월 18일자 공지의 12월 2일 제외 예정 항목에도 요일·시간은 포함되지 않았다. 2026년 11월 20일 현재 개방 여부와 각 시설 이용 자격은 별도 확인이 필요하다. [서울시 데이터소식의 2025년 변경 기록](https://data.seoul.go.kr/dataList/OA-22807/S/1/datasetView.do) · [2026년 11월 18일 공지](https://data.seoul.go.kr/together/notice/datasetNoticeView.do?bbsCd=10008&ditcCd=&pageIndex=1&seq=552ad1ea807ba3f76993094832133b55)

## 기존 지도 대조

- 무더위쉼터는 기존 앱 파일의 4,092건과 명칭·도로명주소·좌표로 모두 대응했고 내보낸 공식 필드 값도 모두 같았다. 이번 조사에서 서울시 포털의 11월 20일 갱신 표기를 확인했고, 해당 버전의 전체 CSV 다운로드 요청은 HTTP 503이었다.
- 기존 OSM 지도와 비교할 때 쉼터는 당시 기준인 `gazebo`와 `picnic_shelter`만 비교했다. 기존 4,054개 객체와 새 4,395개 객체의 ID를 대조한 결과 공통 4,033개, 이번 원본에만 362개, 이전 지도에만 21개였고 공통 중 73개의 태그가 달랐다. 두 자료에서 집계 대상이 달라진 객체는 `osm-comparison.csv`의 현재·이전 분류를 참고한다. ID 차이는 설치·철거의 현장 증거로 사용하지 않는다.

## 원본 확보 상태

| 추가 공식 출처 | 확인 결과 |
| --- | --- |
| [서울시 한파쉼터 OA-21066](https://data.seoul.go.kr/dataList/OA-21066/S/1/datasetView.do) | 포털의 11월 20일 갱신 표기와 주소·운영시간·GRS80 중부원점 XY 제공 안내 확인. 전체 CSV와 [서울안전누리 시설 지도](https://safecity.seoul.go.kr/distFclt/cfMapDs/cfMapDs.page?layer=coldShelter&menuId=MENU_SSNS_000176&type=heat&upMenuId=MENU_SSNS_000012) 직접 요청은 HTTP 503 |
| [서울시 주요 공원현황 OA-394](https://data.seoul.go.kr/dataList/OA-394/A/1/datasetView.do) | 2026년 하반기 파일과 9월 23일 갱신 표기 확인. 시트 CSV 요청은 HTTP 503 |
| [서울시 공공도서관 현황 OA-15480](https://data.seoul.go.kr/dataList/OA-15480/S/1/datasetView.do) | 11월 18일 갱신 표기 및 도서관 운영시간·휴관일 항목 확인. 시트 CSV 요청은 HTTP 503 |
| [전국무더위쉼터 표준데이터](https://www.data.go.kr/data/15013199/standard.do) · [전국도시공원 표준데이터](https://www.data.go.kr/data/15012890/standard.do) | 대체 전국 CSV 다운로드 경로도 HTTP 503 |

한파쉼터는 강북구가 공지한 시설군별 시간과 시설별 명단 96곳, 강동·금천·중구가 발표한 지정 규모를 보관했다. 강북구 웹매거진의 PDF 링크는 HTTP 403이었고, 강북구의 다른 공식 게시물에서 2쪽짜리 PDF를 확보했다. [서울시 겨울철 종합대책](https://scpm.seoul.go.kr/seoul-policy/evt0323) · [강북구 PDF 게시물](https://m.blog.naver.com/gangbuk_official/224475389845) · [강동구 안내](https://culture.gangdong.go.kr/web/newportal/bbs/b_133) · [금천구 보도자료](https://www.geumcheon.go.kr/portal/selectBbsNttView.do?bbsNo=8&key=297&nttNo=271818) · [중구 보도자료](https://www.junggu.seoul.kr/content.do?cid=148973239&cmsid=14390&mode=view)

강북구 96건은 13개 동에 걸쳐 있다. 원본 PDF는 공공시설 30건, 특정계층이용시설 65건, 생활밀착민간시설 1건을 분류한다. 연번·주소 96건과 시간 범위 103개를 PDF 원문과 대조했다. 강북웰빙스포츠센터는 PDF의 주말 09:00~18:00와 공지 본문의 토요일 09:00~17:00가 다르다. 두 값을 각 자료에 보존했다. [강북구 웹매거진 공지](https://www.snsgangbuk.com/sub/notice.html?type=view&bsNo=3404&page=1)

## 재생성과 검증

프로젝트 루트에서 OSM과 무더위쉼터 정리에 Python의 `osmium`, `shapely`, `pyproj`를 사용한다. 원본 PBF SHA-256은 [출처 기록](sources.json)에 있다.

```bash
dir=research/accessibility/seoul-rest-2026-11-20
python "$dir/extract_osm.py" /path/to/south-korea-261119.osm.pbf "$dir/derived" --retrieved-date 2026-11-20
python "$dir/summarize.py" research/accessibility/round4-2026-11-05/raw/seoul-shelter-csv/response.bin \
  donghaeng-nav/dist/data/accessibility/seoul/seoul-facilities.geojson "$dir/derived" \
  --cooling-retrieved-date 2026-11-05
```

도서관 조회 URL은 [조회 기록](derived/seoul-public-libraries-2025-summary.json)의 `request.url`에 있다. 받은 JSON은 `normalize_libraries.py`에 원본, 경계 GeoJSON, 출력 폴더, `--retrieved-date`를 지정해 처리한다. 강북구 PDF는 `pdfplumber`를 설치한 Python에서 `extract_gangbuk.py`에 원본 PDF, 출력 CSV, `--retrieved-date`를 지정한다.

서울시와 25개 자치구 경계의 유효성, 서울 경계 내부 좌표, 목록별 ID 중복, CSV와 GeoJSON 간 ID·행 수, 구 합계, 기존 공식 값 대조를 검증했다. 연구 결과는 별도 폴더에 저장했다.
