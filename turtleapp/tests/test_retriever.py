from typing import Dict

import pytest
from langchain import hub
from langchain_anthropic import ChatAnthropic
from langsmith.schemas import Example, Run

from turtleapp.src.utils import logger
from turtleapp.src.nodes import ToolAgent
from turtleapp.src.core.tools import movie_retriever_tool
from turtleapp.settings import settings

EVALSET_NAME = "home_assistant_recommendations"

grade_prompt_doc_relevance = hub.pull("langchain-ai/rag-document-relevance")
grade_prompt_hallucinations = hub.pull("langchain-ai/rag-answer-hallucination")
grade_prompt_answer_helpfulness = hub.pull("langchain-ai/rag-answer-helpfulness")
llm = ChatAnthropic(model="claude-3-5-sonnet-20241022", temperature=0, api_key=settings.claude.api_key)

retriever_agent = ToolAgent(movie_retriever_tool)


@pytest.fixture
def test_query():
    """Fixture providing a test query for retriever tests."""
    return {"messages": "recommend 3 comedy movies"}


@pytest.fixture
async def retriever_response(test_query):
    """Fixture providing a retriever agent response (async)."""
    return await retriever_agent.process(test_query)


@pytest.fixture
async def mock_run(retriever_response, test_query):
    """Fixture providing a mock run for evaluation tests (async)."""
    import uuid
    from datetime import datetime

    retriever_response = await retriever_response
    run_id = str(uuid.uuid4())
    trace_id = str(uuid.uuid4())
    start_time = datetime.now()

    return Run(
        id=run_id,
        name="test_run",
        start_time=start_time,
        run_type="chain",
        trace_id=trace_id,
        inputs=test_query,
        outputs={"output": retriever_response.update['messages'][-1].content},
        child_runs=[
            Run(
                id=str(uuid.uuid4()),
                name="data_retriever_agent",
                start_time=start_time,
                run_type="chain",
                trace_id=trace_id,
                child_runs=[
                    Run(
                        id=str(uuid.uuid4()),
                        name="tools",
                        start_time=start_time,
                        run_type="chain",
                        trace_id=trace_id,
                        child_runs=[
                            Run(
                                id=str(uuid.uuid4()),
                                name="movie_plots_tool",
                                start_time=start_time,
                                run_type="tool",
                                trace_id=trace_id,
                                outputs={"documents": retriever_response.update['messages'][-1].additional_kwargs.get("documents", [])}
                            )
                        ]
                    )
                ]
            )
        ]
    )


async def predict_rag_answer(example: Dict[str, str]) -> Dict[str, str]:
    """Async version of RAG answer prediction."""
    response = await retriever_agent.process(example)
    return {"output": response.update['messages'][-1].content, "output_context": response}


def get_nested_run_by_names(runs, names):
    current_run = runs
    for name in names:
        current_run = next(run for run in current_run if run.name == name).child_runs
    return current_run


async def document_relevance_grader(root_run: Run, example: Example) -> dict:
    """Async version of document relevance grader."""
    try:
        names = ["data_retriever_agent", "tools", "movie_plots_tool"]
        inner_retrieve_run = get_nested_run_by_names(root_run.child_runs, names)[0]
        
        documents = inner_retrieve_run.outputs.get("documents", [])
        if not documents:
            return {"key": "document_relevance", "score": 0, "error": "No documents retrieved"}
            
        contexts = "\n\n".join([doc.page_content for doc in documents])
        input_question = example.inputs["messages"]

        answer_grader = grade_prompt_doc_relevance | llm
        score = await answer_grader.ainvoke({"question": input_question, "documents": contexts})
        
        return {"key": "document_relevance", "score": score["Score"]}
    except Exception as e:
        logger.error(f"Error in document relevance grading: {str(e)}")
        return {"key": "document_relevance", "score": 0, "error": str(e)}


async def answer_hallucination_grader(root_run: Run, example: Example) -> dict:
    """Async version of answer hallucination grader."""
    try:
        names = ["data_retriever_agent", "tools", "movie_plots_tool"]
        inner_retrieve_run = get_nested_run_by_names(root_run.child_runs, names)[0]
        
        documents = inner_retrieve_run.outputs.get("documents", [])
        if not documents:
            return {"key": "answer_hallucination", "score": 0, "error": "No documents retrieved"}
            
        contexts = "\n\n".join([doc.page_content for doc in documents])
        prediction = root_run.outputs["output"]

        answer_grader = grade_prompt_hallucinations | llm
        score = await answer_grader.ainvoke({"student_answer": prediction, "documents": contexts})
        
        return {"key": "answer_hallucination", "score": score["Score"]}
    except Exception as e:
        logger.error(f"Error in answer hallucination grading: {str(e)}")
        return {"key": "answer_hallucination", "score": 0, "error": str(e)}


@pytest.mark.asyncio
async def test_retriever_agent_response(request):
    """Test that the retriever agent returns a valid response."""
    retriever_response = await request.getfixturevalue('retriever_response')
    assert retriever_response is not None
    assert 'messages' in retriever_response.update
    assert len(retriever_response.update['messages']) > 0
    logger.info("Retriever agent response test passed")


@pytest.mark.asyncio
async def test_rag_answer_prediction(request):
    """Test RAG answer prediction functionality."""
    test_query = request.getfixturevalue('test_query')
    result = await predict_rag_answer(test_query)
    assert "output" in result
    assert "output_context" in result
    assert isinstance(result["output"], str)
    assert len(result["output"]) > 0
    logger.info("RAG answer prediction test passed")


# Optional expensive RAG evaluation tests - only run when explicitly requested
@pytest.mark.asyncio
@pytest.mark.slow
async def test_document_relevance_evaluation(request):
    """Test document relevance evaluation (expensive - requires LLM calls)."""
    test_query = request.getfixturevalue('test_query')
    mock_run = await request.getfixturevalue('mock_run')
    import uuid
    example = Example(
        id=str(uuid.uuid4()),
        inputs=test_query,
        outputs={"output": mock_run.outputs["output"]}
    )
    
    relevance_score = await document_relevance_grader(mock_run, example)
    assert "key" in relevance_score
    assert relevance_score["key"] == "document_relevance"
    assert "score" in relevance_score
    logger.info(f"Document Relevance Score: {relevance_score}")


@pytest.mark.asyncio
@pytest.mark.slow
async def test_answer_hallucination_evaluation(request):
    """Test answer hallucination evaluation (expensive - requires LLM calls)."""
    test_query = request.getfixturevalue('test_query')
    mock_run = await request.getfixturevalue('mock_run')
    import uuid
    example = Example(
        id=str(uuid.uuid4()),
        inputs=test_query,
        outputs={"output": mock_run.outputs["output"]}
    )
    
    hallucination_score = await answer_hallucination_grader(mock_run, example)
    assert "key" in hallucination_score
    assert hallucination_score["key"] == "answer_hallucination"
    assert "score" in hallucination_score
    logger.info(f"Answer Hallucination Score: {hallucination_score}")