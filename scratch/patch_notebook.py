import json
p = r'f:\Studies\Đồ án tốt nghiệp\Social_media_sentiment_pipeline\nlp\training\Colab_Finetuning_Template.ipynb'

with open(p, 'r', encoding='utf-8') as f:
    d = json.load(f)

for cell in d['cells']:
    if cell['cell_type'] == 'code':
        source = cell['source']
        if any("trainer_velectra = Trainer(" in line for line in source):
            new_source = []
            for line in source:
                if line == "trainer_velectra = Trainer(\n":
                    new_source.extend([
                        "import torch\n",
                        "from torch import nn\n",
                        "class WeightedTokenTrainer(Trainer):\n",
                        "    def compute_loss(self, model, inputs, return_outputs=False, **kwargs):\n",
                        "        labels = inputs.pop('labels')\n",
                        "        outputs = model(**inputs)\n",
                        "        logits = outputs.logits\n",
                        "        # Nhãn 0 (O) có loss cực thấp (0.01), các nhãn thực thể (1-12) có loss cao (2.0)\n",
                        "        weights = torch.tensor([0.01] + [2.0] * (model.config.num_labels - 1)).to(model.device)\n",
                        "        loss_fct = nn.CrossEntropyLoss(weight=weights)\n",
                        "        active_loss = inputs['attention_mask'].view(-1) == 1\n",
                        "        active_logits = logits.view(-1, model.config.num_labels)\n",
                        "        active_labels = torch.where(\n",
                        "            active_loss, labels.view(-1), torch.tensor(loss_fct.ignore_index).type_as(labels)\n",
                        "        )\n",
                        "        loss = loss_fct(active_logits, active_labels)\n",
                        "        return (loss, outputs) if return_outputs else loss\n",
                        "\n",
                        "trainer_velectra = WeightedTokenTrainer(\n"
                    ])
                else:
                    new_source.append(line)
            cell['source'] = new_source

with open(p, 'w', encoding='utf-8') as f:
    json.dump(d, f, indent=1, ensure_ascii=False)
