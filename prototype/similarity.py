"""ai_rules.md Rule 3: 모든 섬의 중심 벡터와 Cosine Similarity 계산."""

import numpy as np


def cosine_similarity(a: list[float], b: list[float]) -> float:
    vec_a, vec_b = np.array(a), np.array(b)
    return float(np.dot(vec_a, vec_b) / (np.linalg.norm(vec_a) * np.linalg.norm(vec_b)))