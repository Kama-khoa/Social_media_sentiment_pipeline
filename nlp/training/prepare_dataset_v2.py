import json
import random
from pathlib import Path
from underthesea import word_tokenize
from sklearn.model_selection import train_test_split

random.seed(42)

def main():
    root = Path(__file__).parent.parent.parent
    data_dir = root / "data" / "export_for_colab"
    
    input_files = [
        data_dir / "gemini_annotated_full.json",
        data_dir / "gemini_annotated_pos_neg.json"
    ]

    master_dir = root / "data" / "master"
    master_dir.mkdir(parents=True, exist_ok=True)
    master_file = master_dir / "labeled_master.jsonl"
    
    out_phobert_dir = root / "data" / "sentiment" / "phobert"
    out_phobert_dir.mkdir(parents=True, exist_ok=True)
    out_velectra_dir = root / "data" / "ner" / "velectra"
    out_velectra_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. TẠO MASTER DATASET VÀ LOAD DỮ LIỆU
    all_records = []
    for path in input_files:
        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                records = json.load(f)
                all_records.extend(records)
                print(f"Loaded {len(records)} records from {path.name}")
                
    with open(master_file, 'w', encoding='utf-8') as f:
        for rec in all_records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            
    print(f"Created labeled_master.jsonl with {len(all_records)} records.")

    # 2. GROUP THEO SENTENCE
    sentence_dict = {}
    for item in all_records:
        sentence = item.get("sentence", "").strip()
        if not sentence:
            continue
            
        aspect = item.get("aspect_label", "NONE")
        sentiment = item.get("sentiment_label", "neutral")
        
        # Lấy tokens và tags
        orig_tokens = item.get("tokens", [])
        orig_tags = item.get("ner_tags", item.get("bio_tags", []))
        
        # Nếu không có tokens, dùng underthesea (split syllables)
        if not orig_tokens:
            orig_tokens = word_tokenize(sentence)
        
        # Word split mapping (chuẩn hóa về syllables giống prepare_colab_data cũ)
        new_tokens = []
        new_tags = []
        if len(orig_tokens) == len(orig_tags):
            for t, tag in zip(orig_tokens, orig_tags):
                parts = str(t).split()
                if not parts: continue
                new_tokens.extend(parts)
                if tag.startswith("B-"):
                    new_tags.append(tag)
                    i_tag = "I-" + tag[2:]
                    new_tags.extend([i_tag] * (len(parts) - 1))
                else:
                    new_tags.extend([tag] * len(parts))
        else:
            # Fallback nếu tag và token không khớp -> set toàn bộ là O
            new_tokens = []
            for t in orig_tokens: new_tokens.extend(str(t).split())
            new_tags = ["O"] * len(new_tokens)
            
        if sentence not in sentence_dict:
            sentence_dict[sentence] = {
                "tokens": new_tokens,
                "aspects_sentiments": {},
                "merged_tags": ["O"] * len(new_tokens),
                "is_conflict": False,
                "has_long_span": False,
                "is_sentiment_conflict": False,
                "is_aspect_without_ner": False
            }
            
        if aspect != "NONE":
            if aspect in sentence_dict[sentence]["aspects_sentiments"]:
                if sentence_dict[sentence]["aspects_sentiments"][aspect] != sentiment:
                    sentence_dict[sentence]["is_sentiment_conflict"] = True
            else:
                sentence_dict[sentence]["aspects_sentiments"][aspect] = sentiment
            
            # Merge tags
            base_tags = sentence_dict[sentence]["merged_tags"]
            if len(new_tags) == len(base_tags):
                for i in range(len(base_tags)):
                    if new_tags[i] != "O":
                        if base_tags[i] == "O":
                            base_tags[i] = new_tags[i]
                        elif base_tags[i] != new_tags[i]:
                            sentence_dict[sentence]["is_conflict"] = True
            else:
                sentence_dict[sentence]["is_conflict"] = True

    def validate_bio(tags):
        current_label = None
        for t in tags:
            if t.startswith("B-"):
                current_label = t[2:]
            elif t.startswith("I-"):
                if current_label != t[2:]:
                    return False
            else:
                current_label = None
        return True

    # Check long spans (>12 tokens) and BIO validation
    for sentence, data in sentence_dict.items():
        if data["is_conflict"] or data.get("is_sentiment_conflict"): continue
        
        tags = data["merged_tags"]
        
        if len(data["aspects_sentiments"]) > 0 and all(t == "O" for t in tags):
            data["is_aspect_without_ner"] = True
            
        if not validate_bio(tags):
            data["is_conflict"] = True
            continue

        current_span = 0
        current_label = None
        for t in tags:
            if t.startswith("B-"):
                if current_span > 12:
                    data["has_long_span"] = True
                current_span = 1
                current_label = t[2:]
            elif t.startswith("I-") and t[2:] == current_label:
                current_span += 1
            else:
                if current_span > 12:
                    data["has_long_span"] = True
                current_span = 0
                current_label = None
        if current_span > 12:
            data["has_long_span"] = True

    # Tách các loại list
    conflict_list = []
    long_span_list = []
    clean_aspect_list = []
    clean_none_list = []
    sentiment_conflict_list = []
    aspect_without_ner_list = []

    for sentence, data in sentence_dict.items():
        data["aspects_sentiments"] = list(data["aspects_sentiments"].items())
        
        if data.get("is_sentiment_conflict"):
            sentiment_conflict_list.append({"sentence": sentence, "tokens": data["tokens"]})
        elif data.get("is_aspect_without_ner"):
            aspect_without_ner_list.append({"sentence": sentence, "tokens": data["tokens"], "merged_tags": data["merged_tags"]})
        elif data["is_conflict"]:
            conflict_list.append({"sentence": sentence, "tokens": data["tokens"], "merged_tags": data["merged_tags"]})
        elif data["has_long_span"]:
            long_span_list.append({"sentence": sentence, "tokens": data["tokens"], "merged_tags": data["merged_tags"]})
        elif len(data["aspects_sentiments"]) > 0:
            clean_aspect_list.append((sentence, data))
        else:
            clean_none_list.append((sentence, data))

    print(f"\nPhân tích sentence:")
    print(f"- Có khía cạnh (Sạch): {len(clean_aspect_list)}")
    print(f"- NONE (Không khía cạnh): {len(clean_none_list)}")
    print(f"- Xung đột (Conflict): {len(conflict_list)}")
    print(f"- Xung đột sentiment: {len(sentiment_conflict_list)}")
    print(f"- Có khía cạnh nhưng ko có NER: {len(aspect_without_ner_list)}")
    print(f"- Span quá dài (>12): {len(long_span_list)}")

    with open(root / "data" / "master" / "review_conflicts.jsonl", "w", encoding="utf-8") as f:
        for c in conflict_list: f.write(json.dumps(c, ensure_ascii=False) + "\n")
        
    with open(root / "data" / "master" / "review_long_spans.jsonl", "w", encoding="utf-8") as f:
        for c in long_span_list: f.write(json.dumps(c, ensure_ascii=False) + "\n")
        
    with open(root / "data" / "master" / "review_sentiment_conflicts.jsonl", "w", encoding="utf-8") as f:
        for c in sentiment_conflict_list: f.write(json.dumps(c, ensure_ascii=False) + "\n")
        
    with open(root / "data" / "master" / "review_aspect_without_ner.jsonl", "w", encoding="utf-8") as f:
        for c in aspect_without_ner_list: f.write(json.dumps(c, ensure_ascii=False) + "\n")

    # 3. LẤY TỶ LỆ NONE THẬT
    # Muốn NONE chiếm 25% tổng dataset -> NONE = 0.25 * (Aspect + NONE) => NONE = Aspect / 3
    target_none_count = int(len(clean_aspect_list) / 3)
    if target_none_count > len(clean_none_list):
        selected_none = clean_none_list
    else:
        selected_none = random.sample(clean_none_list, target_none_count)
        
    final_sentences = clean_aspect_list + selected_none
    random.shuffle(final_sentences)

    print(f"- Dataset chốt: {len(clean_aspect_list)} Aspect + {len(selected_none)} NONE = {len(final_sentences)} câu (Tỷ lệ NONE: {len(selected_none)/len(final_sentences)*100:.1f}%)")

    # 4. CHIA TẬP TRAIN / VAL THEO SENTENCE
    train_sents, val_sents = train_test_split(final_sentences, test_size=0.2, random_state=42)

    train_set_sentences = {s[0] for s in train_sents}
    val_set_sentences = {s[0] for s in val_sents}

    # KIỂM ĐỊNH LEAKAGE
    overlap = train_set_sentences.intersection(val_set_sentences)
    assert len(overlap) == 0, f"DATA LEAKAGE PHÁT HIỆN: {len(overlap)} câu trùng lặp giữa Train và Val!"

    # Xuất ra file
    def export_datasets(sents, mode):
        # NER export
        ner_file = out_velectra_dir / f"{mode}.jsonl"
        sentiment_file = out_phobert_dir / f"{mode}.jsonl"
        
        with open(ner_file, "w", encoding="utf-8") as f_ner, open(sentiment_file, "w", encoding="utf-8") as f_sent:
            for sentence, data in sents:
                # Validation length
                assert len(data["tokens"]) == len(data["merged_tags"]), f"Length mismatch ở câu: {sentence}"
                
                aspects = list(set([a for a, _ in data["aspects_sentiments"]]))
                ner_rec = {
                    "sentence": sentence,
                    "tokens": data["tokens"],
                    "ner_tags": data["merged_tags"],
                    "aspects": aspects
                }
                f_ner.write(json.dumps(ner_rec, ensure_ascii=False) + "\n")
                
                # Sentiment export (chỉ áp dụng cho những câu CÓ aspect)
                for aspect, sentiment in data["aspects_sentiments"]:
                    sent_rec = {
                        "text": sentence,
                        "aspect": aspect,
                        "label": sentiment
                    }
                    f_sent.write(json.dumps(sent_rec, ensure_ascii=False) + "\n")

    export_datasets(train_sents, "train")
    export_datasets(val_sents, "val")

    print("\n[VALIDATION OK] Đã export thành công!")
    print(f"- PhoBERT Sentiment: {out_phobert_dir}")
    print(f"- vELECTRA NER: {out_velectra_dir}")

if __name__ == "__main__":
    main()
