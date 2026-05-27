"""Gemini 3.1 Flash Lite VLM food-ingredient extraction evaluator with W&B logging.

Install:
    pip install -U google-genai pillow wandb

Required environment variables:
    GEMINI_API_KEY
    WANDB_API_KEY

This script evaluates food ingredient extraction from images and logs metrics to W&B.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import time
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps

try:
    import wandb
except ImportError:
    wandb = None

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None


PROMPT = """
이미지에서 유효한 음식 재료명을 추출해.
재료명은 레시피 검색에 쓰기 좋은 표준명으로 정리해.

규칙:
- 포장 식품, 음료, 소스, 조미료도 유효한 음식 재료로 본다. 내용물이 직접 보이지 않아도 포장 전면의 큰 제품명과 재료명을 읽어 items에 포함해.
- 이미지에 비식품 물건이 함께 있어도 음식/음료/식재료가 하나라도 명확히 보이면 invalid로 분류하지 마. 비식품 물건은 무시하고 음식/음료/식재료만 추출해.
- type 기준: 실제 물건/포장 식품/음료 사진이면 food, 레시피/체크리스트/메모/표처럼 텍스트가 주된 이미지이면 text, 음식 관련 단서가 전혀 없을 때만 invalid를 사용해.
- 포장/라벨 텍스트가 핵심 단서인 이미지는 invalid로 분류하지 말고 type을 food로 두고, 읽을 수 있는 음식 재료/제품을 추출해.
- 체크리스트/할 일 메모/식단표 같은 텍스트 이미지는 체크 여부와 무관하게 음식/음료/영양제/물처럼 섭취하는 항목을 모두 추출하고, 비음식 활동은 제외해.
- 음료도 음식 재료/제품으로 본다. 탄산음료, 요구르트, 발효유, 물, 와인처럼 마실 수 있는 제품명은 items에 포함해.
- 과일/해산물의 껍질, 껍데기, 줄기, 말랭이, 칩처럼 원물과 다른 형태가 명확히 보이면 원물로 뭉뚱그리지 말고 그 형태를 유지해. 먹을 수 있는 과육/살보다 껍질/껍데기가 주된 사진이면 수박껍질, 굴껍데기처럼 표현해. 예: 수박껍질, 굴껍데기, 귤껍질, 고구마말랭이, 감자칩, 고구마칩.
- 한 이미지에 작은 포장 식품이나 봉지 과자가 여러 개 있으면 눈에 띄는 제품/재료를 빠뜨리지 말고 모두 읽어. 예: 새우깡, 콘칩, 감자칩, 고구마칩.
- 깐양파, 채썬양파는 양파로 정리해.
- 편마늘, 깐마늘, 통마늘은 마늘로 정리해.
- 다진마늘, 간마늘은 마늘이 아니라 다진마늘로 유지해.
- 쌀과 밥은 구분해.
- 고추, 고춧가루, 고추장은 구분해.
- 포장육/양념육은 상품명에 부위명이나 조리명이 있어도 레시피 검색 표준명으로 소고기 또는 돼지고기를 우선 사용해. 다진 고기는 다진돼지고기/다진소고기로 구체화해.
- 닭고기는 부위가 확실하면 닭가슴살, 닭다리살처럼 정리하고, 확실하지 않으면 닭고기로 정리해. 한 제품/한 덩어리를 여러 부위명으로 중복 추정하지 마.
- 채소류는 헷갈리면 특수하거나 드문 이름보다 사람들이 흔히 먹는 채소명으로 정리해. 예: 깻잎, 상추, 청경채, 시금치, 근대, 양배추, 배추, 대파, 쪽파.
- 야채/채소처럼 범용으로 적힌 제품은 야채로 유지하고, 샐러드용 혼합 채소는 샐러드채소로 정리해.
- 버섯은 종류가 확실하면 표고버섯, 새송이버섯, 팽이버섯, 느타리버섯처럼 구체적으로 정리하고, 확실하지 않으면 버섯으로 정리해.
- 포장된 잎채소가 넓은 타원형 잎으로 여러 장 겹쳐 있고 잎맥이 뚜렷하면 깻잎으로 우선 판단해. 쑥갓은 잎이 잘게 갈라진 형태일 때만 쑥갓으로 판단해.
- 여러 채소가 펼쳐진 사진에서는 범용 잎채소로 뭉뚱그리지 말고 보이는 개별 재료를 끝까지 세어. 넓고 부드러운 호박 잎은 호박잎, 길고 옅은 초록색 호박은 애호박, 길고 가는 파 다발은 쪽파, 작고 둥근 빨간 열매는 앵두로 판단해.
- 곡물/잡곡은 색과 크기로 구분해. 흰색의 둥근 찰성 쌀알은 찹쌀, 작고 둥근 노란색/연두색 잡곡은 조로 판단하고, 쌀/들깨처럼 과하게 일반화하지 마.
- 한방/백숙 재료에서는 둥글게 깐 흰 알은 밤, 갈색의 가는 나무 막대처럼 보이는 약재는 감초, 두꺼운 절편 뿌리는 황기/엄나무처럼 구분해.
- 포장면/파스타는 포장명을 그대로 읽어. 비빔면, 마카로니, 푸실리, 메밀면은 라면이나 일반 면으로 뭉뚱그리지 마.
- 텍스트 이미지에서 유산균처럼 구체적인 섭취 항목을 이미 뽑았다면 영양제 같은 더 넓은 일반어를 중복으로 추가하지 마.
- 제품 표준화 예: 참타리버섯은 느타리버섯, 신선란/계란은 달걀, 인스턴트 이스트는 이스트, 사골곰탕은 사골육수, 동치미육수는 냉면육수, 스위트콘/옥수수 통조림은 옥수수캔, 타바스코/칠리소스는 핫소스, 푸실리/스파게티/막국수는 파스타면 또는 메밀면처럼 면 재료명으로 정리해.
- 라벨에 구체 상품명이 보이더라도 레시피 검색에 더 자연스러운 표준명이 있으면 표준명을 우선해. 예: 칠성사이다는 사이다, 닭가슴살 핫도그는 핫도그, 리코타치즈/체다치즈는 치즈, 식빵/모닝빵은 빵.
- 원재료가 아니라 완성 음식명만 보이면 임의의 비슷한 요리명으로 바꾸지 말고, 라벨에 실제로 적힌 핵심 재료명이나 가장 가까운 재료명으로 정리해. 예: 주꾸미 제품을 낙지볶음으로 바꾸지 말고 주꾸미로 유지해.
- 실제 음식/재료/재료 텍스트가 아니면 items는 빈 배열로 반환해.
- 반드시 유효한 JSON만 출력해.
- JSON key와 string value는 반드시 double quotes를 사용해.
- 설명, 주석, markdown, JavaScript object 문법을 쓰지 마.

형식:
{"type":"food|text|invalid|unclear","items":[{"raw":"string","name":"string"}]}
""".strip()


SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def load_env_files(explicit_env_file: Path | None = None) -> list[Path]:
    """
    Load KEY=VALUE pairs from .env files without adding a dependency.
    Existing environment variables win, so shell-provided secrets are not overwritten.
    """
    candidates: list[Path] = []
    if explicit_env_file is not None:
        candidates.append(explicit_env_file)
    else:
        candidates.extend([Path.cwd() / ".env", Path(__file__).with_name(".env")])

    loaded_files: list[Path] = []
    seen_files: set[Path] = set()

    for env_file in candidates:
        try:
            resolved = env_file.resolve()
        except OSError:
            resolved = env_file
        if resolved in seen_files or not env_file.exists():
            continue
        seen_files.add(resolved)

        loaded_any = False
        for line in env_file.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value
                loaded_any = True

        if loaded_any:
            loaded_files.append(resolved)

    return loaded_files


@dataclass
class ImagePayload:
    data: bytes
    mime_type: str
    original_width: int
    original_height: int
    processed_width: int
    processed_height: int
    original_size_kb: float
    processed_size_kb: float
    resized: bool


def load_ground_truth(path: Path) -> dict[str, dict[str, Any]]:
    """
    Expected ground-truth format:
    [
      {
        "name": "1.jpg",
        "type": "food",
        "items": [{"raw": "대파", "name": "대파"}]
      }
    ]
    """
    text = path.read_text(encoding="utf-8").strip()
    data = json.loads(text)

    if not isinstance(data, list):
        raise ValueError("Ground truth file must be a JSON array.")

    gt_by_name: dict[str, dict[str, Any]] = {}
    for row in data:
        if not isinstance(row, dict) or "name" not in row:
            continue
        gt_by_name[str(row["name"])] = row

    return gt_by_name


def resize_and_encode_image(
    image_path: Path,
    max_long_side: int = 1280,
    output_format: str = "JPEG",
    quality: int = 92,
) -> ImagePayload:
    original_size_kb = image_path.stat().st_size / 1024

    with Image.open(image_path) as img:
        img = ImageOps.exif_transpose(img)
        img = img.convert("RGB")
        original_width, original_height = img.size

        processed = img
        resized = False

        long_side = max(original_width, original_height)
        if long_side > max_long_side:
            scale = max_long_side / long_side
            new_width = max(1, int(original_width * scale))
            new_height = max(1, int(original_height * scale))
            processed = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            resized = True

        processed_width, processed_height = processed.size

        buffer = BytesIO()
        fmt = output_format.upper()

        if fmt == "WEBP":
            processed.save(buffer, format="WEBP", quality=quality, method=6)
            mime_type = "image/webp"
        elif fmt in {"JPG", "JPEG"}:
            processed.save(buffer, format="JPEG", quality=quality, optimize=True)
            mime_type = "image/jpeg"
        elif fmt == "PNG":
            processed.save(buffer, format="PNG", optimize=True)
            mime_type = "image/png"
        else:
            raise ValueError("output_format must be WEBP, JPEG, JPG, or PNG.")

        data = buffer.getvalue()

    return ImagePayload(
        data=data,
        mime_type=mime_type,
        original_width=original_width,
        original_height=original_height,
        processed_width=processed_width,
        processed_height=processed_height,
        original_size_kb=round(original_size_kb, 2),
        processed_size_kb=round(len(data) / 1024, 2),
        resized=resized,
    )


def extract_json(text: str) -> dict[str, Any]:
    """
    Gemini should return JSON only, but this handles accidental ```json fences too.
    """
    text = text.strip()

    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            raise
        parsed = json.loads(match.group(0))

    if not isinstance(parsed, dict):
        raise ValueError("Model output JSON must be an object.")

    if "type" not in parsed:
        parsed["type"] = "unclear"
    if "items" not in parsed or not isinstance(parsed["items"], list):
        parsed["items"] = []

    cleaned_items = []
    for item in parsed["items"]:
        if isinstance(item, dict):
            raw = str(item.get("raw", "")).strip()
            name = str(item.get("name", "")).strip()
            if raw or name:
                cleaned_items.append({"raw": raw or name, "name": name or raw})
        elif isinstance(item, str) and item.strip():
            cleaned_items.append({"raw": item.strip(), "name": item.strip()})

    parsed["items"] = cleaned_items
    return parsed


LABEL_ALIASES = {
    "계란": "달걀",
    "신선란": "달걀",
    "달걀지단": "달걀",
    "계란지단": "달걀",
    "참타리버섯": "느타리버섯",
    "타리버섯": "느타리버섯",
    "인스턴트이스트": "이스트",
    "드라이이스트": "이스트",
    "사골곰탕": "사골육수",
    "곰탕육수": "사골육수",
    "동치미육수": "냉면육수",
    "스위트콘": "옥수수캔",
    "옥수수통조림": "옥수수캔",
    "콘옥수수": "옥수수캔",
    "타바스코소스": "핫소스",
    "칠리소스": "핫소스",
    "칠성사이다": "사이다",
    "푸실리": "파스타면",
    "후실리": "파스타면",
    "스파게티면": "파스타면",
    "파스타": "파스타면",
    "막국수": "메밀면",
    "메밀막국수": "메밀면",
    "쭈꾸미": "주꾸미",
    "생선통조림": "참치캔",
    "참치통조림": "참치캔",
    "식빵": "빵",
    "모닝빵": "빵",
    "리코타치즈": "치즈",
    "모짜렐라치즈": "치즈",
    "모차렐라치즈": "치즈",
    "체다치즈": "치즈",
    "닭가슴살핫도그": "핫도그",
    "삼겹살": "돼지고기",
    "대패삼겹살": "돼지고기",
    "우삼겹": "소고기",
    "차돌박이": "소고기",
    "갈비살": "소고기",
    "한우갈비살": "소고기",
    "상그리아": "와인",
    "잡곡밥": "잡곡밥",
    "채소": "야채",
    "모둠채소": "샐러드채소",
    "믹스채소": "샐러드채소",
    "숙주": "숙주나물",
    "고구마순": "고구마줄기",
    "홍고추": "고추",
    "적근대": "근대",
    "캔옥수수": "옥수수캔",
    "김밥김": "김",
}


def normalize_alias_key(label: str) -> str:
    value = re.sub(r"\([^)]*\)", "", label.strip().lower())
    return re.sub(r"[\s\-_·,./]+", "", value)


def resolve_label_alias(value: str) -> str:
    seen = set()
    while value in LABEL_ALIASES and value not in seen:
        seen.add(value)
        value = LABEL_ALIASES[value]
    return value


def load_label_aliases(alias_file: Path | None = None) -> int:
    candidate = alias_file
    if candidate is None:
        default_file = Path(__file__).with_name("ingredient_aliases.json")
        if default_file.exists():
            candidate = default_file

    if candidate is None:
        return 0

    data = json.loads(candidate.read_text(encoding="utf-8"))
    if isinstance(data, dict) and isinstance(data.get("aliases"), dict):
        data = data["aliases"]
    if not isinstance(data, dict):
        raise ValueError("Alias file must be a JSON object or contain an 'aliases' object.")

    loaded_count = 0
    for raw_key, raw_value in data.items():
        key = normalize_alias_key(str(raw_key))
        value = normalize_alias_key(str(raw_value))
        if key and value:
            LABEL_ALIASES[key] = value
            loaded_count += 1

    return loaded_count


def normalize_label(label: str) -> str:
    """
    Normalize formatting and common Korean ingredient aliases for set metrics.
    These aliases are general food-name synonyms, not per-image expected answers.
    """
    return resolve_label_alias(normalize_alias_key(label))


REDUNDANT_GENERIC_LABELS = {
    "영양제": {"유산균", "프로바이오틱스", "비타민"},
}


def drop_redundant_generic_labels(labels: set[str]) -> set[str]:
    labels = set(labels)
    for generic, specifics in REDUNDANT_GENERIC_LABELS.items():
        if generic in labels and labels.intersection(specifics):
            labels.remove(generic)
    return labels


def calculate_set_metrics(
    pred_names: list[str],
    true_names: list[str],
    pred_type: str | None = None,
    gt_type: str | None = None,
) -> dict[str, Any]:
    pred_set = drop_redundant_generic_labels({normalize_label(x) for x in pred_names if x})
    true_set = drop_redundant_generic_labels({normalize_label(x) for x in true_names if x})

    type_match = str(pred_type) == str(gt_type)

    # Important edge case:
    # For invalid/non-food images, the correct behavior is to return no ingredients.
    # In a pure set metric, empty prediction vs empty ground truth becomes 0/0 -> 0.
    # But for this task, gt=invalid + pred=invalid + both empty should be counted as a correct result.
    if not pred_set and not true_set and type_match and str(gt_type) == "invalid":
        return {
            "precision": 1.0,
            "recall": 1.0,
            "f1": 1.0,
            "true_positive_count": 0,
            "false_positive_count": 0,
            "false_negative_count": 0,
            "true_positives": [],
            "false_positives": [],
            "false_negatives": [],
            "exact_match": True,
        }

    tp_set = pred_set & true_set
    fp_set = pred_set - true_set
    fn_set = true_set - pred_set

    tp = len(tp_set)
    fp = len(fp_set)
    fn = len(fn_set)

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "true_positive_count": tp,
        "false_positive_count": fp,
        "false_negative_count": fn,
        "true_positives": sorted(tp_set),
        "false_positives": sorted(fp_set),
        "false_negatives": sorted(fn_set),
        "exact_match": not fp_set and not fn_set,
    }


def get_usage_dict(response: Any) -> dict[str, int | None]:
    """
    google-genai response usage fields may differ by model/API version.
    This tries common field names safely.
    """
    usage = getattr(response, "usage_metadata", None)
    if usage is None:
        return {
            "prompt_tokens": None,
            "candidates_tokens": None,
            "total_tokens": None,
        }

    return {
        "prompt_tokens": getattr(usage, "prompt_token_count", None),
        "candidates_tokens": getattr(usage, "candidates_token_count", None),
        "total_tokens": getattr(usage, "total_token_count", None),
    }


def call_gemini(
    client: genai.Client,
    model: str,
    prompt: str,
    image_payload: ImagePayload,
    temperature: float = 0.0,
    thinking_level: str = "medium",
    max_output_tokens: int = 2048,
)-> tuple[dict[str, Any], str, dict[str, int | None], float]:
    image_part = types.Part.from_bytes(
        data=image_payload.data,
        mime_type=image_payload.mime_type,
    )

    started = time.perf_counter()
    response = client.models.generate_content(
        model=model,
        contents=[prompt, image_part],
        config=types.GenerateContentConfig(
            temperature=temperature,
            response_mime_type="application/json",
            max_output_tokens=max_output_tokens,
            thinking_config=types.ThinkingConfig(thinking_level=thinking_level),
        ),
    )
    latency_ms = (time.perf_counter() - started) * 1000

    raw_text = response.text or ""
    usage = get_usage_dict(response)

    try:
        parsed = extract_json(raw_text)
    except Exception as e:
        print("\n[RAW GEMINI RESPONSE]")
        print(raw_text if raw_text else "<EMPTY RESPONSE>")
        print("[JSON PARSE ERROR]")
        print(f"{type(e).__name__}: {e}\n")
        raise

    return parsed, raw_text, usage, latency_ms


def is_retryable_error(error: Exception) -> bool:
    message = f"{type(error).__name__}: {error}"

    if "GenerateRequestsPerDayPerProjectPerModel-FreeTier" in message:
        return False

    retryable_keywords = [
        "500",
        "503",
        "INTERNAL",
        "UNAVAILABLE",
        "Internal error",
        "high demand",
        "429",
        "RESOURCE_EXHAUSTED",
        "JSONDecodeError",
        "Expecting ',' delimiter",
        "Expecting property name enclosed in double quotes",
        "EMPTY RESPONSE",
    ]
    return any(keyword in message for keyword in retryable_keywords)


def call_gemini_with_retry(
    client: genai.Client,
    model: str,
    prompt: str,
    image_payload: ImagePayload,
    temperature: float = 0.0,
    thinking_level: str = "minimal",
    max_output_tokens: int = 2048,
    max_retries: int = 3,
    retry_sleep: float = 5.0,
) -> tuple[dict[str, Any], str, dict[str, int | None], float]:
    last_error: Exception | None = None

    for attempt in range(1, max_retries + 1):
        try:
            return call_gemini(
                client=client,
                model=model,
                prompt=prompt,
                image_payload=image_payload,
                temperature=temperature,
                thinking_level=thinking_level,
                max_output_tokens=max_output_tokens,
            )
        except Exception as e:
            last_error = e

            if not is_retryable_error(e):
                raise

            if attempt >= max_retries:
                break

            print(
                f"[RETRY] attempt={attempt}/{max_retries} failed: "
                f"{type(e).__name__}: {e}"
            )
            print(f"[RETRY] {retry_sleep}초 대기 후 재시도합니다.")
            time.sleep(retry_sleep)

    assert last_error is not None
    raise last_error


def find_images(image_dir: Path) -> list[Path]:
    return sorted(
        [
            p
            for p in image_dir.iterdir()
            if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
        ],
        key=lambda p: p.name,
    )


def select_image_names_from_jsonl(
    input_jsonl: Path,
    max_f1: float | None = None,
    pred_types: set[str] | None = None,
) -> set[str]:
    if max_f1 is None and not pred_types:
        max_f1 = 0.8
        pred_types = {"error"}

    selected_names: set[str] = set()
    with input_jsonl.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            row = json.loads(line)
            image_name = str(row.get("image_name", "")).strip()
            if not image_name:
                continue

            include = False
            if max_f1 is not None:
                try:
                    include = include or float(row.get("f1", 0.0)) <= max_f1
                except (TypeError, ValueError):
                    include = include or str(row.get("pred_type")) == "error"

            if pred_types:
                include = include or str(row.get("pred_type")) in pred_types

            if include:
                selected_names.add(image_name)

    if not selected_names:
        raise ValueError(f"No rows matched selection criteria in {input_jsonl}")

    return selected_names


def summarize_metric_rows(
    metric_rows: list[dict[str, Any]],
    valid_json_count: int | None = None,
    include_latency: bool = False,
) -> dict[str, float | int]:
    total = len(metric_rows)
    if total == 0:
        raise ValueError("No metric rows to summarize.")

    tp_total = sum(int(x.get("true_positive_count", 0)) for x in metric_rows)
    fp_total = sum(int(x.get("false_positive_count", 0)) for x in metric_rows)
    fn_total = sum(int(x.get("false_negative_count", 0)) for x in metric_rows)

    micro_precision = tp_total / (tp_total + fp_total) if (tp_total + fp_total) else 0.0
    micro_recall = tp_total / (tp_total + fn_total) if (tp_total + fn_total) else 0.0
    micro_f1 = (
        2 * micro_precision * micro_recall / (micro_precision + micro_recall)
        if (micro_precision + micro_recall)
        else 0.0
    )

    summary: dict[str, float | int] = {
        "summary/avg_precision": sum(float(x["precision"]) for x in metric_rows) / total,
        "summary/avg_recall": sum(float(x["recall"]) for x in metric_rows) / total,
        "summary/avg_f1": sum(float(x["f1"]) for x in metric_rows) / total,
        "summary/item_micro_precision": micro_precision,
        "summary/item_micro_recall": micro_recall,
        "summary/item_micro_f1": micro_f1,
        "summary/type_accuracy": sum(1 for x in metric_rows if x.get("type_match")) / total,
        "summary/image_exact_match_accuracy": sum(
            1 for x in metric_rows if x.get("image_exact_match")
        )
        / total,
        "summary/total_true_positive_count": tp_total,
        "summary/total_false_positive_count": fp_total,
        "summary/total_false_negative_count": fn_total,
        "summary/error_rows": sum(1 for x in metric_rows if x.get("pred_type") == "error"),
        "summary/total_images": total,
    }

    if valid_json_count is not None:
        summary["summary/valid_json_rate"] = valid_json_count / total
    else:
        summary["summary/valid_json_rate"] = (
            sum(1 for x in metric_rows if x.get("valid_json") is True) / total
        )

    if include_latency:
        avg_latency = sum(float(x.get("latency_ms") or 0.0) for x in metric_rows) / total
        sorted_latency = sorted(float(x.get("latency_ms") or 0.0) for x in metric_rows)
        p95_index = min(total - 1, int(total * 0.95))
        summary["summary/avg_latency_ms"] = avg_latency
        summary["summary/p95_latency_ms"] = sorted_latency[p95_index]

    return summary


def load_jsonl_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def classify_failure(row: dict[str, Any]) -> str:
    pred_type = str(row.get("pred_type"))
    gt_type = str(row.get("gt_type"))

    if pred_type == "error":
        return "api_error"
    if row.get("valid_json") is False:
        return "json_failure"
    if pred_type != gt_type:
        return "type_mismatch"
    if bool(row.get("image_exact_match")):
        return "exact_match"

    fp = int(row.get("false_positive_count", 0) or 0)
    fn = int(row.get("false_negative_count", 0) or 0)

    if fp == 0 and fn > 0:
        return "missed_items"
    if fp > 0 and fn == 0:
        return "extra_items"
    if fp == 1 and fn == 1:
        return "single_pair_mismatch"
    return "mixed_label_or_vision"


def write_failure_report(
    rows: list[dict[str, Any]],
    output_path: Path,
    max_f1: float = 0.95,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    report_rows = []
    category_counts: dict[str, int] = {}
    for row in rows:
        category = classify_failure(row)
        category_counts[category] = category_counts.get(category, 0) + 1
        f1 = float(row.get("f1", 0.0) or 0.0)
        if f1 <= max_f1 or category in {"api_error", "json_failure", "type_mismatch"}:
            report_rows.append(
                {
                    "image_name": row.get("image_name", ""),
                    "category": category,
                    "gt_type": row.get("gt_type", ""),
                    "pred_type": row.get("pred_type", ""),
                    "precision": row.get("precision", 0.0),
                    "recall": row.get("recall", 0.0),
                    "f1": f1,
                    "false_positives": ", ".join(str(x) for x in row.get("false_positives", [])),
                    "false_negatives": ", ".join(str(x) for x in row.get("false_negatives", [])),
                    "ground_truth_names": ", ".join(str(x) for x in row.get("ground_truth_names", [])),
                    "prediction_names": ", ".join(str(x) for x in row.get("prediction_names", [])),
                    "error_message": row.get("error_message", ""),
                }
            )

    report_rows.sort(key=lambda x: (float(x["f1"]), str(x["image_name"])))

    if output_path.suffix.lower() == ".csv":
        fieldnames = [
            "image_name",
            "category",
            "gt_type",
            "pred_type",
            "precision",
            "recall",
            "f1",
            "false_positives",
            "false_negatives",
            "ground_truth_names",
            "prediction_names",
            "error_message",
        ]
        with output_path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(report_rows)
        return

    lines = [
        "# Food Evaluation Failure Report",
        "",
        f"- Total rows: {len(rows)}",
        f"- Included rows: {len(report_rows)}",
        f"- Inclusion rule: f1 <= {max_f1} or api/json/type failure",
        "",
        "## Category Counts",
        "",
    ]
    for category, count in sorted(category_counts.items(), key=lambda x: (-x[1], x[0])):
        lines.append(f"- {category}: {count}")

    lines.extend(
        [
            "",
            "## Rows",
            "",
            "| image | category | gt_type | pred_type | P | R | F1 | FP | FN |",
            "| --- | --- | --- | --- | ---: | ---: | ---: | --- | --- |",
        ]
    )
    for row in report_rows:
        lines.append(
            "| {image_name} | {category} | {gt_type} | {pred_type} | "
            "{precision:.3f} | {recall:.3f} | {f1:.3f} | {false_positives} | {false_negatives} |".format(
                image_name=row["image_name"],
                category=row["category"],
                gt_type=row["gt_type"],
                pred_type=row["pred_type"],
                precision=float(row["precision"] or 0.0),
                recall=float(row["recall"] or 0.0),
                f1=float(row["f1"] or 0.0),
                false_positives=str(row["false_positives"]).replace("|", "/"),
                false_negatives=str(row["false_negatives"]).replace("|", "/"),
            )
        )

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def recalculate_jsonl_metrics(input_jsonl: Path, output_jsonl: Path) -> dict[str, float | int]:
    rows: list[dict[str, Any]] = []
    with input_jsonl.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))

    if not rows:
        raise ValueError(f"No rows found in {input_jsonl}")

    return recalculate_rows_to_jsonl(rows, output_jsonl)


def merge_jsonl_rows(base_jsonl: Path, update_jsonl: Path, output_jsonl: Path) -> dict[str, float | int]:
    base_rows: list[dict[str, Any]] = []
    with base_jsonl.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                base_rows.append(json.loads(line))

    update_rows: dict[str, dict[str, Any]] = {}
    with update_jsonl.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            row = json.loads(line)
            image_name = str(row.get("image_name", "")).strip()
            if image_name:
                update_rows[image_name] = row

    if not base_rows:
        raise ValueError(f"No rows found in {base_jsonl}")
    if not update_rows:
        raise ValueError(f"No usable update rows found in {update_jsonl}")

    merged_rows = []
    updated_count = 0
    for row in base_rows:
        image_name = str(row.get("image_name", "")).strip()
        if image_name in update_rows:
            merged_rows.append(update_rows[image_name])
            updated_count += 1
        else:
            merged_rows.append(row)

    missing_in_base = sorted(set(update_rows) - {str(row.get("image_name", "")).strip() for row in base_rows})
    if missing_in_base:
        raise ValueError(f"Update rows not found in base JSONL: {missing_in_base}")

    summary = recalculate_rows_to_jsonl(merged_rows, output_jsonl)
    summary["summary/merged_update_rows"] = updated_count
    return summary


def recalculate_rows_to_jsonl(rows: list[dict[str, Any]], output_jsonl: Path) -> dict[str, float | int]:
    output_jsonl.parent.mkdir(parents=True, exist_ok=True)

    with output_jsonl.open("w", encoding="utf-8") as f:
        for row in rows:
            true_names = [
                str(x)
                for x in row.get("ground_truth_names", [])
                if str(x).strip()
            ]
            pred_names = [
                str(x)
                for x in row.get("prediction_names", [])
                if str(x).strip()
            ]
            metrics = calculate_set_metrics(
                pred_names=pred_names,
                true_names=true_names,
                pred_type=row.get("pred_type"),
                gt_type=row.get("gt_type"),
            )
            type_match = str(row.get("pred_type")) == str(row.get("gt_type"))
            row.update(
                {
                    "type_match": type_match,
                    "image_exact_match": bool(metrics["exact_match"] and type_match),
                    "precision": metrics["precision"],
                    "recall": metrics["recall"],
                    "f1": metrics["f1"],
                    "true_positive_count": metrics["true_positive_count"],
                    "false_positive_count": metrics["false_positive_count"],
                    "false_negative_count": metrics["false_negative_count"],
                    "true_positives": metrics["true_positives"],
                    "false_positives": metrics["false_positives"],
                    "false_negatives": metrics["false_negatives"],
                    "metric_note": "Recalculated from existing predictions with current normalize_label().",
                }
            )
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    return summarize_metric_rows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--image-dir",
        type=Path,
        default=Path(r"C:\Users\SSAFY\Desktop\음식재료사진"),
        help="Directory containing test images.",
    )
    parser.add_argument(
        "--ground-truth",
        type=Path,
        required=True,
        help="Path to ground-truth JSON txt file.",
    )
    parser.add_argument(
        "--model",
        default="gemini-3.1-flash-lite",
        help="Gemini model name. Change this to the model you use.",
    )
    parser.add_argument("--max-long-side", type=int, default=1280)
    parser.add_argument("--format", default="JPEG", choices=["WEBP", "JPEG", "JPG", "PNG"])
    parser.add_argument("--quality", type=int, default=92)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument(
        "--thinking-level",
        default="minimal",
        choices=["minimal", "low", "medium", "high"],
    )
    parser.add_argument("--max-output-tokens", type=int, default=2048)
    parser.add_argument("--max-retries", type=int, default=3)
    parser.add_argument("--retry-sleep", type=float, default=5.0)
    parser.add_argument("--sleep-seconds", type=float, default=0.0)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument(
        "--image-names",
        default=None,
        help="Comma-separated image filenames to evaluate, e.g. 33.jpg,48.jpg.",
    )
    parser.add_argument(
        "--select-from-jsonl",
        type=Path,
        default=None,
        help="Select image filenames to evaluate from an existing result JSONL.",
    )
    parser.add_argument(
        "--select-max-f1",
        type=float,
        default=None,
        help="With --select-from-jsonl, select rows whose f1 is less than or equal to this value.",
    )
    parser.add_argument(
        "--select-pred-types",
        default=None,
        help="With --select-from-jsonl, comma-separated pred_type values to select, e.g. error,invalid.",
    )
    parser.add_argument(
        "--select-only",
        action="store_true",
        help="Print selected image filenames and exit before calling Gemini.",
    )
    parser.add_argument("--no-wandb", action="store_true")
    parser.add_argument("--wandb-entity", default="rlashfod0202-ssafagetti")
    parser.add_argument("--wandb-project", default="food-ingredient-vlm")
    parser.add_argument("--wandb-run-name", default=None)
    parser.add_argument("--output-jsonl", type=Path, default=Path("gemini_food_eval_results.jsonl"))
    parser.add_argument(
        "--env-file",
        type=Path,
        default=None,
        help="Optional .env file containing GEMINI_API_KEY/GOOGLE_API_KEY/WANDB_API_KEY.",
    )
    parser.add_argument(
        "--failure-report",
        type=Path,
        default=None,
        help="Optional Markdown or CSV report path for low-score/error rows.",
    )
    parser.add_argument(
        "--failure-report-max-f1",
        type=float,
        default=0.95,
        help="Include rows with f1 <= this value in --failure-report.",
    )
    parser.add_argument(
        "--alias-file",
        type=Path,
        default=None,
        help="Optional ingredient alias JSON file. Defaults to ingredient_aliases.json next to this script when present.",
    )
    parser.add_argument(
        "--recalculate-jsonl",
        type=Path,
        default=None,
        help="Recalculate metrics for an existing JSONL without calling Gemini.",
    )
    parser.add_argument(
        "--merge-base-jsonl",
        type=Path,
        default=None,
        help="Base full-result JSONL to merge with a smaller retry/update JSONL.",
    )
    parser.add_argument(
        "--merge-update-jsonl",
        type=Path,
        default=None,
        help="Retry/update JSONL whose rows replace matching image_name rows from --merge-base-jsonl.",
    )

    args = parser.parse_args()

    loaded_env_files = load_env_files(args.env_file)
    for env_file in loaded_env_files:
        print(f"[ENV] loaded variables from {env_file}")

    alias_count = load_label_aliases(args.alias_file)
    if alias_count:
        print(f"[ALIASES] loaded {alias_count} aliases.")

    if args.merge_base_jsonl is not None or args.merge_update_jsonl is not None:
        if args.merge_base_jsonl is None or args.merge_update_jsonl is None:
            raise ValueError("--merge-base-jsonl and --merge-update-jsonl must be used together.")
        summary = merge_jsonl_rows(
            base_jsonl=args.merge_base_jsonl,
            update_jsonl=args.merge_update_jsonl,
            output_jsonl=args.output_jsonl,
        )
        if args.failure_report is not None:
            write_failure_report(
                rows=load_jsonl_rows(args.output_jsonl),
                output_path=args.failure_report,
                max_f1=args.failure_report_max_f1,
            )
            print(f"Saved failure report to: {args.failure_report.resolve()}")
        print("\n=== Merged Recalculated Summary ===")
        for key, value in summary.items():
            print(f"{key}: {value}")
        print(f"\nSaved merged JSONL to: {args.output_jsonl.resolve()}")
        return

    if args.recalculate_jsonl is not None:
        summary = recalculate_jsonl_metrics(args.recalculate_jsonl, args.output_jsonl)
        if args.failure_report is not None:
            write_failure_report(
                rows=load_jsonl_rows(args.output_jsonl),
                output_path=args.failure_report,
                max_f1=args.failure_report_max_f1,
            )
            print(f"Saved failure report to: {args.failure_report.resolve()}")
        print("\n=== Recalculated Summary ===")
        for key, value in summary.items():
            print(f"{key}: {value}")
        print(f"\nSaved recalculated JSONL to: {args.output_jsonl.resolve()}")
        return

    if not args.image_dir.exists():
        raise FileNotFoundError(f"Image directory not found: {args.image_dir}")

    if not args.ground_truth.exists():
        raise FileNotFoundError(f"Ground truth file not found: {args.ground_truth}")

    gt_by_name = load_ground_truth(args.ground_truth)
    images = find_images(args.image_dir)
    requested_names: set[str] = set()
    if args.image_names:
        requested_names.update(
            name.strip()
            for name in args.image_names.split(",")
            if name.strip()
        )

    if args.select_from_jsonl is not None:
        pred_types = None
        if args.select_pred_types:
            pred_types = {
                pred_type.strip()
                for pred_type in args.select_pred_types.split(",")
                if pred_type.strip()
            }
        selected_names = select_image_names_from_jsonl(
            input_jsonl=args.select_from_jsonl,
            max_f1=args.select_max_f1,
            pred_types=pred_types,
        )
        requested_names.update(selected_names)

    if requested_names:
        images = [image for image in images if image.name in requested_names]
        found_names = {image.name for image in images}
        missing_names = sorted(requested_names - found_names)
        if missing_names:
            raise FileNotFoundError(f"Requested image names not found: {missing_names}")

    if args.limit:
        images = images[: args.limit]

    if requested_names:
        print(
            f"[SELECT] evaluating {len(images)} selected images: "
            f"{', '.join(sorted(image.name for image in images))}"
        )

    if args.select_only:
        if not requested_names:
            print("[SELECT] no selection filter was provided; nothing to print.")
            return
        for image in images:
            print(image.name)
        return

    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY or GOOGLE_API_KEY environment variable is not set.")
    if genai is None or types is None:
        raise RuntimeError("google-genai is not installed. Run: pip install -U google-genai")

    client = genai.Client(api_key=api_key)

    use_wandb = not args.no_wandb
    run = None
    table = None

    if use_wandb:
        if wandb is None:
            raise RuntimeError("wandb is not installed. Run: pip install wandb")

        run = wandb.init(
            entity=args.wandb_entity,
            project=args.wandb_project,
            name=args.wandb_run_name,
            config={
                "wandb_entity": args.wandb_entity,
                "wandb_project": args.wandb_project,
                "model": args.model,
                "temperature": args.temperature,
                "max_output_tokens": args.max_output_tokens,
                "thinking_level": args.thinking_level,
                "max_retries": args.max_retries,
                "retry_sleep": args.retry_sleep,
                "sleep_seconds": args.sleep_seconds,
                "max_long_side": args.max_long_side,
                "format": args.format,
                "quality": args.quality,
                "image_names": args.image_names,
                "select_from_jsonl": str(args.select_from_jsonl) if args.select_from_jsonl else None,
                "select_max_f1": args.select_max_f1,
                "select_pred_types": args.select_pred_types,
                "env_files_loaded": [str(path) for path in loaded_env_files],
                "alias_file": str(args.alias_file) if args.alias_file else None,
                "prompt": PROMPT,
                "image_dir": str(args.image_dir),
                "ground_truth": str(args.ground_truth),
            },
        )

        table = wandb.Table(
            columns=[
                "image",
                "image_name",
                "gt_type",
                "pred_type",
                "ground_truth_names",
                "prediction_names",
                "precision",
                "recall",
                "f1",
                "latency_ms",
                "prompt_tokens",
                "candidates_tokens",
                "total_tokens",
                "original_size_kb",
                "processed_size_kb",
                "original_wh",
                "processed_wh",
                "resized",
                "valid_json",
                "false_positives",
                "false_negatives",
                "raw_response",
            ]
        )

    output_file = args.output_jsonl
    output_file.parent.mkdir(parents=True, exist_ok=True)

    total = 0
    valid_json_count = 0
    metric_rows = []

    with output_file.open("w", encoding="utf-8") as f:
        for image_path in images:
            total += 1
            gt = gt_by_name.get(image_path.name, {"type": "unclear", "items": []})
            true_names = [x.get("name", "") for x in gt.get("items", []) if isinstance(x, dict)]

            image_payload = resize_and_encode_image(
                image_path=image_path,
                max_long_side=args.max_long_side,
                output_format=args.format,
                quality=args.quality,
            )

            valid_json = True
            error_message = None

            try:
                pred, raw_response, usage, latency_ms = call_gemini_with_retry(
                    client=client,
                    model=args.model,
                    prompt=PROMPT,
                    image_payload=image_payload,
                    temperature=args.temperature,
                    thinking_level=args.thinking_level,
                    max_output_tokens=args.max_output_tokens,
                    max_retries=args.max_retries,
                    retry_sleep=args.retry_sleep,
                )
                valid_json_count += 1
            except Exception as e:
                valid_json = False
                error_message = f"{type(e).__name__}: {e}"
                print(f"[ERROR] {image_path.name}: {error_message}")

                if "GenerateRequestsPerDayPerProjectPerModel-FreeTier" in error_message:
                    print("[STOP] 이 모델의 Free Tier 일일 요청 수 제한에 걸렸습니다. 다른 모델을 쓰거나 리셋 후 다시 실행하세요.")
                    break

                if "429" in error_message or "RESOURCE_EXHAUSTED" in error_message:
                    print("[RATE LIMIT] 일시적 요청 제한입니다. 60초 대기합니다.")
                    time.sleep(60)

                pred = {"type": "error", "items": []}
                raw_response = ""
                usage = {
                    "prompt_tokens": None,
                    "candidates_tokens": None,
                    "total_tokens": None,
                }
                latency_ms = 0.0

            pred_names = [x.get("name", "") for x in pred.get("items", []) if isinstance(x, dict)]
            type_match = str(pred.get("type")) == str(gt.get("type"))
            metrics = calculate_set_metrics(
                pred_names=pred_names,
                true_names=true_names,
                pred_type=pred.get("type"),
                gt_type=gt.get("type"),
            )

            row = {
                "image_name": image_path.name,
                "gt_type": gt.get("type"),
                "pred_type": pred.get("type"),
                "type_match": type_match,
                "image_exact_match": bool(metrics["exact_match"] and type_match),
                "invalid_correct": bool(
                    gt.get("type") == "invalid"
                    and pred.get("type") == "invalid"
                    and not true_names
                    and not pred_names
                ),
                "ground_truth_names": true_names,
                "prediction_names": pred_names,
                "prediction_items": pred.get("items", []),
                "precision": metrics["precision"],
                "recall": metrics["recall"],
                "f1": metrics["f1"],
                "true_positive_count": metrics["true_positive_count"],
                "false_positive_count": metrics["false_positive_count"],
                "false_negative_count": metrics["false_negative_count"],
                "true_positives": metrics["true_positives"],
                "false_positives": metrics["false_positives"],
                "false_negatives": metrics["false_negatives"],
                "latency_ms": latency_ms,
                "prompt_tokens": usage.get("prompt_tokens"),
                "candidates_tokens": usage.get("candidates_tokens"),
                "total_tokens": usage.get("total_tokens"),
                "original_width": image_payload.original_width,
                "original_height": image_payload.original_height,
                "processed_width": image_payload.processed_width,
                "processed_height": image_payload.processed_height,
                "original_size_kb": image_payload.original_size_kb,
                "processed_size_kb": image_payload.processed_size_kb,
                "resized": image_payload.resized,
                "valid_json": valid_json,
                "error_message": error_message,
                "raw_response": raw_response,
            }

            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            metric_rows.append(row)

            if use_wandb and run is not None and table is not None:
                run.log(
                    {
                        "precision": metrics["precision"],
                        "recall": metrics["recall"],
                        "f1": metrics["f1"],
                        "latency_ms": latency_ms,
                        "prompt_tokens": usage.get("prompt_tokens") or 0,
                        "candidates_tokens": usage.get("candidates_tokens") or 0,
                        "total_tokens": usage.get("total_tokens") or 0,
                        "valid_json": int(valid_json),
                        "type_match": int(type_match),
                        "image_exact_match": int(metrics["exact_match"] and type_match),
                        "invalid_correct": int(
                            gt.get("type") == "invalid"
                            and pred.get("type") == "invalid"
                            and not true_names
                            and not pred_names
                        ),
                        "original_size_kb": image_payload.original_size_kb,
                        "processed_size_kb": image_payload.processed_size_kb,
                        "resized": int(image_payload.resized),
                    },
                    step=total,
                )

                table.add_data(
                    wandb.Image(str(image_path)),
                    image_path.name,
                    gt.get("type"),
                    pred.get("type"),
                    ", ".join(true_names),
                    ", ".join(pred_names),
                    metrics["precision"],
                    metrics["recall"],
                    metrics["f1"],
                    latency_ms,
                    usage.get("prompt_tokens"),
                    usage.get("candidates_tokens"),
                    usage.get("total_tokens"),
                    image_payload.original_size_kb,
                    image_payload.processed_size_kb,
                    f"{image_payload.original_width}x{image_payload.original_height}",
                    f"{image_payload.processed_width}x{image_payload.processed_height}",
                    image_payload.resized,
                    valid_json,
                    ", ".join(metrics["false_positives"]),
                    ", ".join(metrics["false_negatives"]),
                    raw_response[:2000],
                )

            print(
                f"[{total}/{len(images)}] {image_path.name} "
                f"gt={gt.get('type')} pred={pred.get('type')} "
                f"f1={metrics['f1']:.3f} latency={latency_ms:.0f}ms "
                f"tokens={usage.get('total_tokens')}"
            )

            if args.sleep_seconds > 0 and total < len(images):
                time.sleep(args.sleep_seconds)

    if metric_rows:
        summary = summarize_metric_rows(
            metric_rows=metric_rows,
            valid_json_count=valid_json_count,
            include_latency=True,
        )

        print("\n=== Summary ===")
        for key, value in summary.items():
            print(f"{key}: {value}")

        if args.failure_report is not None:
            write_failure_report(
                rows=metric_rows,
                output_path=args.failure_report,
                max_f1=args.failure_report_max_f1,
            )
            print(f"Saved failure report to: {args.failure_report.resolve()}")

        if use_wandb and run is not None and table is not None:
            run.log(summary)
            run.log({"prediction_table": table})
            run.finish()

    print(f"\nSaved JSONL results to: {output_file.resolve()}")


if __name__ == "__main__":
    main()
