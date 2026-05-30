import json
import random
import sys
from pathlib import Path
from underthesea import word_tokenize
from sklearn.model_selection import train_test_split
from pyvi import ViTokenizer

# Set encoding to utf-8 for Windows command line
sys.stdout.reconfigure(encoding='utf-8')

# CONFIGURATION PARAMETERS
TARGET_NONE_RATIO = 0.25  # Mặc định cho phiên bản v3_none25
MAX_SPAN_LEN = 12
RANDOM_SEED = 42

random.seed(RANDOM_SEED)

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

def map_syllable_to_word_tags(syllable_tokens, syllable_tags, word_tokens):
    word_tags = []
    syll_idx = 0
    
    for word in word_tokens:
        word_clean = word.replace("_", "").lower()
        
        current_syllables = []
        current_tags = []
        
        while syll_idx < len(syllable_tokens):
            syll = syllable_tokens[syll_idx]
            tag = syllable_tags[syll_idx]
            current_syllables.append(syll.lower())
            current_tags.append(tag)
            syll_idx += 1
            
            concatenated = "".join(current_syllables)
            if concatenated == word_clean:
                break
        
        # Filter out O
        non_o_tags = [t for t in current_tags if t != "O"]
        if not non_o_tags:
            word_tags.append("O")
            continue
            
        # Get entity types
        ent_types = set(t[2:] for t in non_o_tags)
        if len(ent_types) > 1:
            return None  # Conflict: multiple types in one word
            
        ent_type = list(ent_types)[0]
        has_b = any(t.startswith("B-") for t in non_o_tags)
        
        if has_b:
            word_tags.append(f"B-{ent_type}")
        else:
            word_tags.append(f"I-{ent_type}")
            
    if syll_idx != len(syllable_tokens):
        return None  # Alignment mismatch
        
    # Ensure BIO sequence compliance
    for i in range(len(word_tags)):
        t = word_tags[i]
        if t.startswith("I-"):
            ent_type = t[2:]
            if i == 0 or word_tags[i-1] == "O" or word_tags[i-1][2:] != ent_type:
                word_tags[i] = f"B-{ent_type}"
                
    return word_tags

def process_data(all_records, target_none_ratio):
    sentence_dict = {}
    for item in all_records:
        sentence = item.get("sentence", "").strip()
        if not sentence:
            continue
            
        aspect = item.get("aspect_label", "NONE")
        sentiment = item.get("sentiment_label", "neutral")
        
        orig_tokens = item.get("tokens", [])
        orig_tags = item.get("ner_tags", item.get("bio_tags", []))
        
        if not orig_tokens:
            orig_tokens = word_tokenize(sentence)
        
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

    # Validate BIO and Long Spans
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
                if current_span > MAX_SPAN_LEN:
                    data["has_long_span"] = True
                current_span = 1
                current_label = t[2:]
            elif t.startswith("I-") and t[2:] == current_label:
                current_span += 1
            else:
                if current_span > MAX_SPAN_LEN:
                    data["has_long_span"] = True
                current_span = 0
                current_label = None
        if current_span > MAX_SPAN_LEN:
            data["has_long_span"] = True

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

    # Apply NONE ratio
    target_none_count = int(len(clean_aspect_list) * target_none_ratio / (1 - target_none_ratio))
    if target_none_count > len(clean_none_list):
        selected_none = clean_none_list
    else:
        selected_none = random.sample(clean_none_list, target_none_count)
        
    final_sentences = clean_aspect_list + selected_none
    random.shuffle(final_sentences)
    
    return final_sentences, clean_aspect_list, selected_none, conflict_list, long_span_list, sentiment_conflict_list, aspect_without_ner_list

def export_datasets(sents, out_ner_dir, out_phobert_ner_dir=None, out_sent_dir=None):
    out_ner_dir.mkdir(parents=True, exist_ok=True)
    ner_train = out_ner_dir / "train.jsonl"
    ner_val = out_ner_dir / "val.jsonl"
    
    train_sents, val_sents = train_test_split(sents, test_size=0.2, random_state=RANDOM_SEED)
    
    def write_ner(file_path, sents_list):
        with open(file_path, "w", encoding="utf-8") as f:
            for sentence, data in sents_list:
                assert len(data["tokens"]) == len(data["merged_tags"]), f"Length mismatch: {sentence}"
                aspects = list(set([a for a, _ in data["aspects_sentiments"]]))
                ner_rec = {
                    "sentence": sentence,
                    "tokens": data["tokens"],
                    "ner_tags": data["merged_tags"],
                    "aspects": aspects
                }
                f.write(json.dumps(ner_rec, ensure_ascii=False) + "\n")
                
    write_ner(ner_train, train_sents)
    write_ner(ner_val, val_sents)
    
    # PhoBERT NER export (Word-segmented)
    if out_phobert_ner_dir:
        out_phobert_ner_dir.mkdir(parents=True, exist_ok=True)
        pb_train = out_phobert_ner_dir / "train.jsonl"
        pb_val = out_phobert_ner_dir / "val.jsonl"
        
        def write_pb_ner(file_path, sents_list):
            wrong_pb_ner = []
            write_count = 0
            with open(file_path, "w", encoding="utf-8") as f:
                for sentence, data in sents_list:
                    word_segmented_text = ViTokenizer.tokenize(sentence)
                    words = word_segmented_text.split()
                    
                    word_tags = map_syllable_to_word_tags(data["tokens"], data["merged_tags"], words)
                    
                    if word_tags is None:
                        wrong_pb_ner.append({
                            "sentence": sentence,
                            "syllable_tokens": data["tokens"],
                            "syllable_tags": data["merged_tags"],
                            "word_tokens": words
                        })
                        continue
                        
                    assert len(words) == len(word_tags), f"Word tag length mismatch: {sentence}"
                    aspects = list(set([a for a, _ in data["aspects_sentiments"]]))
                    ner_rec = {
                        "sentence": sentence,
                        "tokens": words,
                        "ner_tags": word_tags,
                        "aspects": aspects
                    }
                    f.write(json.dumps(ner_rec, ensure_ascii=False) + "\n")
                    write_count += 1
            return write_count, wrong_pb_ner
            
        tr_count, tr_wrongs = write_pb_ner(pb_train, train_sents)
        val_count, val_wrongs = write_pb_ner(pb_val, val_sents)
        
        all_wrongs = tr_wrongs + val_wrongs
        if all_wrongs:
            review_file = out_phobert_ner_dir / "review_phobert_ner_conflicts.jsonl"
            with open(review_file, "w", encoding="utf-8") as f:
                for w in all_wrongs:
                    f.write(json.dumps(w, ensure_ascii=False) + "\n")
            print(f"  PhoBERT NER: Skip {len(all_wrongs)} conflict sentences, saved to review_phobert_ner_conflicts.jsonl")
            
    # Sentiment export
    if out_sent_dir:
        out_sent_dir.mkdir(parents=True, exist_ok=True)
        sent_train = out_sent_dir / "train.jsonl"
        sent_val = out_sent_dir / "val.jsonl"
        
        def write_sent(file_path, sents_list):
            with open(file_path, "w", encoding="utf-8") as f:
                for sentence, data in sents_list:
                    for aspect, sentiment in data["aspects_sentiments"]:
                        sent_rec = {
                            "text": sentence,
                            "aspect": aspect,
                            "label": sentiment
                        }
                        f.write(json.dumps(sent_rec, ensure_ascii=False) + "\n")
                        
        write_sent(sent_train, train_sents)
        write_sent(sent_val, val_sents)

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

    # 2. XỬ LÝ CHO CÁC TỶ LỆ NONE KHÁC NHAU
    ratios = [0.25, 0.30]
    
    for ratio in ratios:
        print(f"\n--- Processing dataset with TARGET_NONE_RATIO = {ratio} ---")
        final_sentences, clean_aspect_list, selected_none, conflict_list, long_span_list, sentiment_conflict_list, aspect_without_ner_list = process_data(all_records, ratio)
        
        # In thông tin thống kê
        print(f"- Có khía cạnh (Sạch): {len(clean_aspect_list)}")
        print(f"- NONE (Không khía cạnh): {len(selected_none)}")
        print(f"- Xung đột (Conflict): {len(conflict_list)}")
        print(f"- Xung đột sentiment: {len(sentiment_conflict_list)}")
        print(f"- Có khía cạnh nhưng ko có NER: {len(aspect_without_ner_list)}")
        print(f"- Span quá dài (>{MAX_SPAN_LEN}): {len(long_span_list)}")
        print(f"- Tổng dataset chốt: {len(final_sentences)} câu (Tỷ lệ NONE: {len(selected_none)/len(final_sentences)*100:.1f}%)")
        
        # Chỉ ghi nhận review files cho ratio mặc định (0.25)
        if ratio == 0.25:
            with open(master_dir / "review_conflicts.jsonl", "w", encoding="utf-8") as f:
                for c in conflict_list: f.write(json.dumps(c, ensure_ascii=False) + "\n")
            with open(master_dir / "review_long_spans.jsonl", "w", encoding="utf-8") as f:
                for c in long_span_list: f.write(json.dumps(c, ensure_ascii=False) + "\n")
            with open(master_dir / "review_sentiment_conflicts.jsonl", "w", encoding="utf-8") as f:
                for c in sentiment_conflict_list: f.write(json.dumps(c, ensure_ascii=False) + "\n")
            with open(master_dir / "review_aspect_without_ner.jsonl", "w", encoding="utf-8") as f:
                for c in aspect_without_ner_list: f.write(json.dumps(c, ensure_ascii=False) + "\n")

        # Cấu hình đường dẫn xuất
        ratio_str = f"none{int(ratio*100)}"
        out_ner_dir = root / "data" / "ner" / f"v3_{ratio_str}" / "velectra"
        
        out_phobert_ner_dir = None
        out_sent_dir = None
        if ratio == 0.25:
            out_phobert_ner_dir = root / "data" / "ner" / f"v3_{ratio_str}" / "phobert"
            out_sent_dir = root / "data" / "sentiment" / "phobert"
            
        export_datasets(final_sentences, out_ner_dir, out_phobert_ner_dir, out_sent_dir)
        print(f"Exported v3 {ratio_str} datasets successfully!")

    print("\n[VALIDATION OK] Đã hoàn tất export tập dataset v3!")

if __name__ == "__main__":
    main()
