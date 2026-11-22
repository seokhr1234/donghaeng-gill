# 청주오스코 주변 경사 자료

2026-11-22(KST) 조사. 범위는 청주오스코 공식 대표점(경도 127.335363, 위도 36.6267203)과 오송역·호수공원 일대다. 보도 종단 경사·횡단 경사·경사로를 현장에서 측정한 공개 원본은 찾지 못했다.

## 환경부 5m 표고모형 기반 경사 등급

국토환경성평가지도는 2022년 제작한 국토지리정보원 5m 표고모형을 경사 분석에 사용한다고 안내한다. 공개 지점 분석을 실제 호출해 다섯 곳 모두 **5도 미만** 범주의 응답을 받았다. 각 지점의 좌표 출처, 좌표 역할, 수집 시각(KST), 요청 좌표와 응답 해시를 기록했다. [공식 지점 분석](https://webgis.neins.go.kr/map.do) · [수집 결과](neins-point-slope-classes.json)

| 조회 지점 | 좌표 역할 | 지형 경사 등급 |
| --- | --- | --- |
| 청주오스코 | 공식 안내 대표점 | 5도 미만 |
| 오송역 | OSM 철도역 대표점 | 5도 미만 |
| 오송역 8번 출구 | OSM 출입구 등록점 | 5도 미만 |
| 오송역8(517번) | OSM 버스정류장 등록점 | 5도 미만 |
| 오송호수공원 | 한국관광공사 지도 대표점 | 5도 미만 |

원 좌표는 경도·위도 EPSG:4326이며 조회는 EPSG:3857로 변환했다. 5도는 경사율 약 8.75%에 해당한다. 응답은 정확한 기울기나 이동 방향을 제공하지 않는다. 점 사이의 보행로, 턱과 진입로의 실제 경사는 미확인이다. 베타의 **시설·지도 → 조사 지도 → 오스코 주변 지형 경사 참고**에 등급만 표시한다.

## 원본과 대조

- **OSM**. 2026-11-20 21:21:21Z 스냅샷(2026-11-21 06:21:21 KST)을 11월 21일 수집했다. 오스코 대표점 기준 3km의 보행 관련 도형 132개, 도로 문맥 1,399개, 횡단·출입 59개 모두 `incline` 태그가 없다. 층이 겹치거나 객체가 여러 층에 포함될 수 있다. 더 넓은 조사 사각형의 도로 문맥에는 방향 표기 44건과 `0%`·`-0%` 표기 각 1건이 있다. [OSM 스냅샷 출처와 범위](../osco-seoul-2026-11-21/README.md) · [태그 대조 결과](slope-audit.json)
- **Copernicus GLO-30**. 원본 타일 49,583,060바이트를 11월 22일 다시 받아 기존 SHA-256과 일치함을 확인했다. EPSG:4326의 원본 절취본을 EPSG:5186 30m 격자로 보간한 뒤, 3×3 셀의 Horn 기울기를 경사율(%)로 계산했다. 제품의 높이 기준은 EGM2008이다. 반경 1km 3,494셀의 중앙값은 1.74%, 3km 31,414셀의 중앙값은 3.44%다. 픽셀은 건물과 식생을 포함하는 지표면 모델이며 보행로가 아닌 주변 지형 전체도 포함한다. [Copernicus 데이터](https://registry.opendata.aws/copernicus-dem/) · [경사율 GeoTIFF](osco-copernicus-surface-slope-percent.tif) · [검증·재현 정보](slope-audit.json)
- **국토지리정보원**. 1m·5m 수치표고모형 구축 규정과 원본 카탈로그, 1:1,000 수치지도 카탈로그를 확인했다. 국토정보플랫폼의 실제 자료 요청은 HTTP 503을 반환해 해당 지역 원본과 도엽별 측량 시점은 확보하지 못했다. 환경부의 5m 지점 등급 조회 결과는 별도로 보존했다. [표고모형 원본 카탈로그](https://www.data.go.kr/data/15059920/fileData.do) · [수치지도 V2.0](https://www.data.go.kr/data/15059719/fileData.do)
- **행사장 운영사**. 오송역 8번 출구부터 도보 약 10분으로 안내한다. 이용 안내의 시간·좌표와 구간 경사나 무단차 통행 확인을 구분한다. [청주오스코 교통안내](https://osco.or.kr/traffic/traffic_guidance/)

`/usr/bin/python3 derive.py`는 기존 OSM 자료 해시를 확인하고 참고 GeoTIFF를 생성한다. GDAL과 NumPy가 필요하다. `/usr/bin/python3 collect-neins.py`는 공개 조회 응답을 다시 수집하며 수집 일시와 등급을 갱신한다. 경로망에 적용한 새 경사값은 0건이다.

Produced using Copernicus WorldDEM-30 © DLR e.V. 2010–2014 and © Airbus Defence and Space GmbH 2014–2018 provided under COPERNICUS by the European Union and ESA; all rights reserved. OSM © OpenStreetMap contributors · [ODbL](https://www.openstreetmap.org/copyright)
