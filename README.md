# Explaining the Whys In Source Code

## Abstract
Developers spend approximately 60\% of their time understanding the source code. Developers spend this much time because, when recording code changes, the emphasis is often on what has changed rather than why the change was made. While tools like Git facilitate recording "what" has changed very easily, they fail to provide support capturing the rationale behind code changes. This research investigates the potential of automated techniques and large language models (LLMs) to systematically extract and manage the answer to those "whys" questions which we call \textit{rationale} from software artifacts such as commit messages, issue logs, discussions, etc. This paper explores the capabilities of prompts and multi-model architectures and assesses the extent to which rationale can be effectively extracted from documentation linked to source code. The evaluation shows this project scored 63\%, and 67\% in precision, and recall scores respectively while extracting rationales texts from different sources. Additionally, Chain-of-Thought Prompting outperformed Zero-Shot and One-Shot prompts in constructing rationales.

# Installation Process

## Prerequisites
- Python 3.10.16 (Also Works with Python 3.10+)
- Hypothes.is API Token : To collect annotated data
- GEMINI API Token: To get the Gemini model to produce code change summary
- Hugging Face API Token: To run the prompt engineering experiments for Llama

## Environment Setup

### Install python required package
- pip install -r requirements.txt

# Directory Structure

## dataset
 This folder contains all the intermediate files and folder (Spring Framework Repo) used in the paper. The folder contains following important files:
1. ```dataset/annotated_dataset.json```: This file consist of annotated data
2. ```dataset/manual_analyzed_issues.csv```: This CSV File consist of Manually Analyzed Issues.
3. ```dataset/spring-framework```: This is the target folder which will be created when run.sh is run.

## prompt
This folder contains prompt templates for various experiments. Inside the ```version``` folder, there are nine subfolders, each corresponding to a specific version of the prompt. Within each subfolder, there are three files.

1. ```prompt/version/<version>/prompt.csv```: This is the prompt file which will be use to model's input.
2. ```prompt/version/<version>/response_eval.csv```: This is a evaluation file of model's response.
3. ```prompt/version/<version>/response.csv```: This file is generated after model's prompt response generation is complete.

## results
This folder holds results of Retriever Model and Prompt Model.

## sources
This folder contains the source code for the data preparation, tuning, and evaluation of the models for all experiments. This folder contains the following files:

1. ```source/a_get_annotated_data.py```: This script collect the annotated data from hypothe.is api.
2. ```source/b_data_preparation.py```: This script clone the target projects to local machine & extract filtered commits with explicit change types.
3. ```source/c_data_process.py```: This script links commits to its issues, add summary of code change export data as JSON.
4. ```source/d_relavent_text_retriever.py```: This script retrieve all relevant texts for each commit. It is the Retriever model Class.
5. ```source/e_prompt_engineering.py```: This script conduct the prompt engineering experiments.

# Run Models:

Provide User Permission to The run.sh File.
1. chmod +x run.sh

Run run.sh 
2. ./run.sh

## Machine Information
To run the experiments I have used both CPU and GPU. Below I mentioned the machine information I have used to train and evaluate my models.

#### 1. ```Machine 1```: 
    1.1. CPU: Intel(R) Xeon(R) Gold 6254, Memory: 754 GB
    1.2. GPU: NVIDIA A40, Memory: 46068 MB
