# Explaining the Whys In Source Code

## Abstract
Developers spend approximately 60% of their time comprehending code, often focusing on "what" has changed rather than "why" it changed. While tools like Git facilitate recording "what" has changed, capturing the rationale behind code changes remains an underexplored area. This research investigates the potential of automated techniques and large language models (LLMs) to systematically extract and manage rationale information ("whys") from software artifacts such as commit messages, issue logs, and discussions. By exploring the capabilities of prompts and multi-modal architectures, it assesses the extent to which rationale can be effectively extracted from documentation linked to source code. The findings emphasize the efficacy of these approaches for software engineering tasks, underscore the lack of benchmarks, and propose strategies for standardizing rationale extraction across software development workflows.

# Installation Process

## Prerequisites
- Python 3.10.16 (Also Works with Python 3.10+)

## Environment Setup

### Install python required package
- pip install -r requirements.txt

# Directory Structure

## dataset
<!-- This folder contains all the dataset used in the paper. The folder contains following subfolders:
1. ```dataset/annotation_data```: This folder contains the annotation data, i.e., all the comments for all the 356 issues with the annotated code assigned by human annotators.
2. ```dataset/issue_data```: This folder contains the issue title, summary, and meta-data information for the 356 issues.
3. ```solution_identification_data```: This folder contains the solution identification data, i.e., the issue comments labeled as either solution or non-solution and dataset split (prompt set, train set, and test set). -->

## prompting
<!-- This folder contains 10 prompts templates used for the prompting experiments. It also contains the generated prompts and responses for all the 10 prompts with all the 10 folds test dataset for three runs. -->

## results
<!-- This folder contains results of MLMs, PLMs, LLM-prompting, and LLM-fine-tuning experiments. -->

## results_analysis
<!-- This folder contains the ensembled models analysis and the results analysis across issue types and problems categories. -->

## sources
This folder contains the source code for the data preparation, tuning, and evaluation of the models for all experiments. This folder contains the following files:

1. ```source/a_data_preparation.py```: This script clone the target projects to local machine & extract filtered commits with explicit change types.
<!-- 2. ```b_preprocess_data.py```: This script preprocess the comment data to be used in MLMs experiments. 
3. ```c_generate_embeddings.py```: This script generate LM embeddings (Llama, GPT, BERT) to be used in MLMs experiments.
4. ```d_mlm_experiments.py```: This script run all MLMs and save the results to ```results/ml``` folder.
5. ```e_plm_experiments.py```: This script run all PLMs and save the results to ```results/plm``` folder.
6. ```f_llm_prompting_experiments.py```: This script run the LLM prompting experiments.
7. ```g_compute_metrics_for_prompting.py```: This script save the results to ```results/llm_prompting``` folder.
8. ```h_llm_fine_tuning_experiments.py```: This script run the LLM finetuning experiments and save results to ```results/llm_fine_tuning``` folder. -->

# Run Models:
<!-- 1. chmod +x solution_localization.sh

Provile User Permission to The solution_localization.sh File.

2. ./solution_localization.sh

Run solution_localization.sh  -->

## Machine Information
To run the experiments I have used both CPU and GPU. Below I mentioned the machine information I have used to train and evaluate my models.

#### 1. ```Machine 1```: 
    1.1. CPU: Intel(R) Xeon(R) Gold 6254, Memory: 754 GB
    1.2. GPU: NVIDIA A40, Memory: 46068 MB
