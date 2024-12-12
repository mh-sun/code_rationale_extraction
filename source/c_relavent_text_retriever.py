import csv
import json
import os
import re
import pandas as pd
import torch
import torch.nn.functional as F
from tqdm import tqdm
from torch import Tensor
from transformers import AutoModel, AutoTokenizer
import spacy
from sklearn.metrics import precision_score, recall_score, f1_score, accuracy_score
from difflib import SequenceMatcher
from const import *

nlp = spacy.load("en_core_web_sm")

def check_text(text):
    return not not text and type(text) != type(0.0) and text != None

def get_query_prompt(query: str):
    query_description = 'Given a code change summary, retrieve relevant text that explain to the summary'
    prompt = f'Instruct: {query_description}\Summary: {query}'
    return prompt

def last_token_pool(last_hidden_states: Tensor, attention_mask: Tensor) -> Tensor:
    left_padding = (attention_mask[:, -1].sum() == attention_mask.shape[0])
    if left_padding:
        return last_hidden_states[:, -1]
    else:
        sequence_lengths = attention_mask.sum(dim=1) - 1
        batch_size = last_hidden_states.shape[0]
        return last_hidden_states[torch.arange(batch_size, device=last_hidden_states.device), sequence_lengths]

def get_relevant_texts(model, tokenizer, target_col, all_texts):
        inputs = tokenizer([get_query_prompt(target_col)] + all_texts, max_length=8192, padding=True, truncation=True, return_tensors='pt')
        outputs = model(**inputs)

        embeddings = last_token_pool(outputs.hidden_states[-1], inputs['attention_mask'])

        embeddings = F.normalize(embeddings, dim=1, p=2)
        similarity = embeddings @ embeddings.T
        similarity = similarity[0, 1:]
            
        top_k = min(10,len(similarity))
        top_indices = torch.topk(similarity, top_k).indices
            
        related_texts = []
        for rank, idx in enumerate(top_indices, start=1):
            rel_text = all_texts[idx]
            score = similarity[idx].item()

            related_texts.append({
                    "rank": rank,
                    "text": rel_text,
                    "similarity": score
                })
            
        return related_texts

def retrieve_relevant_text(input_path, output_path):
    with open(input_path, "r") as f:
        commits = json.load(f)

    token_limit = 2*1024
    model_name = "Kwaipilot/OASIS-code-1.3B"

    for commit in tqdm(commits, desc=f"Processing Commit"):
        if 'related_texts' in commit:
            continue
        try:
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            
            diff = commit['diff']
            summary = commit['cc_summary']['text']
            commit_message = commit['commit_subject']
            commit_body = commit['commit_body'] if check_text(commit['commit_body']) else ''

            texts = []
            for issue in commit['linked_issues']:
                texts.append(issue['issue_title'])

                if check_text(issue['issue_body']) and len(tokenizer.tokenize(issue['issue_body'])) <= token_limit:
                    texts.append(re.sub(r"\*\*\[.*?\]\(.*?\)\*\*.*?commented\n\n", "", issue['issue_body']))

                for comment in issue['issue_comment']:
                    if not check_text(comment) or len(tokenizer.tokenize(comment)) > token_limit:
                        continue

                    cleaned_text = re.sub(r"\*\*\[.*?\]\(.*?\)\*\* commented\n\n", "", comment) # Remove Comment Initial
                    cleaned_text = re.sub(r"\[.*?\]\(https.*?\)\s*,*\s*", "", cleaned_text) # Remove mentions

                    splitted_text = []
                    for st in cleaned_text.split('\n'):
                        flag = True

                        # Remove Reply
                        if st.startswith('>'):
                            flag = False

                        # Remove Stack Trace
                        doc = nlp(st)
                        dates = [ent.text for ent in doc.ents if ent.label_ == "DATE"]

                        if len(dates) >= 1 and "trace" in st.lower() or "info" in st.lower():
                            flag = False

                        # Remove Error Logs
                        match = re.search(r"\s*at.*?\(.*\.java\:\d+\).*", st)
                        if match != None:
                            flag = False

                        match = re.search(r"\t*... \d+ more", st)
                        if match != None:
                            flag = False

                        if flag:
                            splitted_text.append(st)

                    cleaned_text = '\n'.join(splitted_text)

                    texts.append(cleaned_text)

            merged_texts:list[str] = [commit_message, commit_body]
            merged_texts.extend(texts)

            # Parse Into Paragraph Level
            all_texts = []
            for text in merged_texts:
                try:
                    all_texts.extend(text.split('\n\n'))
                except Exception as e:
                    print(f"$$$ Error Found on {text}\n\nError:{e}")
            
            model = AutoModel.from_pretrained(model_name, output_hidden_states=True)

            related_texts_summary = get_relevant_texts(model, tokenizer, summary, all_texts)
            related_texts_diff = get_relevant_texts(model, tokenizer, diff, all_texts)
            
            commit['related_texts'] = {
                "summary": related_texts_summary,
                "diff": related_texts_diff
            }

            with open(output_path, "w") as f:
                json.dump(commits, f, indent=4)
        except Exception as e_out:
            print(f"### Error Found on {commit['commit_hash']}\n\nError: {e_out}")

    print(f"Related Texts Saved Successfully in {output_path}")

def get_reference_text(annotated_data, commit_hash):
    texts = []
    for commit in annotated_data:
        if commit['commit'] == commit_hash:
            for i in commit['IR_RATIONALE_PRES']:
                texts.extend(i.split('\n\n'))
            for i in commit['PR_RATIONALE_PRES']:
                texts.extend(i.split('\n\n'))
            for i in commit['CC_RATIONALE_PRES']:
                texts.extend(i.split('\n\n'))
            for i in commit['COM_T_RATIONALE_PRES']:
                texts.extend(i.split('\n\n'))
            for i in commit['COM_B_RATIONALE_PRES']:
                texts.extend(i.split('\n\n'))
            
            return texts
    return texts

def get_generated_texts(commits, commit_hash, col, k):
    texts = []
    for commit in commits:
        if commit['commit_hash'] == commit_hash:
            max_length = len(commit['related_texts'][col])
            data_count = min(k, max_length)

            texts = [t['text'] for t in commit['related_texts'][col][:data_count]]
            return texts
    
    return texts

def string_similarity(s1, s2):
    """Compute similarity between two strings using SequenceMatcher."""
    return SequenceMatcher(None, s1, s2).ratio()

def calculate_metrics(reference_texts, generated_texts, similarity_threshold=0.8):
    """Calculate precision, recall, F1, and accuracy."""
    tp = 0
    fp = 0
    fn = 0
    
    for gen_text in generated_texts:
        if any(string_similarity(gen_text, ref_text) >= similarity_threshold for ref_text in reference_texts):
            tp += 1  # True Positive
        else:
            fp += 1  # False Positive
    
    for ref_text in reference_texts:
        if not any(string_similarity(gen_text, ref_text) >= similarity_threshold for gen_text in generated_texts):
            fn += 1  # False Negative
    
    # Metrics calculation
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    accuracy = tp / len(generated_texts) if generated_texts else 0  

    return tp, fp, fn, precision, recall, f1, accuracy

def save_results_to_csv(results, file_path):
    """Save results to a CSV file."""
    header = ['k', 'source', 'commit_hash', 'tp', 'fp', 'fn', 'precision', 'recall', 'f1', 'accuracy']
    
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    with open(file_path, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(header)  # Write the header
        writer.writerows(results)  # Write each row of results

def evaluate_retrieved_text(input_path, annotated_data_path, output_path):
    with open(input_path, "r") as f:
        commits = json.load(f)

    with open(annotated_data_path, "r") as f:
        annotated_data = json.load(f)

    commits_in_annotation = set([c['commit'] for c in annotated_data])
    commits_in_generated = set([c['commit_hash'] for c in commits])

    commits_hashes = commits_in_annotation.intersection(commits_in_generated)

    results = []
    for k in range(1,11):
        for col in ['summary', 'diff']:
            for commit_hash in commits_hashes:
                reference_texts = get_reference_text(annotated_data, commit_hash)
                generated_texts = get_generated_texts(commits, commit_hash, col, k)

                tp, fp, fn, precision, recall, f1, accuracy = calculate_metrics(reference_texts, generated_texts)
                results.append([k, col, commit_hash, tp, fp, fn, precision, recall, f1, accuracy])

    save_results_to_csv(results, output_path)

    df = pd.DataFrame(results, columns=['k', 'source', 'commit_hash', 'tp', 'fp', 'fn', 'precision', 'recall', 'f1', 'accuracy'])
    grouped = df.groupby(['k', 'source'], as_index=False).agg({'tp': 'sum', 'fp': 'sum', 'fn': 'sum'})

    # Calculate precision, recall, f1, and accuracy
    grouped['precision'] = grouped['tp'] / (grouped['tp'] + grouped['fp'])
    grouped['recall'] = grouped['tp'] / (grouped['tp'] + grouped['fn'])
    grouped['f1'] = 2 * (grouped['precision'] * grouped['recall']) / (grouped['precision'] + grouped['recall'])
    grouped['accuracy'] = grouped['tp'] / (grouped['tp'] + grouped['fp'] + grouped['fn'])

    # Handle potential division by zero
    grouped = grouped.fillna(0)

    # Display the grouped results
    print(grouped)

    grouped.to_csv(RETRIEVED_DATA_EVAL_ACC, index=False)

if __name__=="__main__":
    # retrieve_relevant_text(COMMIT_W_CC_SUMMARY_JSON, COMMIT_W_REL_TEXT_JSON)
    evaluate_retrieved_text(COMMIT_W_REL_TEXT_JSON, MANUAL_ANNOTATED_DATA, RETRIEVED_DATA_EVAL)