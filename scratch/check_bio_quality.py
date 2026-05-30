import json

def check_bio_tags():
    path = r'f:\Studies\Đồ án tốt nghiệp\Social_media_sentiment_pipeline\data\export_for_colab\gemini_annotated_pos_neg.json'
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    valid = 0
    all_o = 0
    
    for item in data:
        aspect = item.get('aspect_label', 'NONE')
        if aspect == 'NONE':
            continue
            
        tags = item.get('bio_tags', item.get('ner_tags', []))
        valid += 1
        
        if all(t == 'O' for t in tags):
            all_o += 1
            
    print(f"Total non-NONE sentences: {valid}")
    print(f"Total with ONLY 'O' tags: {all_o}")
    print(f"Percentage of failed alignment: {all_o / valid * 100:.2f}%")

check_bio_tags()
