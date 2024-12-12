import json
import os
import re
import torch
import torch.nn.functional as F
from tqdm import tqdm

from torch import Tensor
from transformers import AutoModel, AutoTokenizer
import spacy

from const import *

nlp = spacy.load("en_core_web_sm")

def check_text(text):
    return not not text and type(text) != type(0.0)

with open(COMMIT_W_CC_SUMMARY_JSON, "r") as f:
    commits = json.load(f)

token_limit = 2*1024

for commit in tqdm(commits, desc=f"Processing Commit"):
    if 'related_texts' in commit:
        continue
    
    try:
        tokenizer = AutoTokenizer.from_pretrained("Kwaipilot/OASIS-code-1.3B")
        
        diff = commit['diff']
        summary = commit['cc_summary']['text']
        commit_message = commit['commit_subject']
        commit_body = commit['commit_body'] if check_text(commit['commit_body']) else ''

        target_col = summary

        texts = []
        for issue in commit['linked_issues']:
            texts.append(issue['issue_title'])

            if check_text(issue['issue_body']) or len(tokenizer.tokenize(issue['issue_body'])) <= token_limit:
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
        
        def last_token_pool(last_hidden_states: Tensor, attention_mask: Tensor) -> Tensor:
            left_padding = (attention_mask[:, -1].sum() == attention_mask.shape[0])
            if left_padding:
                return last_hidden_states[:, -1]
            else:
                sequence_lengths = attention_mask.sum(dim=1) - 1
                batch_size = last_hidden_states.shape[0]
                return last_hidden_states[torch.arange(batch_size, device=last_hidden_states.device), sequence_lengths]

        def get_query_prompt(query: str):
            query_description = 'Given a code change summary, retrieve relevant text that explain to the summary'
            prompt = f'Instruct: {query_description}\Summary: {query}'
            return prompt

        model = AutoModel.from_pretrained("Kwaipilot/OASIS-code-1.3B", output_hidden_states=True)

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
        
        commit['related_texts'] = related_texts

        with open(COMMIT_W_REL_TEXT_JSON, "w") as f:
            json.dump(commits, f, indent=4)
    except Exception as e_out:
        print(f"### Error Found on {commit['commit_hash']}\n\nError: {e_out}")

print(f"Related Texts Saved Successfully in {COMMIT_W_REL_TEXT_JSON}")