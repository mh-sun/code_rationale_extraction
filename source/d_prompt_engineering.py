import random
import re
from tqdm import tqdm
from transformers import AutoTokenizer, AutoModelForCausalLM, LlamaTokenizer, LlamaForCausalLM
import os
import json
import pandas as pd
import torch
from bert_score import score

from const import *

def get_example(datas, data_hash, hashes, N=1):
    eligible_hashes = hashes.copy()
    eligible_hashes.remove(data_hash)

    random_hashes = random.sample(eligible_hashes, N)

    return [d for d in datas if d['commit_hash'] in random_hashes]

def get_rationale(annotated_data, hash):
    for a in annotated_data:
        if a['commit'] == hash:
            return a['RATIONALE'][0].strip('RATIONALE:').strip('\n')
    return None

def prompt_construct(prompt_root_dir, prompt_template_path, prompt_result_dir, commit_data_path, annotated_path, hashes):
    with open(commit_data_path, 'r') as file:
        datas = json.load(file)

    with open(annotated_path, 'r') as file:
        annotated_data = json.load(file)

    datas = [d for d in datas if d['commit_hash'] in hashes]

    prompt_templates = pd.read_csv(prompt_template_path)

    for prompt_version in PROMPT_VERSIONS:
        prompt_template = prompt_templates[prompt_templates['Version'] == prompt_version]
        if prompt_template.empty:
            print(f"No templates found for version {prompt_version}")
            continue

        prompt_strategy = prompt_template['Prompting-Strategy'].iloc[0]
        prompt_experiment = prompt_template['Exp-Name'].iloc[0]
        prompt_template_text = prompt_template['Template'].iloc[0]

        result = []
        for data in datas:
            prompt_copy = prompt_template_text
            if "{diff}" in prompt_copy:
                prompt_copy = prompt_copy.replace("{diff}", data['diff'])
            if "{commit_message}" in prompt_copy:
                prompt_copy = prompt_copy.replace("{commit_message}", data['commit_subject']+'\n\n'+str(data['commit_body']))
            if "{related_text}" in prompt_copy:
                max_rel_text_count = min(len(data['related_texts']['summary']), 4)
                related_texts = [t['text'] for t in data['related_texts']['summary'][:max_rel_text_count]]
                related_texts = '\n'.join(related_texts)
                prompt_copy = prompt_copy.replace("{related_text}", related_texts)

            if prompt_version.startswith('1.2'):
                examples = get_example(datas, data['commit_hash'], hashes, FEW_SHOT_N)

                template = ""
                for example in examples:
                    example_diff = example['diff']

                    example_commit_message = example['commit_subject']+'\n\n'+str(example['commit_body'])

                    max_rel_text_count = min(len(example['related_texts']['summary']), 4)
                    example_related_text = [t['text'] for t in example['related_texts']['summary'][:max_rel_text_count]]
                    example_related_text = '\n'.join(example_related_text)

                    example_rationale = get_rationale(annotated_data, example['commit_hash'])
                    
                    template += f"Code Diff:\n{example_diff}\n\nCommit Message:\n{example_commit_message}\n\nRelated Texts(If Any):\n{example_related_text}\n\nRationale:{example_rationale}\n\n"
                
                if "{example}" in prompt_copy:
                    prompt_copy = prompt_copy.replace("{example}", template)

            result.append([
                prompt_strategy,
                prompt_experiment, 
                prompt_version,
                prompt_template_text,
                prompt_copy,
                get_rationale(annotated_data, data['commit_hash'])
            ])

        prompt_dir = os.path.join(os.path.join(prompt_root_dir, 'version'), prompt_version)
        os.makedirs(prompt_dir, exist_ok=True)

        result_df = pd.DataFrame(result, columns=["Prompting-Strategy", "Exp-Name", "Version", "Template", "Input", "Rationale"])
        result_file_path = os.path.join(prompt_dir, "prompt.csv")
        result_df.to_csv(result_file_path, index=False)

        print(f"Results saved to {result_file_path}")

def rationale_generate(prompt_dir, versions:list[str]):
    for version in versions:
        print(f"Inside Version: {version}")
        prompt_path = os.path.join(prompt_dir, version, 'prompt.csv')

        data = pd.read_csv(prompt_path)
        input_texts = data['Input'].tolist()

        model_id = "meta-llama/Meta-Llama-3-8B-Instruct"

        tokenizer = AutoTokenizer.from_pretrained(model_id, cache_dir=MODEL_DIR)
        model = AutoModelForCausalLM.from_pretrained(model_id, cache_dir=MODEL_DIR)

        tokenizer.pad_token = tokenizer.eos_token

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model = model.to(device)

        model_response = []
        rationales = []
        for input_text in tqdm(input_texts):
            messages = [
                {"role": "user", "content": input_text},
            ]

            input_ids = tokenizer.apply_chat_template(
                messages,
                add_generation_prompt=True,
                return_tensors="pt"
            ).to(model.device)

            terminators = [
                tokenizer.eos_token_id,
                tokenizer.convert_tokens_to_ids("<|eot_id|>")
            ]

            outputs = model.generate(
                input_ids,
                max_new_tokens=256,
                eos_token_id=terminators,
                do_sample=True,
                temperature=0.1,
            )
            response = outputs[0][input_ids.shape[-1]:]
            final = tokenizer.decode(response, skip_special_tokens=True)

            if version.startswith("1.3"):
                mode = int(version.split('.')[-1])
                rat = re.sub(r".*Step.*?\n", "", final)
                rat = rat.strip('\n')

            model_response.append(final)
            rationales.append(rat)

        data["generated_rationale"] = pd.Series(rationales)
        data["generated_response"] = pd.Series(model_response)
        
        data.to_csv(os.path.join(os.path.dirname(prompt_path), "response.csv"), index=False)

def calculate_bert_score(reference_texts, candidate_texts, model_type='bert-base-uncased'):
    if not isinstance(reference_texts, list) or not isinstance(candidate_texts, list):
        raise ValueError("Both reference_texts and candidate_texts must be lists of strings.")

    if len(reference_texts) != len(candidate_texts):
        raise ValueError("reference_texts and candidate_texts must have the same length.")

    # Calculate BERTScore
    precision, recall, f1 = score(candidate_texts, reference_texts, model_type=model_type, verbose=False)

    # Convert tensors to lists for readability
    return {
        "precision": precision.tolist()[0],
        "recall": recall.tolist()[0],
        "f1": f1.tolist()[0]
    }

def evaluate_generated_rationale(prompt_dir, versions):
    for version in versions:
        print(f"Inside Version: {version}")
        prompt_path = os.path.join(prompt_dir, version, 'response.csv')

        data = pd.read_csv(prompt_path)
        temp = data.apply(
            lambda row: calculate_bert_score(
                [row['Rationale']],  # Wrap in a list
                [row['generated_rationale']]  # Wrap in a list
            ),  # Extract the F1 score from the returned dictionary
            axis=1
        )

        data['BERTScore_precision'] = pd.Series([t['precision'] for t in temp])
        data['BERTScore_recall'] = pd.Series([t['recall'] for t in temp])
        data['BERTScore_f1'] = pd.Series([t['f1'] for t in temp])

        output_path = os.path.join(os.path.dirname(prompt_path), "response_eval.csv")
        data.to_csv(output_path, index=False)

        print(f"\nData saved to {output_path}\n")
        

if __name__ == "__main__":
    commit_hashes = ['010e8a303b1caf3b80e244fc5e4aebc23d854118', '0f70ac74cd07228bcf67db925b1c01c6b17fc092', '279777b2f3a43ed96eb8151f07b76f38672cc78f', '0728e32e7f3b93e49dfc8c7af20b489b12b3e663', '475c4d4425b2170c4a0f19d5bd39b70e752e38a1', '2624b909060e0967e16771de7a35261decd5a4a9', '2270df515b040d8612c691acc0102d1a224bcd82', '289d378aebd4782f422b880702fbd098122a389c', '19a1477228b8ed75926a15358e3253eb7ffa492e', '3b1d46b3bac74802d264cd57c4a7e685f377c91e', '231433f5406453069aa125329be042d5e32ddff0', '19a9bc4747028e68d0fc9ce71c302488cfbfa978', '02b539c5f50b59d9f5605c21e42d53f0c8e23ae1', '2e5d0470dc0c9766d98d144d5b6bd56248112e46', '030bc224e30699a91e33e27a6d9782803afbd0d4', '0634555424a8742bbe95333c49975437af6eacf8', '052bbcc53031bd48dc76d070ba862f5293618600', '1b1682eacd9c8aabbb86f24dc9c54070f3dd18b4', '947255e3774fe6248c59d2cdd6a1b06b9f6b5d9b']
    
    prompt_construct(PROMPT_DIR, PROMPT_TEMPLATE_PATH, PROMPT_RESULT_DIR, COMMIT_W_REL_TEXT_JSON, MANUAL_ANNOTATED_DATA, commit_hashes)
    rationale_generate(PROMPT_VERSION_DIR, PROMPT_VERSIONS)
    evaluate_generated_rationale(PROMPT_VERSION_DIR, PROMPT_VERSIONS)