import pandas as pd
import torch
from tqdm import tqdm
from transformers import pipeline


def add_diff_summary(input_path, output_path):
    df = pd.read_csv(input_path)
    model_id = "meta-llama/Llama-3.2-1B-Instruct"

    global pipe
    pipe = pipeline(
        "text-generation",
        model=model_id,
        torch_dtype=torch.bfloat16,
        device_map={"": torch.device("cuda:0")},
    )

    def summarize_diff(diff_text):
        messages = [
            {"role": "system", "content": "You are a java expert who understand a java file's git diff very well"},
            {"role": "user",
             "content": f"here is a diff a file\n\n{diff_text}\n\nsummarize what has changed here in one sentence, clearly and precisely."},
        ]
        outputs = pipe(
            messages,
            max_length=10240,
            pad_token_id=pipe.tokenizer.eos_token_id
        )
        response = outputs[0]["generated_text"][-1]['content']
        return response

    tqdm.pandas()
    df['diff_summary'] = df['diff'].progress_apply(summarize_diff)
    df.to_csv(output_path, index=False)


if __name__ == '__main__':
    issue_details_path = 'dataset/cr_list_issue_details.csv'
    issue_diff_summary_path = 'dataset/diff_summary_added.csv'
    issue_diff_summary_comment_match = 'dataset/issue_diff_summary_comment_match.csv'

    add_diff_summary(issue_details_path, issue_diff_summary_path)
