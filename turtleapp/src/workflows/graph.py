from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.constants import START
from langgraph.graph import MessagesState, StateGraph
from langgraph.graph.state import CompiledStateGraph

from turtleapp.settings import settings
from turtleapp.src.nodes import ToolAgent, SupervisorNodeCreator
from turtleapp.src.core.tools import movie_retriever_tool, torrent_info_tool, library_manager_tool
from turtleapp.src.utils import logger


class MovieWorkflowGraph:
    def __init__(self, supervisor_model_name: str = settings.openai.embedding_model):
        self.supervisor_llm = ChatOpenAI(temperature=0, model=supervisor_model_name)
        self.nodes = {
            movie_retriever_tool.name: ToolAgent(movie_retriever_tool),
            torrent_info_tool.name: ToolAgent(torrent_info_tool),
            library_manager_tool.name: ToolAgent(library_manager_tool)
        }
    
    def compile(self) -> CompiledStateGraph:
        builder = StateGraph(MessagesState)
        supervisor_node = SupervisorNodeCreator(self.supervisor_llm, members=list(self.nodes.keys()))
        builder.add_edge(START, "supervisor")
        builder.add_node("supervisor", supervisor_node)
        
        for agent_name, agent in self.nodes.items():
            builder.add_node(agent_name, agent.process)
        
        compiled_graph = builder.compile(checkpointer=MemorySaver())
        compiled_graph.name = "Multi-agent Movie Supervisor"
        return compiled_graph

movie_workflow_agent: CompiledStateGraph = MovieWorkflowGraph().compile()

if __name__ == '__main__':
    config = {"configurable": {"thread_id": "gen_int_13"}}
    result = movie_workflow_agent.invoke({"messages": "tell me the plot of terminator 2 ?"}, config=config)
    logger.info(f"Workflow result: {result['messages'][-1].content}")
