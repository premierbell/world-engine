"""Experiment #44: Assignment Stability under Perturbation (고정 Anchor Set).

Experiment #41의 교란 요인(Anchor Set 자체가 관측 시점마다 달랐다)을
제거한 뒤, RQ7-B("Anchor Assignment는 안정적인가?")를 다시 묻는다. 다만
그냥 "같은 입력을 여러 번 넣어보는" 설계는 위험하다는 지적을 반영했다 -
이 알고리즘은 완전히 결정론적이라 같은 입력 = 항상 같은 출력이고, 그건
"안정성"이 아니라 "결정론성"만 확인하는 것이다.

이번 실험이 실제로 흔드는 건 **관측(observation)**이지 Anchor Set이
아니다: Anchor Set은 Day1+Day7로 한 번 만들고 완전히 고정한다(더 이상
갱신 안 함). Day30 스크랩의 클러스터링(candidate 구성)도 한 번만
계산해서 고정한다(HDBSCAN 파라미터를 흔드는 건 다른 축의 실험이라
이번엔 다루지 않는다 - 향후 확장 후보로만 남긴다). 대신 각 candidate의
관측된 embedding 벡터에 작은 가우시안 노이즈를 여러 번(trial) 주입해서,
"오늘 이 콘텐츠의 embedding이 아주 조금 다르게 나왔다면 1순위 Anchor가
바뀌었을까"를 측정한다 - Assignment가 관측의 작은 변화에도 안 흔들리는지
(brittle하지 않은지) 보는 것이다.

측정 지표:
- Assignment Consistency(%): trial들이 원본(무섭동) 1순위 Anchor와 같은
  Anchor를 고른 비율.
- Assignment Entropy: candidate별로 trial들이 고른 Anchor 분포의 엔트로피
  (0이면 완전히 안정, 클수록 여러 Anchor로 흩어짐).
- Margin(원본 관측의 1등-2등 격차)과 Consistency의 상관관계 - Experiment
  #29는 margin이 correctness(정답 여부)를 설명 못 한다는 걸 보였는데,
  margin이 stability(안정성)는 설명하는지는 아직 안 봤다.
"""

import random
import statistics
from collections import Counter, defaultdict

import numpy as np
import yaml
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from embedding_provider import OpenAIEmbeddingProvider
from experiment_anchor_model import load_virtual_user
from similarity import cosine_similarity
from world import Island, _cluster_new_scraps, _candidates_from_clusters, night_batch_anchor

console = Console()

N_TRIALS = 20
EPSILONS = [0.02, 0.05, 0.10]


def load_config(path: str = "config.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def build_fixed_anchor_set(scraps: list[dict], vectors: dict[str, list[float]], attach_threshold: float) -> list[Island]:
    islands: list[Island] = []
    for day in (1, 7):
        day_texts = [s["text"] for s in scraps if s["day"] == day]
        islands = night_batch_anchor(islands, day_texts, vectors, attach_threshold=attach_threshold)
    return islands


def perturb(vector: list[float], epsilon: float, rng: random.Random) -> list[float]:
    arr = np.array(vector)
    noise = np.array([rng.gauss(0, 1) for _ in range(len(arr))])
    noise = noise / np.linalg.norm(noise) * np.linalg.norm(arr) * epsilon
    return (arr + noise).tolist()


def entropy(counter: Counter, total: int) -> float:
    import math

    return -sum((n / total) * math.log(n / total) for n in counter.values() if n > 0)


def run_persona(user_name: str, scraps: list[dict], vectors: dict[str, list[float]], attach_threshold: float) -> None:
    anchors = build_fixed_anchor_set(scraps, vectors, attach_threshold)
    day30_texts = [s["text"] for s in scraps if s["day"] == 30]

    clusters = _cluster_new_scraps(day30_texts, vectors, min_cluster_size=3, min_samples=1)
    candidates = _candidates_from_clusters(clusters)

    def centroid(texts: list[str], vecs: dict[str, list[float]]) -> list[float]:
        arrs = [vecs[t] for t in texts]
        return (np.mean(arrs, axis=0)).tolist()

    def best_anchor(vec: list[float]) -> tuple[int, float, float | None]:
        scored = sorted(((a, cosine_similarity(vec, a.identity_vector)) for a in anchors), key=lambda p: -p[1])
        best_id, best_sim = scored[0][0].id, scored[0][1]
        second_sim = scored[1][1] if len(scored) > 1 else None
        return best_id, best_sim, second_sim

    original: list[dict] = []
    for texts in candidates:
        c = centroid(texts, vectors)
        aid, best_sim, second_sim = best_anchor(c)
        margin = (best_sim - second_sim) if second_sim is not None else None
        original.append({"texts": texts, "original_anchor": aid, "margin": margin})

    table = Table(title=f"Experiment #44: Assignment Stability under Perturbation ({user_name})")
    for col in ("epsilon", "평균 Consistency", "평균 Entropy", "margin-consistency 상관계수"):
        table.add_column(col)

    for epsilon in EPSILONS:
        rng = random.Random(42)
        consistencies = []
        entropies = []
        margins = []
        for rec in original:
            counts: Counter = Counter()
            for _ in range(N_TRIALS):
                perturbed_vecs = {t: perturb(vectors[t], epsilon, rng) for t in rec["texts"]}
                c = centroid(rec["texts"], perturbed_vecs)
                aid, _, _ = best_anchor(c)
                counts[aid] += 1
            consistency = counts[rec["original_anchor"]] / N_TRIALS
            consistencies.append(consistency)
            entropies.append(entropy(counts, N_TRIALS))
            if rec["margin"] is not None:
                margins.append((rec["margin"], consistency))

        avg_consistency = statistics.mean(consistencies)
        avg_entropy = statistics.mean(entropies)

        if len(margins) >= 2:
            m_vals = [m for m, _ in margins]
            c_vals = [c for _, c in margins]
            mean_m, mean_c = statistics.mean(m_vals), statistics.mean(c_vals)
            cov = sum((m - mean_m) * (c - mean_c) for m, c in margins)
            var_m = sum((m - mean_m) ** 2 for m in m_vals)
            var_c = sum((c - mean_c) ** 2 for c in c_vals)
            corr = cov / ((var_m * var_c) ** 0.5) if var_m > 0 and var_c > 0 else float("nan")
        else:
            corr = float("nan")

        table.add_row(f"{epsilon:.2f}", f"{avg_consistency:.1%}", f"{avg_entropy:.3f}", f"{corr:.3f}")

    console.print(table)
    console.print(f"  [dim]candidate 수: {len(original)}, trial 수: {N_TRIALS}[/dim]\n")


def main() -> None:
    load_dotenv()
    config = load_config()
    embedding_provider = OpenAIEmbeddingProvider(model=config["embedding"]["model"])

    for user_name, path in (
        ("Backend User", "../experiments/virtual_users/backend_developer.json"),
        ("AI Researcher", "../experiments/virtual_users/ai_researcher.json"),
    ):
        user = load_virtual_user(path)
        scraps = user["scraps"]
        vectors = {s["text"]: embedding_provider.embed(s["text"]) for s in scraps}

        run_persona(user_name, scraps, vectors, attach_threshold=0.30)


if __name__ == "__main__":
    main()
