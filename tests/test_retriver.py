from typing import Dict

from dotenv import load_dotenv
from langchain import hub
from langchain_openai import ChatOpenAI
from langsmith import Client
from langsmith.schemas import Example, Run
from langsmith import evaluate
load_dotenv(override=True)
from turtleapp.src.nodes.agents import retriver_node

EVALSET_NAME = "home_assistant_recommendations"

grade_prompt_doc_relevance = hub.pull("langchain-ai/rag-document-relevance")
grade_prompt_hallucinations = hub.pull("langchain-ai/rag-answer-hallucination")
grade_prompt_answer_helpfulness = hub.pull("langchain-ai/rag-answer-helpfulness")
llm = ChatOpenAI(model="gpt-4-turbo", temperature=0)


def predict_rag_answer(example: Dict[str, str]) -> Dict[str, str]:
    """Use this for answer evaluation"""
    response = retriver_node(example).update['messages'][-1]
    return {"output": response.content, "output_context": response}


def get_nested_run_by_names(runs, names):
    current_run = runs
    for name in names:
        current_run = next(run for run in current_run if run.name == name).child_runs
    return current_run


def get_run_by_name(runs, name):
    return next(run for run in runs if run.name == name)

def document_relevance_grader(root_run: Run, example: Example) -> dict:
    """
    A simple evaluator that checks to see if retrieved documents are relevant to the question
    """

    # Get specific steps in our RAG pipeline, which are noted with @traceable decorator
    names = ["data_retriever_agent", "tools", "movie_plots_tool"]
    inner_retrieve_run = get_nested_run_by_names(root_run.child_runs, names)[0]
    contexts = "\n\n".join([document.page_content for document in
                               inner_retrieve_run.outputs["documents"]])
    input_question = example.inputs["messages"]

    # grade
    answer_grader = grade_prompt_doc_relevance | llm
    score = answer_grader.invoke({"question": input_question, "documents": contexts})
    score = score["Score"]
    return {"key": "document_relevance", "score": score}


def answer_hallucination_grader(root_run: Run, example: Example) -> dict:
    """
    A simple evaluator that checks to see the answer is grounded in the documents
    """

    # RAG input
    # rag_pipeline_run = get_run_by_name(root_run.child_runs, "data_retriever_agent")
    # tool_run = get_run_by_name(rag_pipeline_run.child_runs, "tools")
    # retrieve_run = get_run_by_name(tool_run.child_runs, "movie_plots_store")
    # inner_retrieve_run = get_run_by_name(retrieve_run.child_runs, "VectorStoreRetriever")

    names = ["data_retriever_agent", "tools", "movie_plots_tool"]
    inner_retrieve_run = get_nested_run_by_names(root_run.child_runs, names)[0]
    contexts = "\n\n".join([document.page_content for document in inner_retrieve_run.outputs["documents"]])
    prediction = root_run.outputs["output"]

    # grader
    answer_grader = grade_prompt_hallucinations | llm
    score = answer_grader.invoke({"student_answer": prediction, "documents": contexts})
    score = score["Score"]
    return {"key": "answer_hallucination", "score": score}

if __name__ == "__main__": # document_relevance_grader
    experiment_results = evaluate(predict_rag_answer,
                                  data=EVALSET_NAME,
                                  evaluators=[document_relevance_grader,
                                              answer_hallucination_grader
                                      ]
                                      )

        # response = retriver_node({"messages": "recommend 3 comedy movies"})
        # response.update['messages'][-1].pretty_print()
        # pp = response.update['messages'][-1]
        # client = Client()
        # list(client.list_datasets())
        # example = list(client.list_examples(dataset_name=EVALSET_NAME))[0]
        # example.inputs  # example