from transformers import AutoTokenizer, AutoModelForCausalLM
import os
import json
import pandas as pd
import torch

from utils import get_similarity_score

def get_model_tokenizer(model_name, cache_dir):
    os.makedirs(cache_dir, exist_ok=True)

    tokenizer = AutoTokenizer.from_pretrained(model_name, cache_dir=cache_dir)
    tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        model_name, 
        cache_dir=cache_dir,
        device_map="auto"
    )
    return tokenizer, model

if __name__ == "__main__":
    model_name = "meta-llama/CodeLlama-7b-Instruct-hf"
    cache_dir = "/scratch/projects/mehedi/models"
    dataset_path = "dataset/annotated_dataset.json"
    prompt_template_path = "prompt/prompt_templates.csv"
    result_dir = "prompt/results"

    tokenizer, model = get_model_tokenizer(model_name, cache_dir)

    print(model.hf_device_map)  
    print(next(model.parameters()).dtype)  

    print(f"Quantized model and tokenizer loaded from {cache_dir}")

    with open(dataset_path, 'r') as file:
        annotation_data = json.load(file)

    prompt_templates = pd.read_csv(prompt_template_path)

    prompt_versions = ["1.1.0.0", "1.1.0.1", "1.1.0.2", "1.3.0.0", "1.3.0.1", "1.3.0.2"]

    batch_size = 16  

    for prompt_version in prompt_versions:
        prompt_template = prompt_templates[prompt_templates['Version'] == prompt_version]

        if prompt_template.empty:
            print(f"No templates found for version {prompt_version}")
            continue

        prompt_strategy = prompt_template['Prompting-Strategy'].iloc[0]
        prompt_experiment = prompt_template['Exp-Name'].iloc[0]
        prompt_template_text = prompt_template['Template'].iloc[0]

        result = []
        all_prompts = []

        for annotation in annotation_data:
            prompt_copy = prompt_template_text
            if "{diff}" in prompt_copy:
                prompt_copy = prompt_copy.replace("{diff}", annotation['diff'])
            if "{commit_message}" in prompt_copy:
                prompt_copy = prompt_copy.replace("{commit_message}", annotation['commit_message'])
            if "{related_text}" in prompt_copy:
                related_text = "\n".join(
                    annotation.get('IR_RATIONALE_PRES', []) +
                    annotation.get('PR_RATIONALE_PRES', []) +
                    annotation.get('CC_RATIONALE_PRES', []) +
                    annotation.get('COM_T_RATIONALE_PRES', []) +
                    annotation.get('COM_B_RATIONALE_PRES', [])
                )
                prompt_copy = prompt_copy.replace("{related_text}", related_text)

            all_prompts.append((prompt_copy, annotation['RATIONALE'][0]))

        for i in range(0, len(all_prompts), batch_size):
            batch = all_prompts[i:i + batch_size]
            batch_prompts = [item[0] for item in batch]
            batch_rationales = [item[1] for item in batch]

            # Tokenize and generate for the batch
            inputs = tokenizer(batch_prompts, return_tensors="pt", max_length=512, truncation=True, padding=True)
            
            # Explicitly set attention_mask and pad_token_id
            inputs = { 
                'input_ids': inputs['input_ids'].to("cuda:0"), 
                'attention_mask': inputs['attention_mask'].to("cuda:0"),
                'pad_token_id': tokenizer.pad_token_id
            }

            outputs = model.generate(inputs["input_ids"], num_beams=5, early_stopping=True, max_new_tokens=1024)

            for j, output in enumerate(outputs):
                rationale_gen = tokenizer.decode(output, skip_special_tokens=True)
                similarity_score = get_similarity_score(batch_rationales[j], rationale_gen)

                result.append([
                    prompt_strategy,
                    prompt_experiment, 
                    prompt_version,
                    prompt_template_text,
                    batch_prompts[j],
                    rationale_gen,
                    batch_rationales[j],
                    similarity_score
                ])

        result_version_dir = os.path.join(result_dir, prompt_version)
        os.makedirs(result_version_dir, exist_ok=True)
        result_df = pd.DataFrame(result, columns=["Prompting-Strategy", "Exp-Name", "Version", "Template", "Input", "Code-Llama-7B-Output", "Rationale", "Score"])
        result_file_path = os.path.join(result_version_dir, "results.csv")
        result_df.to_csv(result_file_path, index=False)

        print(f"Results saved to {result_file_path}")
