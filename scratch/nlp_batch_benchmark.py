import time
import argparse
import sys
from pathlib import Path
import torch
import torch.nn.functional as F
from transformers import AutoModelForTokenClassification, AutoModelForSequenceClassification, AutoTokenizer, PreTrainedTokenizerFast
from underthesea import word_tokenize
from pyvi import ViTokenizer

class BatchVELECTRAExtractor:
    def __init__(self, model_dir):
        model_dir = Path(model_dir)
        self._tokenizer = self._load_tokenizer(model_dir)
        self._model = AutoModelForTokenClassification.from_pretrained(str(model_dir))
        self._model.eval()
        self._id2label = self._model.config.id2label
        self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self._model.to(self._device)
        print(f"Loaded VELECTRA Extractor on device: {self._device}")

    def _load_tokenizer(self, model_dir):
        try:
            return AutoTokenizer.from_pretrained(str(model_dir))
        except ValueError as exc:
            if "TokenizersBackend" not in str(exc):
                raise
            return PreTrainedTokenizerFast(
                tokenizer_file=str(model_dir / "tokenizer.json"),
                unk_token="[UNK]",
                sep_token="[SEP]",
                pad_token="[PAD]",
                cls_token="[CLS]",
                mask_token="[MASK]",
                model_max_length=256,
            )

    def extract(self, sentence: str) -> list[dict]:
        sentence = sentence.strip()
        if not sentence:
            return [{"aspect_label": "NONE", "segment_text": "", "confidence": 1.0}]

        raw_tokens = word_tokenize(sentence)
        tokens = []
        for t in raw_tokens:
            tokens.extend(str(t).split())

        if not tokens:
            return [{"aspect_label": "NONE", "segment_text": "", "confidence": 1.0}]

        encoding = self._tokenizer(
            tokens,
            is_split_into_words=True,
            return_tensors="pt",
            truncation=True,
            max_length=256,
        )
        word_ids = encoding.word_ids(batch_index=0)
        inputs = {k: v.to(self._device) for k, v in encoding.items()}

        with torch.no_grad():
            logits = self._model(**inputs).logits[0]

        probs = F.softmax(logits, dim=-1)
        pred_ids = logits.argmax(dim=-1)

        word_labels = {}
        for pos, wid in enumerate(word_ids):
            if wid is None or wid in word_labels:
                continue
            label = self._id2label[pred_ids[pos].item()]
            conf = probs[pos, pred_ids[pos]].item()
            word_labels[wid] = (label, conf)

        for i in range(len(tokens)):
            if i not in word_labels:
                word_labels[i] = ("O", 0.5)

        tag_seq = [word_labels[i][0] for i in range(len(tokens))]
        conf_seq = [word_labels[i][1] for i in range(len(tokens))]

        return self._decode_spans(tokens, tag_seq, conf_seq)

    def _decode_spans(self, tokens, tags, confs):
        spans = []
        span_tokens = []
        span_confs = []
        current_label = None

        for token, tag, conf in zip(tokens, tags, confs):
            if tag.startswith("B-"):
                if current_label is not None:
                    spans.append({
                        "aspect_label": current_label,
                        "segment_text": " ".join(span_tokens),
                        "confidence": min(span_confs),
                    })
                current_label = tag[2:]
                span_tokens = [token]
                span_confs = [conf]
            elif tag.startswith("I-") and current_label == tag[2:]:
                span_tokens.append(token)
                span_confs.append(conf)
            else:
                if current_label is not None:
                    spans.append({
                        "aspect_label": current_label,
                        "segment_text": " ".join(span_tokens),
                        "confidence": min(span_confs),
                    })
                current_label = None
                span_tokens = []
                span_confs = []

        if current_label is not None:
            spans.append({
                "aspect_label": current_label,
                "segment_text": " ".join(span_tokens),
                "confidence": min(span_confs),
            })

        if not spans:
            o_confs = [c for t, c in zip(tags, confs) if t == "O"]
            avg_o_conf = sum(o_confs) / max(len(o_confs), 1)
            return [{"aspect_label": "NONE", "segment_text": "", "confidence": avg_o_conf}]

        return spans

    def extract_batch(self, sentences: list[str]) -> list[list[dict]]:
        results = [None] * len(sentences)
        batch_tokens = []
        valid_indices = []

        for i, sent in enumerate(sentences):
            sent = sent.strip()
            if not sent:
                results[i] = [{"aspect_label": "NONE", "segment_text": "", "confidence": 1.0}]
                continue

            raw_tokens = word_tokenize(sent)
            tokens = []
            for t in raw_tokens:
                tokens.extend(str(t).split())

            if not tokens:
                results[i] = [{"aspect_label": "NONE", "segment_text": "", "confidence": 1.0}]
            else:
                batch_tokens.append(tokens)
                valid_indices.append(i)

        if not batch_tokens:
            return results

        encoding = self._tokenizer(
            batch_tokens,
            is_split_into_words=True,
            padding=True,
            truncation=True,
            return_tensors="pt",
            max_length=256,
        )
        inputs = {k: v.to(self._device) for k, v in encoding.items()}

        with torch.no_grad():
            logits = self._model(**inputs).logits

        probs = F.softmax(logits, dim=-1)
        pred_ids = logits.argmax(dim=-1)

        for idx, valid_idx in enumerate(valid_indices):
            word_ids = encoding.word_ids(batch_index=idx)
            seq_logits = logits[idx]
            seq_probs = probs[idx]
            seq_pred_ids = pred_ids[idx]
            tokens = batch_tokens[idx]

            word_labels = {}
            for pos, wid in enumerate(word_ids):
                if wid is None or wid in word_labels:
                    continue
                label = self._id2label[seq_pred_ids[pos].item()]
                conf = seq_probs[pos, seq_pred_ids[pos]].item()
                word_labels[wid] = (label, conf)

            for i in range(len(tokens)):
                if i not in word_labels:
                    word_labels[i] = ("O", 0.5)

            tag_seq = [word_labels[i][0] for i in range(len(tokens))]
            conf_seq = [word_labels[i][1] for i in range(len(tokens))]

            results[valid_idx] = self._decode_spans(tokens, tag_seq, conf_seq)

        return results


class BatchPhoBERTClassifier:
    def __init__(self, model_dir):
        model_dir = Path(model_dir)
        self._tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
        self._model = AutoModelForSequenceClassification.from_pretrained(str(model_dir))
        self._model.eval()
        self._id2label = self._model.config.id2label
        self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self._model.to(self._device)
        print(f"Loaded PhoBERT Classifier on device: {self._device}")

    def classify(self, comment_text: str, aspect_label: str) -> tuple[str, float]:
        aspect_segmented = ViTokenizer.tokenize(aspect_label) if aspect_label.strip() else ""
        sent_segmented = ViTokenizer.tokenize(comment_text)

        inputs = self._tokenizer(
            aspect_segmented,
            sent_segmented,
            return_tensors="pt",
            truncation=True,
            max_length=256,
        )
        inputs = {k: v.to(self._device) for k, v in inputs.items()}

        with torch.no_grad():
            logits = self._model(**inputs).logits[0]

        probs = F.softmax(logits, dim=-1)
        pred_id = logits.argmax().item()

        return self._id2label[pred_id], probs[pred_id].item()

    def classify_batch(self, pairs: list[tuple[str, str]]) -> list[tuple[str, float]]:
        if not pairs:
            return []

        aspect_segmented_list = []
        sent_segmented_list = []

        for comment_text, aspect_label in pairs:
            aspect_seg = ViTokenizer.tokenize(aspect_label) if aspect_label.strip() else ""
            sent_seg = ViTokenizer.tokenize(comment_text)
            aspect_segmented_list.append(aspect_seg)
            sent_segmented_list.append(sent_seg)

        inputs = self._tokenizer(
            aspect_segmented_list,
            sent_segmented_list,
            padding=True,
            truncation=True,
            return_tensors="pt",
            max_length=256,
        )
        inputs = {k: v.to(self._device) for k, v in inputs.items()}

        with torch.no_grad():
            logits = self._model(**inputs).logits

        probs = F.softmax(logits, dim=-1)
        pred_ids = logits.argmax(dim=-1)

        results = []
        for idx in range(len(pairs)):
            pred_id = pred_ids[idx].item()
            conf = probs[idx, pred_id].item()
            results.append((self._id2label[pred_id], conf))

        return results


def run_sequential(sentences, extractor, classifier, threshold=0.70):
    results = []
    for sent in sentences:
        aspects = extractor.extract(sent)
        sent_results = []
        for aspect in aspects:
            aspect_label = aspect["aspect_label"]
            ner_conf = aspect["confidence"]
            
            if aspect_label == "NONE":
                sent_results.append({
                    "sentence": sent,
                    "aspect_label": "NONE",
                    "segment_text": "",
                    "sentiment_label": "neutral",
                    "ner_confidence": ner_conf,
                    "sentiment_confidence": 1.0,
                    "confidence": ner_conf,
                })
                continue
                
            sentiment_label, sentiment_conf = classifier.classify(sent, aspect_label)
            sent_results.append({
                "sentence": sent,
                "aspect_label": aspect_label,
                "segment_text": aspect["segment_text"],
                "sentiment_label": sentiment_label,
                "ner_confidence": ner_conf,
                "sentiment_confidence": sentiment_conf,
                "confidence": min(ner_conf, sentiment_conf),
            })
        results.append(sent_results)
    return results


def run_batched(sentences, extractor, classifier, batch_size=32, threshold=0.70):
    all_results = [None] * len(sentences)
    
    # 1. Trích xuất khía cạnh (aspect extraction) theo lô
    batch_aspects = []
    for start in range(0, len(sentences), batch_size):
        chunk = sentences[start : start + batch_size]
        batch_aspects.extend(extractor.extract_batch(chunk))
        
    # 2. Thu thập các cặp cần phân tích cảm xúc (aspect_label != "NONE")
    # Cấu trúc: (sentence, aspect_label, sentence_idx, aspect_idx, aspect_dict)
    classification_tasks = []
    
    for sent_idx, aspects in enumerate(batch_aspects):
        sent_results = []
        for aspect_idx, aspect in enumerate(aspects):
            aspect_label = aspect["aspect_label"]
            ner_conf = aspect["confidence"]
            
            if aspect_label == "NONE":
                # Không cần phân tích sentiment qua PhoBERT, gán luôn neutral
                sent_results.append({
                    "sentence": sentences[sent_idx],
                    "aspect_label": "NONE",
                    "segment_text": "",
                    "sentiment_label": "neutral",
                    "ner_confidence": ner_conf,
                    "sentiment_confidence": 1.0,
                    "confidence": ner_conf,
                })
            else:
                # Cần phân tích sentiment
                classification_tasks.append((
                    sentences[sent_idx],
                    aspect_label,
                    sent_idx,
                    aspect_idx,
                    aspect
                ))
                # Placeholder để điền kết quả vào sau
                sent_results.append(None)
        all_results[sent_idx] = sent_results

    # 3. Phân tích cảm xúc (sentiment classification) theo lô
    if classification_tasks:
        # Gom các cặp (sentence, aspect_label)
        pairs = [(task[0], task[1]) for task in classification_tasks]
        
        batch_sentiments = []
        for start in range(0, len(pairs), batch_size):
            chunk = pairs[start : start + batch_size]
            batch_sentiments.extend(classifier.classify_batch(chunk))
            
        # Điền kết quả ngược lại cấu trúc đầu ra
        for task, (sentiment_label, sentiment_conf) in zip(classification_tasks, batch_sentiments):
            sent_text, aspect_label, sent_idx, aspect_idx, aspect_dict = task
            ner_conf = aspect_dict["confidence"]
            
            all_results[sent_idx][aspect_idx] = {
                "sentence": sent_text,
                "aspect_label": aspect_label,
                "segment_text": aspect_dict["segment_text"],
                "sentiment_label": sentiment_label,
                "ner_confidence": ner_conf,
                "sentiment_confidence": sentiment_conf,
                "confidence": min(ner_conf, sentiment_conf),
            }
            
    return all_results


def generate_mock_sentences(num_samples):
    templates = [
        "Điện thoại này pin trâu dã man, dùng cả ngày không hết.",
        "Màn hình của máy hơi tối khi ra ngoài trời nắng.",
        "Hiệu năng chơi game rất mượt nhưng máy nhanh nóng.",
        "Thiết kế của laptop cực kỳ sang trọng và mỏng nhẹ.",
        "Giá bán của chiếc tai nghe này hơi cao so với chất âm.",
        "Camera chụp ảnh đêm rất đẹp, lấy nét nhanh.",
        "Bàn phím gõ êm, hành trình phím sâu.",
        "Chất lượng hoàn thiện kém, vỏ nhựa ọp ẹp.",
        "Loa ngoài nghe hơi rè khi bật âm lượng lớn.",
        "Sạc nhanh 67W giúp đầy pin chỉ trong 40 phút."
    ]
    sentences = []
    for i in range(num_samples):
        sentences.append(templates[i % len(templates)])
    return sentences


def verify_correctness(seq_res, batch_res):
    print("\n--- KIEM TRA DO CHINH XAC ---")
    if len(seq_res) != len(batch_res):
        print("[LOI] So luong cau dau ra khong khop!")
        return False
        
    for i, (s_list, b_list) in enumerate(zip(seq_res, batch_res)):
        if len(s_list) != len(b_list):
            print(f"[LOI] tai cau thu {i}: So luong khia canh khong khop!")
            return False
        for s_item, b_item in zip(s_list, b_list):
            for key in ["aspect_label", "segment_text", "sentiment_label"]:
                if s_item[key] != b_item[key]:
                    print(f"[LOI] tai cau thu {i}: Khac biet truong '{key}': Sequential='{s_item[key]}', Batch='{b_item[key]}'")
                    return False
            # So sanh do tin cay sai so nho
            if abs(s_item["confidence"] - b_item["confidence"]) > 1e-4:
                print(f"[CANH BAO] tai cau thu {i}: Sai so confidence nhe: Sequential={s_item['confidence']:.4f}, Batch={b_item['confidence']:.4f}")
                
    print("[HOP LE] Ket qua dau ra cua 2 phuong phap trung khop 100%!")
    return True


def main():
    parser = argparse.ArgumentParser(description="Benchmark NLP Vectorized Batching vs Sequential")
    parser.add_argument("--num-samples", type=int, default=500, help="So luong cau test")
    parser.add_argument("--batch-size", type=int, default=64, help="Kich thuoc lo cho Batch Inference")
    args = parser.parse_args()

    project_root = Path(__file__).parent.parent
    velectra_dir = project_root / "models" / "velectra_aspect"
    phobert_dir = project_root / "models" / "phobert_sentiment"

    if not velectra_dir.exists() or not phobert_dir.exists():
        print(f"[LOI] Thu muc model khong ton tai!")
        print(f"Kiem tra duong dan:")
        print(f" - VELECTRA: {velectra_dir}")
        print(f" - PhoBERT: {phobert_dir}")
        sys.exit(1)

    print("=== KHOI TAO MO HINH ===")
    extractor = BatchVELECTRAExtractor(velectra_dir)
    classifier = BatchPhoBERTClassifier(phobert_dir)

    print(f"\nSinh tap du lieu mau: {args.num_samples} cau...")
    sentences = generate_mock_sentences(args.num_samples)

    # 1. Warm-up (Chay thu de PyTorch nap model len GPU hoan chinh)
    print("Dang khoi dong (warm-up) GPU/Mo hinh...")
    _ = run_batched(sentences[:10], extractor, classifier, batch_size=args.batch_size)

    # 2. Chay Sequential
    print(f"\n1. Dang chay Sequential Inference ({args.num_samples} cau)...")
    t0 = time.perf_counter()
    seq_results = run_sequential(sentences, extractor, classifier)
    t_seq = time.perf_counter() - t0
    seq_speed = args.num_samples / t_seq
    print(f"-> Hoan thanh Sequential: {t_seq:.3f} giay ({seq_speed:.2f} cau/giay)")

    # 3. Chay Batched
    print(f"\n2. Dang chay Vectorized Batch Inference (Batch Size = {args.batch_size}, {args.num_samples} cau)...")
    t0 = time.perf_counter()
    batch_results = run_batched(sentences, extractor, classifier, batch_size=args.batch_size)
    t_batch = time.perf_counter() - t0
    batch_speed = args.num_samples / t_batch
    print(f"-> Hoan thanh Batch: {t_batch:.3f} giay ({batch_speed:.2f} cau/giay)")

    # 4. Kiem tra tinh chinh xac
    verify_correctness(seq_results, batch_results)

    # 5. Bao cao ket qua
    speedup = t_seq / t_batch
    print("\n==================================================")
    print("             KET QUA SO SANH HIEU NANG            ")
    print("==================================================")
    print(f"Tong so cau xu ly   : {args.num_samples}")
    print(f"Kich thuoc Lo (Batch): {args.batch_size}")
    print(f"Toc do Sequential   : {seq_speed:.2f} cau/giay (Tong: {t_seq:.3f}s)")
    print(f"Toc do Batch        : {batch_speed:.2f} cau/giay (Tong: {t_batch:.3f}s)")
    print("--------------------------------------------------")
    print(f"TY LE TANG TOC (Speedup Factor): {speedup:.2f}x")
    print("==================================================")


if __name__ == "__main__":
    main()
