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

  function cityProfile(profile, basic = false) {
    return {
      ...profile, rest: false, restMinutes: null,
      ...(basic ? {avoidSteps: false, wheelchair: false, maxSlope: null, avoidSlope: false} :
        {avoidSlope: profile.maxSlope != null && profile.avoidSlope}),
    };
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
    let basic = false;
    try {
      result = Endpoint.route(E, working, from, to, preferred);
    } catch (error) {
      if (!(profile.rest || profile.maxSlope != null || profile.avoidSlope || profile.avoidSteps || profile.wheelchair)) {
        throw error;
      }
      basic = true;
      result = Endpoint.route(E, working, from, to, cityProfile(profile, true));
    }
    const notes = ['시연 전용 · 실제 이용과 안전은 현장에서 확인해 주세요.'];
    if (profile.rest) notes.push('시설은 모두 개방으로 가정했어요. 운영시간·출입 제한·검증 상태와 요청한 휴식 간격은 적용하지 않았어요.');
    if (basic) notes.push('기본 보행망에서 찾은 예시로, 입력한 계단·경사 등 이동 조건을 충족하지 않을 수 있어요.');
    return {
      ...result, p: profile, label: '베타 시연 경로', selectionIneligible: true, demoNotes: notes,
      demoNearbyRest: result.restStop ? null : nearbyRest(E, result.coords, candidates, profile),
    };
  }

  return {places, cityProfile, nearbyRest, localRoute, availabilityNote};
});
