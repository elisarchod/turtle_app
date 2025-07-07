from typing import Dict

from dotenv import load_dotenv
from langchain import hub
from langchain_openai import ChatOpenAI
from langsmith.schemas import Example, Run

from turtleapp.src.utils.log_handler import logger
from turtleapp.src.nodes.agents import ToolAgent
from turtleapp.src.core.tools import retriever_tool

load_dotenv(override=True)

EVALSET_NAME = "home_assistant_recommendations"

grade_prompt_doc_relevance = hub.pull("langchain-ai/rag-document-relevance")
grade_prompt_hallucinations = hub.pull("langchain-ai/rag-answer-hallucination")
grade_prompt_answer_helpfulness = hub.pull("langchain-ai/rag-answer-helpfulness")
llm = ChatOpenAI(model="gpt-4-turbo", temperature=0)

# Create a singleton instance for testing
retriever_agent = ToolAgent(retriever_tool)

def predict_rag_answer(example: Dict[str, str]) -> Dict[str, str]:
    """Use this for answer evaluation"""
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
    """
    A simple evaluator that checks to see if retrieved documents are relevant to the question
    """
    try:
        # Get specific steps in our RAG pipeline
        names = ["data_retriever_agent", "tools", "movie_plots_tool"]
        inner_retrieve_run = get_nested_run_by_names(root_run.child_runs, names)[0]
        
        # Get documents and question
        documents = inner_retrieve_run.outputs.get("documents", [])
        if not documents:
            return {"key": "document_relevance", "score": 0, "error": "No documents retrieved"}
            
        contexts = "\n\n".join([doc.page_content for doc in documents])
        input_question = example.inputs["messages"]

        # Grade using the prompt
        answer_grader = grade_prompt_doc_relevance | llm
        score = answer_grader.invoke({"question": input_question, "documents": contexts})
        
        return {"key": "document_relevance", "score": score["Score"]}
    except Exception as e:
        logger.error(f"Error in document relevance grading: {str(e)}")
        return {"key": "document_relevance", "score": 0, "error": str(e)}


def answer_hallucination_grader(root_run: Run, example: Example) -> dict:
    """
    A simple evaluator that checks to see if the answer is grounded in the documents
    """
    try:
        # Get documents and prediction
        names = ["data_retriever_agent", "tools", "movie_plots_tool"]
        inner_retrieve_run = get_nested_run_by_names(root_run.child_runs, names)[0]
        
        documents = inner_retrieve_run.outputs.get("documents", [])
        if not documents:
            return {"key": "answer_hallucination", "score": 0, "error": "No documents retrieved"}
            
        contexts = "\n\n".join([doc.page_content for doc in documents])
        prediction = root_run.outputs["output"]

        # Grade using the prompt
        answer_grader = grade_prompt_hallucinations | llm
        score = answer_grader.invoke({"student_answer": prediction, "documents": contexts})
        
        return {"key": "answer_hallucination", "score": score["Score"]}
    except Exception as e:
        logger.error(f"Error in answer hallucination grading: {str(e)}")
        return {"key": "answer_hallucination", "score": 0, "error": str(e)}

if __name__ == "__main__":
    # Test query
    test_query = {"messages": "recommend 3 comedy movies"}
    
    # Get response from retriever
    response = retriever_agent.process(test_query)
    logger.info("Retriever agent response:", response)
    
    # Create a mock Example object for evaluation
    example = Example(
        inputs=test_query,
        outputs={"output": response.update['messages'][-1].content}
    )
    
    # Create a mock Run object with the necessary structure
    mock_run = Run(
        name="test_run",
        inputs=test_query,
        outputs={"output": response.update['messages'][-1].content},
        child_runs=[
            Run(
                name="data_retriever_agent",
                child_runs=[
                    Run(
                        name="tools",
                        child_runs=[
                            Run(
                                name="movie_plots_tool",
                                outputs={"documents": response.update['messages'][-1].additional_kwargs.get("documents", [])}
                            )
                        ]
                    )
                ]
            )
        ]
    )
    
    # Test document relevance
    relevance_score = document_relevance_grader(mock_run, example)
    logger.info(f"Document Relevance Score: {relevance_score}")
    
    # Test answer hallucination
    hallucination_score = answer_hallucination_grader(mock_run, example)
    logger.info(f"Answer Hallucination Score: {hallucination_score}")