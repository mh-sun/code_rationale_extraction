import ast

import numpy as np
import pandas as pd
import spacy
import torch
from scipy.spatial.distance import euclidean
from sklearn.metrics.pairwise import cosine_similarity
from tqdm import tqdm
from transformers import RobertaTokenizer, RobertaModel

nlp = spacy.load("en_core_web_lg")

tokenizer = RobertaTokenizer.from_pretrained('microsoft/codebert-base')
model = RobertaModel.from_pretrained('microsoft/codebert-base')


def calculate_similar_comment_score(input_path, output_path):
    def get_embeddings(text):
        inputs = tokenizer(text, return_tensors="pt", truncation=True, padding=True, max_length=512)

        with torch.no_grad():
            outputs = model(**inputs)

        embeddings = outputs.last_hidden_state.mean(dim=1).squeeze().numpy()
        return embeddings

    def average_sentence_embeddings(comment):
        doc = nlp(comment)
        sentences = [sent.text.strip() for sent in doc.sents]

        # Get embeddings for each sentence and average them
        sentence_embeddings = [get_embeddings(sentence) for sentence in sentences if sentence]
        avg_embedding = np.mean(sentence_embeddings, axis=0) if sentence_embeddings else np.zeros(
            768)  # CodeBERT output dimension is 768

        return avg_embedding

    def calculate_relevance_scores(code_description, comments):
        # Get the embedding for the code description
        code_vector = get_embeddings(code_description)

        scored_comments = []
        for comment in comments:
            # Get the embedding for the comment
            comment_vector = get_embeddings(comment)

            # Reshape the vectors to 2D for cosine similarity
            code_vector_reshaped = code_vector.reshape(1, -1)
            comment_vector_reshaped = comment_vector.reshape(1, -1)

            # Compute cosine similarity (closer to 1 means more similar)
            similarity_score = cosine_similarity(code_vector_reshaped, comment_vector_reshaped)[0][0]

            # Store the comment with its similarity score
            scored_comments.append((comment, similarity_score))

        # Sort comments by their similarity score in descending order (higher is more relevant)
        scored_comments.sort(key=lambda x: x[1], reverse=True)

        return scored_comments

    df = pd.read_csv(input_path)
    df = df.fillna('')

    def add_similarity(row):
        diff_description = row['diff_summary']
        comments = ast.literal_eval(row['issue_comments']) if row['issue_comments'] else []

        scored_comments = calculate_relevance_scores(diff_description, comments)

        return scored_comments

    tqdm.pandas()
    df["comments_with_similarity"] = df.progress_apply(lambda x: add_similarity(x), axis=1)
    df["comments_with_similarity"] = df["comments_with_similarity"].apply(
        lambda x: ', '.join([f"{comment}: {score:.2f}" for comment, score in x])
    )

    df.to_csv(output_path, index=False)



issue_diff_summary_path = 'dataset/diff_summary_added.csv'
issue_diff_summary_comment_match = 'dataset/issue_diff_summary_comment_match.csv'

calculate_similar_comment_score(issue_diff_summary_path, issue_diff_summary_comment_match)
