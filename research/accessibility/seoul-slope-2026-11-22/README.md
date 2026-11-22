# 서울 시연용 경사 자료 조사

2026-11-22(KST). 서울 25개 자치구를 대상으로 보도 실측, 이동경로 등급, 지형 표고와 OSM 등록을 대조했다. 서울 전역 보도의 종단·횡단 경사가 모두 실측된 공개 원본은 확보하지 못했다. **가장 넓은 경로 등급 자료는 서울시 GNSS 자료, 공개 실측 수치는 3개 자치구 514개 표본**이다.

## 확보한 자료

| 자료 | 확인한 범위와 값 | 출처와 결과 |
| --- | --- | --- |
| Seoul Sidewalk Accessibility Image Dataset | 514개 실측 표본. 서대문 297개, 관악 118개, 강서 99개. 종단·횡단 경사(°)와 폭(m)이 있다. | [Zenodo 원본](https://doi.org/10.5281/zenodo.22908353) · [실측 CSV](measured/summary_attributes.csv) · [검수](measured/verified-measurements.json) |
| 서울시 GNSS 보행약자 안전 이동경로 | 25개 구 선형 등급 12,205건, 좌표열의 정·역방향 중복을 합치면 7,987개. 5개 이동 유형별 등급의 경계가 다름. | [스마트서울맵 원본 지도](https://map.seoul.go.kr/smgis2/short/6OkfD) · [구별·등급별 감사](municipal/gnss-route-layer-audit.json) |
| 서울시 OA-22241 표고점·등고선 | 2023년 수치지형도 기반 SHP 두 ZIP 재확보. 각각 25개 구와 교차. 수평 EPSG:5174. | [공식 파일](https://data.seoul.go.kr/dataList/OA-22241/F/1/datasetView.do) · [공간 감사](municipal/oa22241-25-district-audit.json) |
| Copernicus GLO-30 | 원본 2타일 해시 대조. 서울 행정경계 673,674셀 30m DSM 지표면에서 경사율(%)을 산출. | [공식 원천](https://registry.opendata.aws/copernicus-dem/) · [GeoTIFF](seoul-copernicus-surface-grade-pct-30m.tif) · [25구 CSV](copernicus-surface-grade-districts.csv) |
| 서울 OSM | 행정경계와 교차하는 보행 선형 47,328개 중 종단 수치 표기 95개. 전체 도로 선형 128,603개 중 수치 표기 207개. | [Geofabrik 원본](https://download.geofabrik.de/asia/south-korea/south-korea-261120.osm.pbf) · [25구 CSV](osm/osm-seoul-incline-districts.csv) · [GeoJSON.gz](osm/osm-seoul-incline-tagged.geojson.gz) |
| 환경부 국토환경성평가지도 | 2022년 5m DEM에서 계산한 각도 등급. 서울 시험점 7곳 응답 확인. | [공식 지도](https://webgis.neins.go.kr/map.do) · [등급·좌표 기록](national/neins-seoul-sample.json) |
| 서울 S-MAP | 공개 WMS 수치 표고 5점. 월곡·시청·남산·여의도·잠실. | [공식 가이드](https://smap.seoul.go.kr/guide/guide.html) · [WMS·WCS 조사](municipal/smap-2025-terrain-audit.json) |
| 은평구 봉산 이동약자 편의시설 지도 | 지도 점 627개 중 의자·이정표·전망대 92개에 0–6의 경사 원문. 단위·측정법 미확인. 두 숲길 선형 확인. | [은평구 지도](https://map.seoul.go.kr/smgis/webs/main/main.do?mode=seoulMapSearch&menuType=cityLife&themeId=1750212969170) · [필드 감사](municipal/official-service-context.json) |
| 서울시 보행자 출입구 OA-21699 | 출입구 16,786점. 경사로 설치 1,856점, 5도 이하 접근 경사 분류 603점, 각도 또는 경사율을 적은 비고 41행. | [공식 SHP](https://data.seoul.go.kr/dataList/OA-21699/S/1/datasetView.do) · [공간·필드 검수](measured/entrance-district-audit.json) |

## 보도 실측과 경로 등급

- **보도 실측**은 2026년 7월 7일·8일·10일·11일 조사자가 기기로 측정했다. 종단 -9.3°~11.8°, 횡단 -9.7°~8.0°. 원본의 514행에 513개 좌표쌍이 있다. 원본에 CRS 코드가 없어 경위도로 해석해 기존 OSM 구 경계와 대조했다. 논문 표의 일부 자치구명과 공개 좌표가 속한 구가 달라, 이 보고서는 좌표로 판정한 구를 기록했다. CC0 원본을 보존했다. [측정 원문](https://arxiv.org/html/2609.17882v1#S4.T2) · [검수 보고](measured/README.md)
- **GNSS 스마트서울맵**의 공개 조회는 HTTP 200이다. 전체 응답은 30,722개 혼합 레코드이며, 그중 경로 길이와 경사 난이도를 포함한 유효 선형은 12,205건이다. 선형 중점으로 서울 25개 구를 대조했다. 수동 휠체어와 전동 휠체어의 최고 등급 하한이 각각 3°와 9°처럼 다르므로 색을 한 가지 경사율로 환산할 수 없다. 개별 측정일과 정확한 종단·횡단 경사 수치는 미제공이다. 재이용 조건이 확인되지 않아 연구 폴더에는 집계와 코드만 두고, 정규화 선형은 작업공간에 보존했다. [공식 지도](https://map.seoul.go.kr/smgis2/short/6OkfD) · [선형 감사](municipal/gnss-route-layer-audit.json)
- **같은 사업의 공개 엑셀**은 역·목적지 목록 608건이다. 0–5° 범주 512건, 5–7° 72건, 7–9° 21건, 9° 이상 3건이다. 행별 좌표열과 개별 실측값은 없으며 위의 웹 선형 집계와 분모가 다르다. [공식 엑셀](https://www.gangnam.go.kr/file/1/get/21f8716f-c46c-44c0-8a64-b948149465d4/download.do) · [엑셀 검수](municipal/official-context-audit.json)
- **창신2동 일대 OSM**에 종단·횡단 수치가 함께 등록된 선형 75개를 공개 API로 재조회했다. 73개는 2026년 10월 21–22일 변경 기록에 현장답사가 명시돼 있다. 개별 수치의 단위·기기·정확도·측량 원자료는 미확인이다. 서울 전체 보행 선형 수치 95개는 명시 39개(%), 1개(°), 단위 없는 55개로 구분했다. [대표 변경묶음](https://www.openstreetmap.org/changeset/190859854) · [전수 조사](osm/README-osm.md)
- **출입구와 편의시설**은 경사 수치 적용 구간 대신 점 위치와 설치 여부에 활용할 수 있다. 2022-11-23 출입구 원본의 603점은 정의서에 따른 분류이고, 41행은 각도·경사율을 언급한 자유서술이라 방향·측정법이 통일되지 않았다. 서울동행맵은 308개 역 반경 300m 현장조사를 공개했으며, 개별 경사 수치 원본의 다운로드는 확인되지 않았다. 서울교통공사 램프 위치 506행과 서울시 보도 통계도 경사 수치 필드가 없다. [서울동행맵](https://news.seoul.go.kr/traffic/archives/512126?listPage=1) · [역·출입구·시설 검수](measured/README.md)

## 지형 자료의 범위

- **OA-22241** 두 원본의 서울 경계 교차 수는 첫 파일 표고점 47,102개·등고선 8,281개, 둘째 파일 표고점 45,687개·등고선 8,511개다. 원본끼리 겹치므로 합산하지 않는다. 첫 파일에서 DBF의 HEIGHT와 NUME가 다른 표고점 219개를 발견했고 수직 기준은 미확인이다. 원자료 기준 2023년, 둘째 파일 목록 수정 2025-03-20, 재수집·검증 2026-11-22(KST)다. 공공누리 제1유형이다. 두 원본 ZIP은 작업공간 artifacts/seoul-slope-2026-11-22에 해시와 함께 보존했다. [서울시 자료 안내](https://data.seoul.go.kr/dataList/OA-22241/F/1/datasetView.do)
- **서울안전누리 길 단위 경사도**는 2024-03 연속수치지형도 등고선 기반 서울 전역 구간의 경사율 범례 8단계를 표시한다. 지도 본문과 WMS 1.3.0 PNG 호출 코드는 직접 확인했다. 설정 요청이 503을 반환해 전체 세그먼트 선형과 원시 수치 필드는 확보하지 못했다. 표시 좌표계 EPSG:5186이며 원자료 CRS는 미확인이다. [실제 응답한 지도](https://safecity.seoul.go.kr/distFclt/cfMapDs/cfMapDs.page?menuId=MENU_SSNS_000190) · [HTTP 기록](municipal/safecity-slope-layer-audit.json)
- **S-MAP**의 경사지도 레이어 이름은 seoul:seoul_1m_2025이며 화면 범례 단위는 m다. EPSG:5186으로 지점 표고를 받았으며 GetMap GeoTIFF의 밴드는 색상 팔레트다. WCS로 원표고 격자를 받지 못했고 측량일·수직 기준·원자료 재배포 조건은 미확인이다. [서울시 S-MAP](https://news.seoul.go.kr/gov/archives/528155?listPage=1) · [공개제한 공간정보 안내](https://opengov.seoul.go.kr/press/28013895)
- **국토지리정보원 1m·5m DEM과 서울 1:1,000 수치지도·브이월드 등고선/표고점**은 공식 목록을 검색했다. 해당 지역 도엽 원본 요청은 502/503 또는 연결 시간 초과였다. 1:1,000은 지도 축척이다. 환경부 5m 시험점에서는 남산·북악산 시험점 20–25도 미만, 나머지 다섯 점 5도 미만을 확인했다. 한강 수면 비교점도 5도 미만이다. [국가기관 원본·접근 기록](national/README.md)
- **Copernicus**는 EPSG:4326 및 EGM2008 표고를 EPSG:5186 30m 격자로 보간하고 Horn 3×3 경사율을 계산했다. 서울 지표면 중앙값 8.36%, 90백분위 34.13%다. 건물·식생·수면이 포함된 지표면이며 보행로 진행 방향이나 보도의 횡단 기울기를 나타내지 않는다. [서울 경사율 지도](seoul-surface-grade-overview.png) · [원본 해시와 계산 절차](copernicus-surface-grade-source.json)

## 동행길 시연

현재 서울 보행망은 2026-11-09 UTC OSM 스냅샷을 사용한다. 서울을 감싸는 직사각형 963,670구간 중 등록 수치 경사는 903구간(약 0.094%)에 있다. 앱 급경사 표시 79,682구간은 지형 추정 79,597개와 OSM 등록 85개로 구성된다. 최신 OSM의 서울 행정경계 연구 집계와는 분모가 다르다. [기존 앱 기준](app-baseline.json)

월곡 오프라인 시연에서는 기존 표고점 944개·등고선 191개로 21,553개 도로 구간의 참고 근거를 확인할 수 있다. 새 보도 실측과 GNSS는 별도 근거로 보존했다. 새 경사값 승격 0건, 보도면과 승강기 운영의 현장 검증 미실시다.

경사율 GeoTIFF와 구별 CSV는 derive-copernicus.py로 재현하고 overview PNG는 plot-surface-grade.py로 그린다. 하위 폴더에 공공 기관별 요청 주소, 기준일·수집일, 좌표계와 파일 무결성 기록을 보존했다. [Copernicus 데이터 조건](https://registry.opendata.aws/copernicus-dem/) · [OSM ODbL](https://www.openstreetmap.org/copyright)
