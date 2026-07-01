import argparse
import json
import random
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

from pyvi import ViTokenizer
from sklearn.model_selection import train_test_split
from underthesea import word_tokenize

sys.stdout.reconfigure(encoding="utf-8")

ASPECT_LABELS = ["Pin", "Camera", "Màn hình", "Hiệu năng", "Thiết kế", "Giá"]
RANDOM_SEED = 42

ASPECT_TERMS = {
    "Pin": [
        "pin",
        "sạc",
        "sạc pin",
        "sạc nhanh",
        "củ sạc",
        "thời lượng pin",
        "dung lượng pin",
        "chai pin",
        "hao pin",
        "tụt pin",
        "trâu pin",
        "20w",
        "watt",
    ],
    "Camera": [
        "camera",
        "cam",
        "cammera",
        "camera trước",
        "camera sau",
        "chụp",
        "chụp ảnh",
        "chụp đêm",
        "ảnh",
        "hình",
        "quay",
        "quay video",
        "selfie",
        "zoom",
        "chống rung",
        "xoá phông",
        "xóa phông",
    ],
    "Màn hình": [
        "màn hình",
        "màn",
        "display",
        "oled",
        "amoled",
        "lcd",
        "ips",
        "tần số quét",
        "độ sáng",
        "viền màn hình",
        "viền",
        "notch",
        "tai thỏ",
        "120hz",
        "90hz",
        "60hz",
    ],
    "Hiệu năng": [
        "hiệu năng",
        "cấu hình",
        "chip",
        "cpu",
        "gpu",
        "ram",
        "rom",
        "bộ nhớ",
        "lag",
        "giật",
        "mượt",
        "game",
        "gaming",
        "nóng máy",
        "snapdragon",
        "exynos",
        "dimensity",
        "antutu",
    ],
    "Thiết kế": [
        "thiết kế",
        "ngoại hình",
        "vỏ",
        "khung",
        "viền",
        "màu",
        "màu sắc",
        "cầm",
        "cầm nắm",
        "mỏng",
        "dày",
        "nặng",
        "nhẹ",
        "hoàn thiện",
    ],
    "Giá": [
        "giá",
        "tầm giá",
        "mức giá",
        "phân khúc",
        "tiền",
        "triệu",
        "tr",
        "rẻ",
        "đắt",
        "mắc",
        "sale",
        "khuyến mãi",
    ],
}


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFC", value.lower())
    value = value.replace("đ", "d")
    value = "".join(
        char for char in unicodedata.normalize("NFD", value)
        if unicodedata.category(char) != "Mn"
    )
    return re.sub(r"\s+", " ", value).strip()


def syllable_tokens(text: str) -> list[str]:
    tokens: list[str] = []
    for token in word_tokenize(text):
        tokens.extend(str(token).split())
    return tokens


def phobert_tokens(text: str) -> list[str]:
    return ViTokenizer.tokenize(text).split()


def candidate_terms(aspect: str) -> list[list[str]]:
    terms = sorted(ASPECT_TERMS[aspect], key=lambda term: len(syllable_tokens(term)), reverse=True)
    return [syllable_tokens(term) for term in terms]


def find_matches(tokens: list[str], aspect: str) -> list[tuple[int, int]]:
    normalized_tokens = [normalize_text(token) for token in tokens]
    matches: list[tuple[int, int]] = []

    for term_tokens in candidate_terms(aspect):
        normalized_term = [normalize_text(token) for token in term_tokens]
        if not normalized_term:
            continue

        length = len(normalized_term)
        for start in range(0, len(tokens) - length + 1):
            end = start + length
            if normalized_tokens[start:end] == normalized_term:
                matches.append((start, end))

    return matches


def apply_span(tags: list[str], start: int, end: int, aspect: str) -> bool:
    if any(tag != "O" for tag in tags[start:end]):
        return False
    tags[start] = f"B-{aspect}"
    for idx in range(start + 1, end):
        tags[idx] = f"I-{aspect}"
    return True


def build_boundary_tags(sentence: str, aspects: set[str]) -> tuple[list[str], list[str], list[str]]:
    tokens = syllable_tokens(sentence)
    tags = ["O"] * len(tokens)
    matched_aspects: list[str] = []

    aspect_order = sorted(
        aspects,
        key=lambda aspect: max((len(term) for term in candidate_terms(aspect)), default=0),
        reverse=True,
    )

    for aspect in aspect_order:
        aspect_matches = find_matches(tokens, aspect)
        for start, end in aspect_matches:
            if apply_span(tags, start, end, aspect):
                matched_aspects.append(aspect)
                break

    return tokens, tags, sorted(set(matched_aspects))


def map_syllable_tags_to_words(
    syllables: list[str],
    tags: list[str],
    words: list[str],
) -> list[str] | None:
    word_tags: list[str] = []
    syllable_idx = 0

    for word in words:
        word_clean = normalize_text(word.replace("_", ""))
        current_syllables: list[str] = []
        current_tags: list[str] = []

        while syllable_idx < len(syllables):
            current_syllables.append(normalize_text(syllables[syllable_idx]))
            current_tags.append(tags[syllable_idx])
            syllable_idx += 1

            if "".join(current_syllables) == word_clean:
                break

        if "".join(current_syllables) != word_clean:
            return None

        entity_tags = [tag for tag in current_tags if tag != "O"]
        if not entity_tags:
            word_tags.append("O")
            continue

        entity_types = {tag[2:] for tag in entity_tags}
        if len(entity_types) != 1:
            return None

        entity_type = next(iter(entity_types))
        prefix = "B" if any(tag.startswith("B-") for tag in entity_tags) else "I"
        word_tags.append(f"{prefix}-{entity_type}")

    if syllable_idx != len(syllables):
        return None

    for idx, tag in enumerate(word_tags):
        if not tag.startswith("I-"):
            continue
        entity_type = tag[2:]
        previous = word_tags[idx - 1] if idx > 0 else "O"
        if previous == "O" or previous[2:] != entity_type:
            word_tags[idx] = f"B-{entity_type}"

    return word_tags


def load_annotation_records(input_files: list[Path]) -> list[dict]:
    records: list[dict] = []
    for path in input_files:
        if not path.exists():
            print(f"[WARN] Missing input file: {path}")
            continue
        with path.open(encoding="utf-8") as file:
            records.extend(json.load(file))
        print(f"Loaded {path.name}")
    return records


def group_sentence_aspects(records: list[dict]) -> dict[str, set[str]]:
    grouped: dict[str, set[str]] = defaultdict(set)
    none_sentences: set[str] = set()

    for item in records:
        sentence = str(item.get("sentence", "")).strip()
        aspect = str(item.get("aspect_label", "NONE")).strip()
        if not sentence:
            continue
        if aspect in ASPECT_LABELS:
            grouped[sentence].add(aspect)
        elif aspect == "NONE":
            none_sentences.add(sentence)

    for sentence in none_sentences:
        grouped.setdefault(sentence, set())

    return grouped


def build_records(grouped: dict[str, set[str]], none_ratio: float) -> list[dict]:
    aspect_records: list[dict] = []
    none_records: list[dict] = []
    missed_records: list[dict] = []

    for sentence, aspects in grouped.items():
        tokens, tags, matched_aspects = build_boundary_tags(sentence, aspects)
        record = {
            "sentence": sentence,
            "tokens": tokens,
            "ner_tags": tags,
            "aspects": matched_aspects,
        }

        if matched_aspects:
            aspect_records.append(record)
        elif aspects:
            missed_records.append({**record, "expected_aspects": sorted(aspects)})
        else:
            none_records.append(record)

    target_none_count = int(len(aspect_records) * none_ratio / (1.0 - none_ratio))
    selected_none = none_records if target_none_count >= len(none_records) else random.sample(none_records, target_none_count)

    final_records = aspect_records + selected_none
    random.shuffle(final_records)

    print(f"Aspect records: {len(aspect_records)}")
    print(f"Selected NONE records: {len(selected_none)}")
    print(f"Missed aspect records: {len(missed_records)}")
    return final_records, missed_records


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")


def export_datasets(records: list[dict], output_root: Path, missed_records: list[dict]) -> None:
    train_rows, val_rows = train_test_split(records, test_size=0.2, random_state=RANDOM_SEED)

    velectra_root = output_root / "velectra"
    write_jsonl(velectra_root / "train.jsonl", train_rows)
    write_jsonl(velectra_root / "val.jsonl", val_rows)

    phobert_train: list[dict] = []
    phobert_val: list[dict] = []
    phobert_conflicts: list[dict] = []

    for target, source in ((phobert_train, train_rows), (phobert_val, val_rows)):
        for row in source:
            words = phobert_tokens(row["sentence"])
            word_tags = map_syllable_tags_to_words(row["tokens"], row["ner_tags"], words)
            if word_tags is None:
                phobert_conflicts.append(row)
                continue
            target.append({
                "sentence": row["sentence"],
                "tokens": words,
                "ner_tags": word_tags,
                "aspects": row["aspects"],
            })

    phobert_root = output_root / "phobert"
    write_jsonl(phobert_root / "train.jsonl", phobert_train)
    write_jsonl(phobert_root / "val.jsonl", phobert_val)

    review_root = output_root / "review"
    write_jsonl(review_root / "missed_aspect_sentences.jsonl", missed_records)
    write_jsonl(review_root / "phobert_alignment_conflicts.jsonl", phobert_conflicts)

    print(f"Exported vELECTRA train/val: {len(train_rows)}/{len(val_rows)}")
    print(f"Exported PhoBERT train/val: {len(phobert_train)}/{len(phobert_val)}")
    print(f"PhoBERT alignment conflicts: {len(phobert_conflicts)}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--none-ratio", type=float, default=0.25)
    parser.add_argument("--output-name", default="v4_boundary")
    args = parser.parse_args()

    random.seed(RANDOM_SEED)

    root = Path(__file__).parent.parent.parent
    input_dir = root / "data" / "export_for_colab"
    input_files = [
        input_dir / "gemini_annotated_full.json",
        input_dir / "gemini_annotated_pos_neg.json",
    ]

    records = load_annotation_records(input_files)
    grouped = group_sentence_aspects(records)
    final_records, missed_records = build_records(grouped, args.none_ratio)
    export_datasets(final_records, root / "data" / "ner" / args.output_name, missed_records)

    print("[OK] Boundary-focused NER dataset is ready.")


if __name__ == "__main__":
    main()
