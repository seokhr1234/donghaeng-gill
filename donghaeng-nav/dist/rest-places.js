(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.DonghaengRestPlaces = factory();
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  const ASSET = 'bundled-seoul-rest-update';
  const REST_KINDS = new Set(['bench', 'seating', 'shelter']);
  const OPENING_CATEGORIES = [['기본운영', '기본'], ['연장운영', '연장'], ['추가운영', '추가']];

  function openingHours(properties, tags) {
    const fields = properties.official_fields;
    if (!fields || !Object.hasOwn(fields, '기본운영_요일')) {
      return properties.opening_hours || tags.opening_hours;
    }
    return OPENING_CATEGORIES.flatMap(([key, label]) => {
      if (key !== '기본운영' && fields[key + '_운영여부'] !== 'Y') return [];
      const days = fields[key + '_요일'];
      const start = fields[key + '_시작시간'];
      const end = fields[key + '_종료시간'];
      const schedule = days && start && end && start !== end ? days + ' ' + start + '–' + end : '상세 시간 미확인';
      return [label + ' ' + schedule];
    }).join('\n');
  }

  function supplement(update) {
    if (update?.version !== 1 || update.routing_eligible !== false || update.field_verified !== false ||
        !Array.isArray(update.osm) || !Array.isArray(update.libraries) || !Array.isArray(update.coldShelters) ||
        !Array.isArray(update.coldShelterPeriod) || update.coldShelterPeriod.length !== 2) {
      throw Error('휴식 시설 자료 형식을 확인해 주세요.');
    }
    const osm = update.osm.map(row => {
      const tags = row.tags;
      return feature(row.coordinate, {
        id: 'osm:' + row.id, osm_id: row.id, kind: row.kind, district: row.district,
        name: tags['name:ko'] || tags.name || '',
        source: 'OpenStreetMap / Geofabrik',
        source_url: 'https://www.openstreetmap.org/' + row.id,
        source_snapshot: update.osmSnapshotLabel,
        retrieved_date: update.retrievedDate, last_osm_edit: row.edited,
        osm_tags: tags, license: 'ODbL-1.0',
        coordinate_role: row.id.startsWith('node/') ? 'mapped_point' : 'mapped_geometry_representative_point',
        ...(row.kind === 'shelter' ? {notice: 'OSM 등록 쉼터예요. 좌석·실내 여부·개방 상태는 미확인입니다.'} : {}),
      });
    });
    const libraries = update.libraries.map(row => feature(row.coordinate, {
      id: 'library:' + row.id, kind: 'library', district: row.district, name: row.name, address: row.address,
      opening_hours: row.hours || '미등록', regular_closure: row.regularClosure || '미등록',
      source: '문화체육관광부 국가도서관통계시스템', source_url: update.librarySource,
      source_snapshot: update.libraryYear + '년 통계', retrieved_date: update.retrievedDate,
      coordinate_role: 'facility_reference', license: '원본 조회 페이지 참조',
      notice: '공공도서관 기준 위치예요. 열람 공간·좌석·출입구와 현재 이용 여부는 방문 전 확인하세요.',
    }));
    return {data: {type: 'FeatureCollection', features: [...osm, ...libraries]}, directory: update.coldShelters,
      period: update.coldShelterPeriod, directorySource: update.coldShelterSource, retrievedDate: update.retrievedDate};
  }

  function feature(coordinates, properties) {
    return {type: 'Feature', geometry: {type: 'Point', coordinates},
      properties: {...properties, operational_status: 'unknown', field_verified: false, routing_eligible: false}};
  }

  function merge(base, supplement, osmId, normalize) {
    const added = normalize([{data: supplement.data, file: 'seoul-rest-update.json'}]);
    if (added.stats.invalid || added.stats.unclassified || added.stats.duplicates ||
        added.features.length !== supplement.data.features.length) throw Error('휴식 시설 좌표·식별자를 확인해 주세요.');
    const current = new Map(added.features.map(row => [row.id, row]));
    const combined = base.features.map(row => {
      if (!REST_KINDS.has(row.kind)) {
        current.delete(row.id);
        return row;
      }
      if (!osmId(row.properties)) return row;
      const next = current.get(row.id);
      if (next) {
        current.delete(row.id);
        return next;
      }
      return {...row, properties: {...row.properties,
        notice: '이전 OSM 자료의 등록 위치예요. 최신 서울 휴식 자료에서 같은 객체를 확인하지 못했어요.'}};
    });
    combined.push(...current.values());
    const counts = {...base.counts, ...added.counts};
    for (const kind of Object.keys(counts)) counts[kind] = 0;
    for (const row of combined) counts[row.kind]++;
    return {...base, features: combined, counts};
  }

  return {ASSET, openingHours, supplement, merge};
});
