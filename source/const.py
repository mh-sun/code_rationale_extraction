TARGET_PROJ = "https://github.com/spring-projects/spring-framework.git"
TARGET_PROJ_LOCAL = "dataset/repos/spring-framework"
TARGET_PROJ_LAST_COMMIT = "d1d6ff87372ddf5d362e30b0e27d8b14270d221a"

COMMIT_DETAILS = "dataset/commit_list.csv"
COMMIT_W_ISSUE_ID = 'dataset/commit_list_issue_ids.csv'
COMMIT_W_ISSUE_DESC = 'dataset/commit_list_issue_details.csv'
COMMIT_W_CC_SUMMARY = 'dataset/commit_list_issue_cc_summ.csv'
COMMIT_W_CC_SUMMARY_JSON = 'dataset/commit_list_issue_cc_summ.json'
COMMIT_W_REL_TEXT_JSON = 'dataset/commit_list_related_text.json'
COMMIT_LIST_MANNUAL_ANALYSIS = 'dataset/commit_list_manual_analysis.csv'

MANUAL_ANNOTATED_DATA = "dataset/annotated_dataset.json"
RETRIEVED_DATA_EVAL = "results/retrieved_data_eval.csv"
RETRIEVED_DATA_EVAL_ACC = "results/retrieved_data_eval_acc.csv"

ALL_ISSUES = "dataset/all_issues.json"

FEW_SHOT_N = 1
PROMPT_VERSIONS = ["1.1.0.0", "1.1.0.1", "1.1.0.2", "1.2.0.0", "1.2.0.1", "1.2.0.2", "1.3.0.0", "1.3.0.1", "1.3.0.2"]
PROMPT_DIR = "prompt/"
PROMPT_VERSION_DIR = "prompt/version"
PROMPT_TEMPLATE_PATH = "prompt/prompt_templates.csv"
MODEL_DIR = "/scratch/projects/mehedi/models"
PROMPT_RESULT_DIR = "results/prompt"
RATIONALE_CONSTRUCT = {
    "model_name" : "meta-llama/Meta-Llama-3-8B-Instruct"
}