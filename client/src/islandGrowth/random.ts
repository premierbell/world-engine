// mulberry32 - 작고 충분히 균일한 시드 기반 PRNG. Island의 장식(지형/
// 오브젝트 선택)에 쓴다 - 같은 islandId는 항상 같은 순서로 같은 값을
// 내놓아서, DB에 저장하지 않고도 매번 같은 모습이 재현된다.
// docs/island_growth_visual.md "Deterministic 선택" 참고.
export function seededRandom(seed: number): () => number {
  let t = seed;
  return () => {
    t += 0x6d2b79f5;
    let r = Math.imul(t ^ (t >>> 15), t | 1);
    r ^= r + Math.imul(r ^ (r >>> 7), r | 61);
    return ((r ^ (r >>> 14)) >>> 0) / 4294967296;
  };
}
