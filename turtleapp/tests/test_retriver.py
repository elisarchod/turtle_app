from typing import Dict

import pytest
from dotenv import load_dotenv
from langchain import hub
from langchain_openai import ChatOpenAI
from langsmith.schemas import Example, Run

from turtleapp.src.utils import logger
from turtleapp.src.nodes import ToolAgent
from turtleapp.src.core.tools import movie_retriever_tool

load_dotenv(override=True)

EVALSET_NAME = "home_assistant_recommendations"

grade_prompt_doc_relevance = hub.pull("langchain-ai/rag-document-relevance")
grade_prompt_hallucinations = hub.pull("langchain-ai/rag-answer-hallucination")
grade_prompt_answer_helpfulness = hub.pull("langchain-ai/rag-answer-helpfulness")
llm = ChatOpenAI(model="gpt-4-turbo", temperature=0)

retriever_agent = ToolAgent(movie_retriever_tool)


@pytest.fixture
def test_query():
    """Fixture providing a test query for retriever tests."""
    return {"messages": "recommend 3 comedy movies"}


@pytest.fixture
def retriever_response(test_query):
    """Fixture providing a retriever agent response."""
    return retriever_agent.process(test_query)


@pytest.fixture
def mock_run(retriever_response, test_query):
    """Fixture providing a mock run for evaluation tests."""
    return Run(
        name="test_run",
        inputs=test_query,
        outputs={"output": retriever_response.update['messages'][-1].content},
        child_runs=[
            Run(
                name="data_retriever_agent",
                child_runs=[
                    Run(
                        name="tools",
                        child_runs=[
                            Run(
                                name="movie_plots_tool",
                                outputs={"documents": retriever_response.update['messages'][-1].additional_kwargs.get("documents", [])}
                            )
                        ]
                    )
                ]
            )
        ]
    )


def predict_rag_answer(example: Dict[str, str]) -> Dict[str, str]:
    response = retriever_agent.process(example).update['messages'][-1]
    return {"output": response.content, "output_context": response}


def get_nested_run_by_names(runs, names):
    current_run = runs
    for name in names:
        current_run = next(run for run in current_run if run.name == name).child_runs
    return current_run


def get_run_by_name(runs, name):
    return next(run for run in runs if run.name == name)


def document_relevance_grader(root_run: Run, example: Example) -> dict:
    try:
        names = ["data_retriever_agent", "tools", "movie_plots_tool"]
        inner_retrieve_run = get_nested_run_by_names(root_run.child_runs, names)[0]
        
        documents = inner_retrieve_run.outputs.get("documents", [])
        if not documents:
            return {"key": "document_relevance", "score": 0, "error": "No documents retrieved"}
            
        contexts = "\n\n".join([doc.page_content for doc in documents])
        input_question = example.inputs["messages"]

        answer_grader = grade_prompt_doc_relevance | llm
        score = answer_grader.invoke({"question": input_question, "documents": contexts})
        
        return {"key": "document_relevance", "score": score["Score"]}
    except Exception as e:
        logger.error(f"Error in document relevance grading: {str(e)}")
        return {"key": "document_relevance", "score": 0, "error": str(e)}


def answer_hallucination_grader(root_run: Run, example: Example) -> dict:
    try:
        names = ["data_retriever_agent", "tools", "movie_plots_tool"]
        inner_retrieve_run = get_nested_run_by_names(root_run.child_runs, names)[0]
        
        documents = inner_retrieve_run.outputs.get("documents", [])
        if not documents:
            return {"key": "answer_hallucination", "score": 0, "error": "No documents retrieved"}
            
        contexts = "\n\n".join([doc.page_content for doc in documents])
        prediction = root_run.outputs["output"]

        answer_grader = grade_prompt_hallucinations | llm
        score = answer_grader.invoke({"student_answer": prediction, "documents": contexts})
        
        return {"key": "answer_hallucination", "score": score["Score"]}
    except Exception as e:
        logger.error(f"Error in answer hallucination grading: {str(e)}")
        return {"key": "answer_hallucination", "score": 0, "error": str(e)}


def test_retriever_agent_response(retriever_response):
    """Test that the retriever agent returns a valid response."""
    assert retriever_response is not None
    assert 'messages' in retriever_response.update
    assert len(retriever_response.update['messages']) > 0
    logger.info("Retriever agent response test passed")


def test_document_relevance_evaluation(mock_run, test_query):
    """Test document relevance evaluation."""
    example = Example(
        inputs=test_query,
        outputs={"output": mock_run.outputs["output"]}
    )
    
    relevance_score = document_relevance_grader(mock_run, example)
    assert "key" in relevance_score
    assert relevance_score["key"] == "document_relevance"
    assert "score" in relevance_score
    logger.info(f"Document Relevance Score: {relevance_score}")


def test_answer_hallucination_evaluation(mock_run, test_query):
    """Test answer hallucination evaluation."""
    example = Example(
        inputs=test_query,
        outputs={"output": mock_run.outputs["output"]}
    )
    
    hallucination_score = answer_hallucination_grader(mock_run, example)
    assert "key" in hallucination_score
    assert hallucination_score["key"] == "answer_hallucination"
    assert "score" in hallucination_score
    logger.info(f"Answer Hallucination Score: {hallucination_score}")


def test_rag_answer_prediction(test_query):
    """Test RAG answer prediction functionality."""
    result = predict_rag_answer(test_query)
    assert "output" in result
    assert "output_context" in result
    assert isinstance(result["output"], str)
    assert len(result["output"]) > 0