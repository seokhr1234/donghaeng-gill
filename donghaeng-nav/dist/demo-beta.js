(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.DonghaengDemoBeta = factory();
})(globalThis, function () {
  'use strict';

  const kinds = ['bench', 'seating', 'shelter', 'library'];
  const availabilityNote = '시연에서는 운영시간·출입 제한·자료 확인 상태와 관계없이 개방으로 가정해요. 실제 개방·출입은 확인이 필요해요.';

  function places(features) {
    return features.flatMap(({id, kind, properties, geometry}) => {
      if (!kinds.includes(kind) || geometry?.type !== 'Point') return [];
      const ll = [geometry.coordinates[1], geometry.coordinates[0]];
      if (!ll.every(Number.isFinite)) return [];
      return [{
        id, kind: kind === 'library' ? 'shelter' : kind, ll,
        name: properties.name || ({bench: '등록 벤치', seating: '등록 의자 시설', shelter: '등록 쉼터'}[kind] || '공공도서관'),
        approximate: true,
        sourceUrl: properties.source_url,
        evidenceNotice: availabilityNote,
      }];
    });
  }

  function cityProfile(profile, relaxSlope = false) {
    return {
      ...profile, rest: false, restMinutes: null,
      ...(relaxSlope ? {demoIgnoreSlope: true, maxSlope: null, avoidSlope: false} : {}),
    };
  }

  function retryCityWithoutSlope(profile, status, code) {
    return status === 422 && (profile.avoidSlope || profile.maxSlope != null || profile.wheelchair) &&
      ['city_slope_evidence_required', 'city_endpoint_unresolved', 'city_no_connected_route'].includes(code);
  }

  function slopeNotes({registered, reference, unknown, relaxed}) {
    const notes = [];
    if (relaxed) notes.push('경사 조건으로 연결을 찾지 못해 경사 제한 없이 다시 계산했어요.');
    if (Number.isFinite(registered)) notes.push('등록 구간 최대 경사 ' + registered.toFixed(1) + '%');
    if (Number.isFinite(reference)) notes.push('지형 추정 구간 최대 경사 약 ' + reference.toFixed(1) + '%');
    if (unknown > 0) notes.push('경사 미확인 ' + Math.round(unknown).toLocaleString() + 'm · 확인된 구간의 수치와 구분해요.');
    return notes;
  }

  function nearbyRest(E, coords, candidates, profile) {
    if (!profile.rest || !coords?.length || !candidates.length) return null;
    const stride = Math.max(1, Math.ceil(coords.length / 72));
    const samples = coords.filter((_, i) => i % stride === 0 || i === coords.length - 1);
    let match = null;
    for (const place of candidates) {
      for (let i = 0; i < samples.length; i++) {
        const distance = E.distance(samples[i], place.ll);
        if (distance > 150) continue;
        const kindPenalty = profile.restKind === 'shelter' && place.kind !== 'shelter' ||
          profile.restKind === 'bench' && place.kind === 'shelter' ? 75 : 0;
        const score = distance + kindPenalty + 25 * Math.abs(i / Math.max(1, samples.length - 1) - .5);
        if (!match || score < match.score) match = {...place, distance, score};
      }
    }
    return match;
  }

  function localRoute(E, Endpoint, graph, from, to, profile, candidates) {
    const screened = graph.meta.buildingAudit?.filterGraph(graph) || graph;
    const working = {...screened, restPlaces: candidates, meta: {...screened.meta, buildingAudit: null}};
    const preferred = {...profile, restMinutes: null};
    let result;
    const askedForSlope = profile.avoidSlope || profile.maxSlope != null || profile.wheelchair;
    let relaxed = false;
    try {
      result = Endpoint.route(E, working, from, to, preferred);
      relaxed = result.assistancePreview;
    } catch (error) {
      if (!askedForSlope) throw error;
      relaxed = true;
    }
    if (relaxed) result = Endpoint.route(E, working, from, to, {
      ...preferred, demoIgnoreSlope: true, maxSlope: null, avoidSlope: false,
    });
    const notes = ['시연 전용 · 실제 이용과 안전은 현장에서 확인해 주세요.', ...slopeNotes({
      registered: result.maxKnownSlope, reference: result.maxEstimatedSlope, unknown: result.unknown, relaxed,
    })];
    if (profile.rest) notes.push('시설은 모두 개방으로 가정했어요. 운영시간·출입 제한·검증 상태와 요청한 휴식 간격은 적용하지 않았어요.');
    return {
      ...result, p: profile, label: '베타 시연 경로', selectionIneligible: true, demoNotes: notes,
      demoSlopeRelaxed: relaxed,
      demoNearbyRest: result.restStop ? null : nearbyRest(E, result.coords, candidates, profile),
    };
  }

  return {places, cityProfile, retryCityWithoutSlope, slopeNotes, nearbyRest, localRoute, availabilityNote};
});
