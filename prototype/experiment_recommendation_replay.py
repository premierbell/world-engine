"""Two-stage 추천(Cosine Recall + LLM Pairwise 재정렬)이 Cosine만 쓸 때보다
실제로 나은지, 그리고 섬 대표 벡터를 "첫 스크랩 고정"에서 "그 시점 멤버 평균"으로
바꾸면 나아지는지를 실사용 데이터로 시간순 재현해 측정한다.

- 정답: 사용자가 실제로 확정한 섬(scrap.island_id)
- 시간순 재현: 각 스크랩 시점에 이미 존재하던 섬/스크랩만 사용(미래 데이터 누수 방지)
- 섬 생성 시각 = 그 섬 소속 스크랩 중 가장 이른 created_at(island 테이블에 생성 시각이 없음).
  그 스크랩 자신은 "새 섬을 만든 경우"라 평가 대상에서 제외
- 재정렬은 서버 코드(RecommendationService + LlmPairwiseJudgeClient.NEUTRAL_PROMPT,
  gpt-4o-mini, temperature 0)를 그대로 옮김

조건 (2 x 2):
  A  : Cosine Top-1, 섬 벡터 = DB에 저장된 값(현재 운영 방식의 Recall)
  B  : A의 Top-3 + LLM 재정렬 (현재 운영 방식 그대로)
  A' : Cosine Top-1, 섬 벡터 = 그 시점 멤버 임베딩 평균
  B' : A'의 Top-3 + LLM 재정렬

사용: uv run python experiment_recommendation_replay.py <export.json> [runs]
export.json 은 DB에서 읽기 전용으로 뽑은 개인 데이터라 레포에 커밋하지 않는다.
"""

import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import numpy as np
from dotenv import load_dotenv
from openai import OpenAI, RateLimitError

RECALL_SIZE = 3
MODEL = "gpt-4o-mini"
# gpt-4o-mini 단가(USD / 1M tokens) - 비용 추정용
PRICE_IN, PRICE_OUT = 0.15, 0.60

NEUTRAL_PROMPT = (
    "다음 두 스크랩 요약이 얼마나 밀접하게 관련되어 있는지 0.0~1.0 사이의 점수로 평가하라. "
    "'같은 주제인가/다른 주제인가'를 판단하지 말고, 단순히 두 내용이 서로 얼마나 가깝게 "
    "연관되어 있다고 느껴지는지만 평가하라. 점수 숫자 하나만 출력하라(예: 0.85). "
    "다른 설명은 절대 덧붙이지 마라.\n\n"
    "스크랩 A: {a}\n"
    "스크랩 B: {b}\n"
)


def cos(a, b):
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def parse_score(raw):
    # LlmPairwiseJudgeClient.parseScore 와 동일: 숫자 아니면 0.5, [0,1]로 자름
    try:
        return max(0.0, min(1.0, float(raw.strip())))
    except ValueError:
        return 0.5


class Judge:
    def __init__(self):
        load_dotenv()
        self.client = OpenAI()
        self.cache = {}
        self.calls = 0
        self.tok_in = 0
        self.tok_out = 0

    def score(self, a, b, run):
        key = (a, b, run)
        if key in self.cache:
            return self.cache[key]
        for attempt in range(6):
            try:
                t0 = time.perf_counter()
                res = self.client.chat.completions.create(
                    model=MODEL, temperature=0,
                    messages=[{"role": "user", "content": NEUTRAL_PROMPT.format(a=a, b=b)}],
                )
                latency = time.perf_counter() - t0
                break
            except RateLimitError:
                time.sleep(2 ** attempt)
        else:
            raise RuntimeError("rate limit retries exhausted")
        self.calls += 1
        self.tok_in += res.usage.prompt_tokens
        self.tok_out += res.usage.completion_tokens
        out = (parse_score(res.choices[0].message.content), latency)
        self.cache[key] = out
        return out


def build_cases(data):
    islands = {i["id"]: i for i in data["islands"]}
    for i in islands.values():
        i["vec"] = np.array(json.loads(i["embedding"]), dtype=np.float64)
    scraps = data["scraps"]  # created_at, id 순으로 정렬돼 있음
    for s in scraps:
        s["vec"] = np.array(json.loads(s["embedding"]), dtype=np.float64) if s["embedding"] else None

    island_birth = {}
    for s in scraps:
        island_birth.setdefault(s["island_id"], (s["created_at"], s["id"]))

    cases, skipped_founder, skipped_no_input = [], 0, 0
    for idx, s in enumerate(scraps):
        if island_birth[s["island_id"]][1] == s["id"]:
            skipped_founder += 1
            continue
        if s["vec"] is None or not s["summary"]:
            skipped_no_input += 1
            continue
        before = scraps[:idx]
        alive = [iid for iid, (t, sid) in island_birth.items() if (t, sid) < (s["created_at"], s["id"])]
        cases.append({"scrap": s, "before": before, "alive": alive})
    return islands, cases, skipped_founder, skipped_no_input


def recall(query, alive, islands, before, mode):
    cands = []
    for iid in alive:
        if mode == "stored":
            vec = islands[iid]["vec"]
        else:  # centroid of members that existed before this scrap
            members = [m["vec"] for m in before if m["island_id"] == iid and m["vec"] is not None]
            vec = np.mean(members, axis=0) if members else islands[iid]["vec"]
        cands.append((iid, cos(query, vec)))
    cands.sort(key=lambda x: -x[1])
    return [iid for iid, _ in cands[:RECALL_SIZE]]


def representative_text(iid, query, before, islands):
    # RecommendationService.representativeText: 그 섬 스크랩 중 query와 가장 가까운 것의 summary
    members = [m for m in before if m["island_id"] == iid and m["vec"] is not None and m["summary"]]
    if not members:
        return islands[iid]["name"]
    return max(members, key=lambda m: cos(query, m["vec"]))["summary"]


def evaluate(islands, cases, judge, runs):
    results = {}
    for mode, label in (("stored", ""), ("centroid", "'")):
        recalled = [recall(c["scrap"]["vec"], c["alive"], islands, c["before"], mode) for c in cases]
        truth = [c["scrap"]["island_id"] for c in cases]
        n = len(cases)
        a_hit = sum(r[0] == t for r, t in zip(recalled, truth))
        top3 = sum(t in r for r, t in zip(recalled, truth))
        results["A" + label] = {"top1": a_hit, "top3_contains": top3, "n": n}

        b_runs = []
        for run in range(runs):
            def judge_case(i):
                c = cases[i]
                q = c["scrap"]
                scored = []
                total_latency = 0.0
                for iid in recalled[i]:
                    text = representative_text(iid, q["vec"], c["before"], islands)
                    score, lat = judge.score(q["summary"], text, run)
                    total_latency += lat
                    scored.append((iid, score))
                ranked = sorted(scored, key=lambda x: -x[1])  # stable: 동점이면 cosine 순서 유지
                return ranked[0][0], total_latency, len(scored)

            with ThreadPoolExecutor(max_workers=4) as pool:
                outs = list(pool.map(judge_case, range(n)))
            b_top1 = [o[0] for o in outs]
            hit = sum(p == t for p, t in zip(b_top1, truth))
            flipped = [(r[0], p, t) for r, p, t in zip(recalled, b_top1, truth) if p != r[0]]
            b_runs.append({
                "top1": hit,
                "flipped": len(flipped),
                "flipped_to_correct": sum(p == t for _, p, t in flipped),
                "flipped_from_correct": sum(c0 == t for c0, _, t in flipped),
                "latency_per_scrap_s": sum(o[1] for o in outs) / n,
                "llm_calls_per_scrap": sum(o[2] for o in outs) / n,
            })
        results["B" + label] = {"n": n, "runs": b_runs}
    return results


def main():
    path = sys.argv[1]
    runs = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    data = json.load(open(path))
    islands, cases, skipped_founder, skipped_no_input = build_cases(data)

    # 진단: 저장된 섬 벡터가 현재 멤버 중 누구와 가장 가까운지(첫 스크랩 고정 + 갱신 누락 확인)
    diag = []
    for iid, isl in islands.items():
        members = [s for s in data["scraps"] if s["island_id"] == iid and s["vec"] is not None]
        best = max(cos(isl["vec"], m["vec"]) for m in members)
        diag.append({"island": iid, "members": len(members), "max_cos_to_member": round(best, 4)})

    judge = Judge()
    results = evaluate(islands, cases, judge, runs)
    cost = judge.tok_in / 1e6 * PRICE_IN + judge.tok_out / 1e6 * PRICE_OUT
    report = {
        "evaluated": len(cases),
        "skipped_founder": skipped_founder,
        "skipped_no_input": skipped_no_input,
        "runs": runs,
        "results": results,
        "llm_total": {"calls": judge.calls, "tokens_in": judge.tok_in, "tokens_out": judge.tok_out,
                      "cost_usd": round(cost, 4)},
        "stored_vector_diagnostic": diag,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
