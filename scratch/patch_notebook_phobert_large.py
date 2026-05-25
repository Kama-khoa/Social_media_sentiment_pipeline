import json
p = r'f:\Studies\Đồ án tốt nghiệp\Social_media_sentiment_pipeline\nlp\training\Colab_Finetuning_Template.ipynb'

with open(p, 'r', encoding='utf-8') as f:
    d = json.load(f)

for cell in d['cells']:
    if cell['cell_type'] == 'code':
        source = cell['source']
        new_source = []
        for line in source:
            # PhoBERT
            if 'model_checkpoint_phobert = "vinai/phobert-base"' in line:
                new_source.append(line.replace("phobert-base", "phobert-large"))
            elif 'learning_rate=2e-5,' in line and 'args_phobert' in "".join(source):
                new_source.append('    learning_rate=1e-5,\n')
                new_source.append('    weight_decay=0.01,\n')
                new_source.append('    lr_scheduler_type="cosine",\n')
                new_source.append('    warmup_ratio=0.1,\n')
            
            # vELECTRA WeightedTokenTrainer fix
            elif 'weights = torch.tensor([0.01]' in line:
                new_source.append("        weights = torch.tensor([1.0] + [2.0] * (model.config.num_labels - 1)).to(model.device)\n")
            elif 'weights = torch.tensor([0.1]' in line:
                new_source.append("        weights = torch.tensor([1.0] + [2.0] * (model.config.num_labels - 1)).to(model.device)\n")
            elif 'weights = torch.tensor([1.0]' in line:
                # In case it's already fixed
                new_source.append("        weights = torch.tensor([1.0] + [2.0] * (model.config.num_labels - 1)).to(model.device)\n")
            else:
                new_source.append(line)
        cell['source'] = new_source

with open(p, 'w', encoding='utf-8') as f:
    json.dump(d, f, indent=1, ensure_ascii=False)

print("Đã vá notebook thành công!")
