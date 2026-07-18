"""Experiment #47: Pairwise LLM Judgment at Scale, with Granularity Labels.

Experiment #46(Error Analysis)이 드러낸 건 LLM의 오류가 아니라 **Virtual
Dataset의 ground truth Topic 라벨이 단일 해상도가 아니라는 것**이었다 -
"Transformer"라는 라벨 하나가 Self-Attention/Layer Normalization/Sliding
Window Attention처럼 서로 다른 구체적 메커니즘을 뭉뚱그리고, "Evaluation"은
원래 여러 Topic에 걸쳐 적용되는 범주 개념이다.

이 실험은 단순히 표본만 5배 늘리는 게 아니라, 각 scrap에 **mechanism
label**(topic보다 한 단계 더 구체적인 하위 개념 - 이 실험을 위해 사람이
직접 읽고 붙인 주석, 원래 데이터셋 설계의 일부가 아니다)을 추가로
붙여서 pair를 세 가지로 나눈다:

- **Case A**: 같은 Topic + 같은 mechanism (예: LoRA ↔ QLoRA, 둘 다
  "peft_low_rank")
- **Case B**: 같은 Topic + 다른 mechanism (예: LoRA ↔ Catastrophic
  Forgetting, 둘 다 Fine-tuning이지만 다른 구체적 메커니즘)
- **Case C**: 다른 Topic

Case A/B/C 각각의 ROC-AUC를 따로 계산한다. A와 C가 둘 다 높고 B만 낮다면,
"LLM이 판단을 못 한다"가 아니라 "ground truth Topic 라벨 자체가 여러
해상도를 섞고 있다"(Finding #012 후보)는 게 정량적으로 증명된다.

주의: mechanism label은 이 실험을 위해 필자가 직접 스크랩 71개를 읽고
붙인 주석이다 - 원래 Virtual User 데이터셋 설계자가 정한 게 아니라서
주관이 섞일 수 있다는 한계가 있다(Decision에서 명시).
"""

import itertools
import json
import random

import yaml
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from sklearn.metrics import roc_auc_score

from experiment_anchor_model import load_virtual_user
from pairwise_judge import OpenAIPairwiseJudge

console = Console()

CACHE_PATH = "pairwise_judgment_cache.json"

# 필자가 71개 스크랩을 직접 읽고 붙인 mechanism sub-label (Experiment #46
# Error Analysis에서 발견한 granularity mismatch를 검증하기 위한 주석).
MECHANISM_LABELS: dict[str, str] = {
    "Transformer 아키텍처 처음 공부하기. Self-Attention이 어떻게 토큰 간 관계를 계산하는지 기초부터 정리한다": "self_attention",
    "Attention is All You Need 논문 읽기. Recurrence 없이 병렬 처리가 가능해진 이유를 이해한다.": "parallel_processing",
    "Positional Encoding 개념 익히기. 순서 정보가 없는 Attention에 위치 정보를 어떻게 주입하는지 정리한다": "positional_encoding",
    "Multi-Head Attention 이해하기. 여러 개의 attention head가 서로 다른 관계를 포착하는 원리를 익힌다": "multi_head_attention",
    "Encoder-Decoder 구조 기초. 번역 태스크에서 두 구조가 어떻게 상호작용하는지 살펴본다.": "encoder_decoder",
    "Transformer의 계산 복잡도 문제 처음 접하기. 시퀀스 길이의 제곱에 비례하는 이유를 정리한다.": "complexity",
    "Layer Normalization 위치 비교하기. Pre-LN과 Post-LN이 학습 안정성에 미치는 영향을 살펴본다.": "layer_norm",
    "BERT와 GPT 구조 차이 정리하기. Encoder-only와 Decoder-only 구조가 어떤 태스크에 유리한지 비교한다": "architecture_comparison",
    "Sliding Window Attention 이해하기. 긴 시퀀스를 효율적으로 처리하는 최근 아키텍처 변형을 정리한다.": "sliding_window_attention",
    "RLHF가 뭔지 처음 정리해본다. 사람 피드백으로 보상 모델을 학습시키는 큰 그림을 이해한다.": "overview",
    "보상 모델(Reward Model) 학습 과정 살펴보기. 사람이 매긴 선호도 순위로 어떻게 점수를 학습하는지 정리한다.": "reward_model",
    "PPO로 언어모델 파인튜닝하기. 강화학습 정책 업데이트가 언어모델에 어떻게 적용되는지 처음 살펴본다.": "policy_optimization",
    "RLHF의 KL penalty 역할 이해하기. 원래 모델에서 너무 멀어지지 않게 막는 이유를 정리한다.": "policy_optimization",
    "RLHF와 SFT(Supervised Fine-Tuning)의 관계 정리하기. 왜 SFT 이후에 RLHF를 적용하는지 이해한다": "sft_relationship",
    "RLHF 파이프라인 구현해보기. 보상 모델과 정책 모델을 함께 학습시키는 최소 구조를 실행해본다.": "pipeline_implementation",
    "DPO(Direct Preference Optimization) 비교하기. RLHF보다 단순한 방식으로 선호도를 학습하는 최근": "dpo_comparison",
    "Diffusion 모델 처음 접하기. 노이즈를 점진적으로 제거하며 이미지를 생성하는 큰 그림을 이해한다.": "overview",
    "Forward Process와 Reverse Process 이해하기. 노이즈를 추가하는 과정과 제거하는 과정을 각각 정리한다.": "noise_process",
    "DDPM 논문 핵심 정리하기. Diffusion 모델을 학습 가능하게 만든 초기 접근을 살펴본다.": "ddpm",
    "Latent Diffusion 개념 익히기. 픽셀 공간이 아니라 잠재 공간에서 diffusion을 수행하는 이유를 이해한다.": "latent_diffusion",
    "Classifier-Free Guidance 이해하기. 조건부 생성 품질을 높이는 기법을 처음 살펴본다.": "guidance",
    "Diffusion 모델의 샘플링 속도 문제 정리하기. 왜 생성에 여러 스텝이 필요한지 이해한다.": "sampling_efficiency",
    "DDIM으로 샘플링 스텝 줄이기. 품질을 유지하면서 생성 속도를 높이는 방법을 살펴본다.": "sampling_efficiency",
    "벡터 데이터베이스가 왜 필요한지 처음 이해하기. 임베딩 유사도 검색을 일반 DB로 하기 어려운 이유를 정리한다.": "overview",
    "HNSW 인덱스 구조 살펴보기. 근사 최근접 이웃 탐색이 어떻게 빨라지는지 개념을 익힌다.": "indexing",
    "Pinecone과 Qdrant 비교해보기. 관리형 벡터 DB와 오픈소스 벡터 DB의 차이를 정리한다.": "db_comparison",
    "임베딩 차원과 검색 성능의 관계 살펴보기. 차원이 늘어날 때 트레이드오프를 처음 관찰한다.": "dimension_tradeoff",
    "코사인 유사도 vs 유클리드 거리 비교하기. 임베딩 검색에서 어떤 metric을 언제 쓰는지 정리한다.": "similarity_metric",
    "벡터 DB에 메타데이터 필터링 적용하기. 벡터 검색과 조건 필터를 함께 쓰는 하이브리드 쿼리를 살펴본다.": "hybrid_query",
    "벡터 인덱스 재구축 비용 고민하기. 임베딩 모델을 바꿀 때 전체 재인덱싱이 필요한 이유를 정리한다.": "reindexing",
    "LoRA로 효율적인 파인튜닝하기. 전체 파라미터 대신 저랭크 행렬만 학습하는 원리를 정리한다.": "peft_low_rank",
    "QLoRA 이해하기. 양자화된 모델 위에서 LoRA를 적용해 메모리를 더 아끼는 방법을 살펴본다.": "peft_low_rank",
    "Full Fine-tuning vs PEFT 비교하기. 언제 전체 파인튜닝이 필요하고 언제 PEFT로 충분한지 정리한다.": "peft_vs_full",
    "파인튜닝 데이터셋 품질 관리하기. 소량이지만 정제된 데이터가 왜 더 효과적인지 이해한다.": "data_quality",
    "Catastrophic Forgetting 문제 살펴보기. 파인튜닝 중 기존 능력을 잃는 현상과 완화 방법을 정리한다.": "catastrophic_forgetting",
    "Instruction Tuning 데이터 구성하기. 다양한 태스크 지시문으로 모델을 학습시키는 방법을 살펴본다.": "instruction_data",
    "파인튜닝 후 평가 방법 고민하기. 기존 벤치마크와 태스크 특화 평가를 어떻게 나눠서 볼지 정리한다.": "evaluation_method",
    "LLM 벤치마크 종류 정리하기. MMLU, HellaSwag 같은 벤치마크가 각각 무엇을 측정하는지 이해한다.": "benchmark_types",
    "벤치마크 오염(Contamination) 문제 살펴보기. 평가 데이터가 학습 데이터에 섞여 들어가는 위험을 정리한다.": "benchmark_contamination",
    "LLM-as-a-Judge 방식 이해하기. 사람 대신 다른 LLM이 응답 품질을 평가하는 방법을 살펴본다.": "llm_as_judge",
    "Human Evaluation 설계하기. 평가자 간 일치도를 어떻게 측정하고 관리하는지 정리한다.": "human_evaluation",
    "리더보드 순위의 함정 고민하기. 벤치마크 점수가 실제 사용성과 괴리될 수 있는 이유를 살펴본다.": "benchmark_types",
    "정성 평가와 정량 평가를 함께 쓰는 이유 정리하기. 숫자만으로 놓치는 부분을 어떻게 보완할지 생각한다.": "qual_quant_combination",
    "Vision-Language 모델 처음 살펴보기. 이미지와 텍스트를 같은 임베딩 공간에 매핑하는 큰 그림을 이해한다.": "overview",
    "CLIP 학습 방식 정리하기. 이미지-텍스트 쌍으로 대조 학습을 하는 원리를 살펴본다.": "clip",
    "이미지 캡셔닝 모델 구조 이해하기. Vision Encoder와 언어 Decoder가 어떻게 연결되는지 정리한다.": "captioning",
    "멀티모달 모델의 토큰화 방식 살펴보기. 이미지를 패치 단위로 나눠 토큰처럼 다루는 방법을 이해한다.": "tokenization",
    "오디오-텍스트 멀티모달 모델 살펴보기. 음성 인식과 언어모델이 결합되는 구조를 정리한다.": "audio_text",
    "멀티모달 데이터셋 구축의 어려움 고민하기. 정합성 있는 이미지-텍스트 쌍을 모으는 과정을 살펴본다.": "dataset_construction",
    "Vision-Language 모델 평가 방법 정리하기. 텍스트 전용 평가와 어떤 부분이 다른지 이해한다.": "evaluation_method",
    "멀티모달 모델의 환각 문제 살펴보기. 이미지에 없는 내용을 설명하는 현상과 원인을 정리한다.": "hallucination",
    "LLM Agent 개념 처음 정리하기. 도구 호출을 반복하며 작업을 완수하는 루프 구조를 이해한다.": "overview",
    "ReAct 패턴 살펴보기. 추론(Reasoning)과 행동(Action)을 번갈아 수행하는 방식을 정리한다.": "react_pattern",
    "Agent의 계획 수립 단계 이해하기. 복잡한 작업을 하위 태스크로 쪼개는 방법을 살펴본다.": "planning",
    "Tool Use 설계하기. Agent가 외부 API를 호출할 때 스키마를 어떻게 정의하는지 정리한다.": "tool_integration",
    "Multi-Agent 시스템 살펴보기. 여러 Agent가 역할을 나눠 협업하는 구조를 이해한다.": "multi_agent",
    "Agent의 메모리 관리 고민하기. 긴 작업 동안 이전 맥락을 어떻게 유지할지 살펴본다.": "memory",
    "Agent 평가 방법 정리하기. 최종 결과뿐 아니라 중간 과정의 효율성도 측정하는 방법을 고민한다.": "evaluation_method",
    "Agent의 실패 복구 전략 살펴보기. 도구 호출이 실패했을 때 재시도/대체 전략을 정리한다.": "failure_recovery",
    "MCP로 Agent에게 도구 노출하기. 표준화된 방식으로 외부 시스템과 Agent를 연결하는 구조를 살펴본다.": "tool_integration",
    "Agent 안전성 고민하기. 의도치 않은 행동을 막기 위한 권한 제한과 검증 절차를 정리한다.": "safety",
    "Prompt Engineering 기초 정리하기. 역할 지정과 출력 형식 강제가 응답에 미치는 영향을 살펴본다.": "basics",
    "Chain-of-Thought 프롬프팅 이해하기. 단계별 추론을 유도해 복잡한 문제 정답률을 높이는 방법을 정리한다.": "reasoning_prompting",
    "Few-shot 예시 선택 전략 고민하기. 무작위 선택과 유사도 기반 선택의 차이를 살펴본다.": "few_shot_selection",
    "System Prompt 설계 체크리스트 만들기. 금지 사항과 출력 형식을 효과적으로 조합하는 방법을 정리한다.": "system_prompt_design",
    "프롬프트 인젝션 방어 고민하기. 사용자 입력에 숨겨진 지시문을 어떻게 무력화할지 살펴본다.": "injection_defense",
    "프롬프트 버전 관리하기. 실험한 프롬프트들을 체계적으로 추적하는 방법을 정리한다.": "versioning",
    "Self-Consistency 기법 이해하기. 여러 번 샘플링해서 다수결로 답을 정하는 방식을 살펴본다.": "reasoning_prompting",
    "프롬프트 압축 고민하기. 긴 지시문을 토큰 비용을 아끼면서 유지하는 방법을 정리한다.": "compression",
    "Meta-Prompting 살펴보기. LLM이 스스로 프롬프트를 개선하게 만드는 방법을 이해한다.": "meta_prompting",
    "프롬프트와 파인튜닝의 경계 고민하기. 언제 프롬프트로 충분하고 언제 파인튜닝이 필요한지 정리한다.": "prompt_vs_finetuning",
}


def load_config(path: str = "config.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def load_cache() -> dict[str, float]:
    try:
        with open(CACHE_PATH) as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save_cache(cache: dict[str, float]) -> None:
    with open(CACHE_PATH, "w") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def pair_key(text_a: str, text_b: str) -> str:
    a, b = sorted((text_a, text_b))
    return f"{a}|||{b}"


def classify(a: dict, b: dict) -> str:
    if a["topic"] != b["topic"]:
        return "C"
    return "A" if MECHANISM_LABELS[a["text"]] == MECHANISM_LABELS[b["text"]] else "B"


def curated_sample(scraps: list[dict], per_topic_cap: int, seed: int = 7) -> list[dict]:
    """Case A(같은 mechanism) 쌍이 최소 1개는 포함되도록, mechanism이 중복되는
    스크랩은 반드시 넣고 나머지는 topic별로 최대 per_topic_cap개까지 무작위로
    채운다 - 전체 71개 쌍(2485개)을 다 돌리는 대신 규모를 관리 가능하게 줄인다."""
    rng = random.Random(seed)
    by_topic: dict[str, list[dict]] = {}
    for s in scraps:
        by_topic.setdefault(s["topic"], []).append(s)

    selected: list[dict] = []
    for topic, group in by_topic.items():
        mech_count: dict[str, int] = {}
        for s in group:
            mech_count[MECHANISM_LABELS[s["text"]]] = mech_count.get(MECHANISM_LABELS[s["text"]], 0) + 1
        mandatory = [s for s in group if mech_count[MECHANISM_LABELS[s["text"]]] > 1]
        rest = [s for s in group if s not in mandatory]
        rng.shuffle(rest)
        fill_n = max(0, per_topic_cap - len(mandatory))
        selected.extend(mandatory + rest[:fill_n])

    return selected


def main() -> None:
    load_dotenv()
    config = load_config()
    judge = OpenAIPairwiseJudge(model=config["label"]["model"])

    user = load_virtual_user("../experiments/virtual_users/ai_researcher.json")
    all_scraps = [s for s in user["scraps"] if s["text"] in MECHANISM_LABELS]
    scraps = curated_sample(all_scraps, per_topic_cap=4)
    console.print(f"[bold]표본 {len(scraps)}개 스크랩(Case A 쌍 보장 + topic당 최대 4개), "
                  f"쌍 {len(scraps)*(len(scraps)-1)//2}개[/bold]")

    cache = load_cache()
    buckets: dict[str, list[tuple[float, int]]] = {"A": [], "B": [], "C": []}
    all_labels, all_scores = [], []

    total_pairs = len(scraps) * (len(scraps) - 1) // 2
    done = 0
    for a, b in itertools.combinations(scraps, 2):
        key = pair_key(a["text"], b["text"])
        if key not in cache:
            cache[key] = judge.score(a["text"], b["text"])
        score = cache[key]
        case = classify(a, b)
        is_same_topic = 1 if a["topic"] == b["topic"] else 0
        buckets[case].append((score, is_same_topic))
        all_labels.append(is_same_topic)
        all_scores.append(score)
        done += 1
        if done % 100 == 0:
            save_cache(cache)  # 중간 저장 - 오래 걸리는 배치라 중단돼도 캐시는 남게

    save_cache(cache)

    table = Table(title="Experiment #47: Case별 Pairwise Score 분포 (AI Researcher, 전체)")
    for col in ("Case", "설명", "n", "mean score", "ROC-AUC (same-topic 기준)"):
        table.add_column(col)

    descriptions = {
        "A": "같은 Topic, 같은 mechanism",
        "B": "같은 Topic, 다른 mechanism",
        "C": "다른 Topic",
    }
    for case in ("A", "B", "C"):
        scores_labels = buckets[case]
        if not scores_labels:
            table.add_row(case, descriptions[case], "0", "-", "-")
            continue
        scores = [s for s, _ in scores_labels]
        mean_score = sum(scores) / len(scores)
        labels = [lab for _, lab in scores_labels]
        try:
            auc = roc_auc_score(labels, scores) if len(set(labels)) > 1 else float("nan")
        except ValueError:
            auc = float("nan")
        table.add_row(case, descriptions[case], str(len(scores_labels)), f"{mean_score:.3f}",
                       f"{auc:.3f}" if auc == auc else "n/a(단일 클래스)")

    console.print(table)

    overall_auc = roc_auc_score(all_labels, all_scores)
    console.print(f"\n[bold]전체 ROC-AUC(같은 Topic 여부 기준): {overall_auc:.3f}[/bold]")
    console.print(
        "[dim]mechanism label은 필자가 직접 붙인 주석(원 데이터셋 설계 아님) - "
        "주관 개입 가능성을 감안해서 해석할 것.[/dim]"
    )


if __name__ == "__main__":
    main()
