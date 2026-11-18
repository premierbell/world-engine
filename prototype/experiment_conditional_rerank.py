"""LLM 재정렬을 유지할지 판단하기 위한 후속 실험 (2026-11-18).
운영 코드가 섬 벡터 = 멤버 평균(PR #148)으로 바뀌었으므로 그 조건(A'/B')을 기준으로 한다.

실험 1. 조건부 재정렬: Cosine 1위-2위 점수 차(margin)가 기준값보다 작을 때만 LLM 재정렬.
        과적합 방지 - 시간순 앞 절반(tune)에서 기준값을 고르고 뒤 절반(test)에서 평가.
        기준값 선택 규칙(사전 고정): tune 정확도 최대, 동률이면 LLM 호출이 가장 적은 값.
실험 2. 재정렬 3회 호출 순차 vs 병렬 지연(p50/p95). 케이스마다 순서를 번갈아 편향 제거.
실험 4. 사례 분석용 오답 목록 - 개인 데이터라 레포에는 남기지 않고 별도 파일(argv[2])로만 출력.

사전 고정한 판단 기준(실행 전 합의):
- test에서 조건부가 전체 재정렬보다 1건 이하로만 덜 맞히고 LLM 호출 50% 이하 -> 조건부 채택
- tune/test 모두에서 전체 재정렬이 Cosine만보다 낫지 않음 -> 재정렬 제거
- 둘 다 아니면 전체 재정렬 유지
- 병렬 p50이 순차의 50% 이하 -> 병렬화 적용

사용: uv run python experiment_conditional_rerank.py <export.json> <case_detail_out.json>
"""

import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import numpy as np

from experiment_recommendation_replay import (
    MODEL, NEUTRAL_PROMPT, RECALL_SIZE, Judge, build_cases, cos, parse_score, representative_text,
)


def centroid_recall_with_scores(case, islands):
    q = case["scrap"]["vec"]
    scored = []
    for iid in case["alive"]:
        members = [m["vec"] for m in case["before"] if m["island_id"] == iid and m["vec"] is not None]
        vec = np.mean(members, axis=0) if members else islands[iid]["vec"]
        scored.append((iid, cos(q, vec)))
    scored.sort(key=lambda x: -x[1])
    return scored[:RECALL_SIZE]


def prepare(cases, islands, judge):
    rows = []
    for c in cases:
        q = c["scrap"]
        recalled = centroid_recall_with_scores(c, islands)
        texts = [representative_text(iid, q["vec"], c["before"], islands) for iid, _ in recalled]
        rows.append({"case": c, "recalled": recalled, "texts": texts})

    def llm(i):
        r = rows[i]
        return [judge.score(r["case"]["scrap"]["summary"], t, 0)[0] for t in r["texts"]]

    with ThreadPoolExecutor(max_workers=4) as pool:
        llm_scores = list(pool.map(llm, range(len(rows))))

    for r, scores in zip(rows, llm_scores):
        ids = [iid for iid, _ in r["recalled"]]
        ranked = sorted(zip(ids, scores), key=lambda x: -x[1])  # stable: 동점이면 cosine 순서
        r["truth"] = r["case"]["scrap"]["island_id"]
        r["cos_top1"] = ids[0]
        r["rerank_top1"] = ranked[0][0]
        r["llm_scores"] = scores
        cs = [s for _, s in r["recalled"]]
        r["margin"] = cs[0] - cs[1] if len(cs) > 1 else float("inf")
        r["n_cands"] = len(ids)
    return rows


def gated(rows, t):
    hit = calls = good = bad = 0
    for r in rows:
        use_llm = r["margin"] < t and r["n_cands"] > 1
        pred = r["rerank_top1"] if use_llm else r["cos_top1"]
        hit += pred == r["truth"]
        if use_llm:
            calls += r["n_cands"]
            if pred != r["cos_top1"]:
                good += pred == r["truth"]
                bad += r["cos_top1"] == r["truth"]
    max_calls = sum(r["n_cands"] for r in rows if r["n_cands"] > 1)
    return {"hit": hit, "n": len(rows), "llm_calls": calls,
            "llm_call_ratio": round(calls / max_calls, 3) if max_calls else 0.0,
            "flip_to_correct": good, "flip_to_wrong": bad}


def choose_threshold(tune):
    finite = sorted({r["margin"] for r in tune if r["margin"] != float("inf")})
    grid = [0.0] + [m + 1e-9 for m in finite] + [float("inf")]
    best = None
    for t in grid:
        g = gated(tune, t)
        key = (g["hit"], -g["llm_calls"])
        if best is None or key > best[0]:
            best = (key, t, g)
    return best[1], best[2]


def latency_experiment(rows):
    from dotenv import load_dotenv
    from openai import OpenAI
    load_dotenv()
    client = OpenAI()

    def call(a, b):
        return client.chat.completions.create(
            model=MODEL, temperature=0,
            messages=[{"role": "user", "content": NEUTRAL_PROMPT.format(a=a, b=b)}],
        ).choices[0].message.content

    seq, par = [], []
    for i, r in enumerate(rows):
        a = r["case"]["scrap"]["summary"]

        def run_seq():
            t0 = time.perf_counter()
            for t in r["texts"]:
                call(a, t)
            return time.perf_counter() - t0

        def run_par():
            t0 = time.perf_counter()
            with ThreadPoolExecutor(max_workers=len(r["texts"])) as pool:
                list(pool.map(lambda t: call(a, t), r["texts"]))
            return time.perf_counter() - t0

        if i % 2 == 0:
            seq.append(run_seq()); par.append(run_par())
        else:
            par.append(run_par()); seq.append(run_seq())

    def pct(xs, p):
        return round(float(np.percentile(xs, p)), 3)
    return {"sequential_s": {"p50": pct(seq, 50), "p95": pct(seq, 95)},
            "parallel_s": {"p50": pct(par, 50), "p95": pct(par, 95)},
            "n": len(rows)}


def main():
    data = json.load(open(sys.argv[1]))
    islands, cases, skipped_founder, skipped_no_input = build_cases(data)
    judge = Judge()
    rows = prepare(cases, islands, judge)

    half = len(rows) // 2
    tune, test = rows[:half], rows[half:]
    t, tune_gated = choose_threshold(tune)

    report = {
        "evaluated": len(rows), "tune_n": len(tune), "test_n": len(test),
        "chosen_margin_threshold": t,
        "tune": {"cosine_only": gated(tune, 0.0), "full_rerank": gated(tune, float("inf")), "gated": tune_gated},
        "test": {"cosine_only": gated(test, 0.0), "full_rerank": gated(test, float("inf")), "gated": gated(test, t)},
        "all_descriptive": {str(x): gated(rows, x) for x in (0.0, 0.01, 0.02, 0.03, 0.05, 0.08, float("inf"))},
        "latency": latency_experiment(rows),
        "llm_cost_usd_ranking_part": round(judge.tok_in / 1e6 * 0.15 + judge.tok_out / 1e6 * 0.60, 4),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))

    # 사례 분석용(개인 데이터) - 레포 밖 파일로만
    names = {iid: isl["name"] for iid, isl in islands.items()}
    detail = []
    for idx, r in enumerate(rows):
        if r["cos_top1"] != r["truth"] or r["rerank_top1"] != r["truth"]:
            s = r["case"]["scrap"]
            detail.append({
                "order": idx, "half": "tune" if idx < half else "test", "scrap_id": s["id"],
                "title": s["title"], "source_type": s["source_type"], "summary": s["summary"][:300],
                "truth": names[r["truth"]], "cos_top1": names[r["cos_top1"]], "rerank_top1": names[r["rerank_top1"]],
                "margin": round(r["margin"], 4),
                "candidates": [(names[i], round(c, 4), sc) for (i, c), sc in zip(r["recalled"], r["llm_scores"])],
            })
    json.dump(detail, open(sys.argv[2], "w"), ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
