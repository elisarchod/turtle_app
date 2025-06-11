from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.constants import START
from langgraph.graph import MessagesState, StateGraph
from langgraph.graph.state import CompiledStateGraph

from turtleapp.settings import supervisor_model_name
from turtleapp.src.nodes.agents import retriever_node, torrent_node, movie_scanner_node
from turtleapp.src.nodes.supervisor import SupervisorNodeCreator
from turtleapp.src.core.tools.movie_summaries_retriever import retriever_tool
from turtleapp.src.core.tools.torrent_tools import torrent_info_tool
from turtleapp.src.core.tools.movie_scanner import movie_scanner_tool


class MovieWorkflowGraph:
    def __init__(self, supervisor_model_name: str = supervisor_model_name):
        self.supervisor_llm = ChatOpenAI(temperature=0, model=supervisor_model_name)
        
        self.node_functions = {
            retriever_tool.name: retriever_node,
            torrent_info_tool.name: torrent_node,
            movie_scanner_tool.name: movie_scanner_node
        }
    
    def compile(self) -> CompiledStateGraph:
        builder = StateGraph(MessagesState)
        supervisor_node = SupervisorNodeCreator(self.supervisor_llm, members=list(self.node_functions.keys()))
        builder.add_edge(START, "supervisor")
        builder.add_node("supervisor", supervisor_node)
        
        for agent_name, agent_function in self.node_functions.items():
            builder.add_node(agent_name, agent_function)
        
        compiled_graph = builder.compile(checkpointer=MemorySaver())
        compiled_graph.name = "Multi-agent Movie Supervisor"
        return compiled_graph

home_agent: CompiledStateGraph = MovieWorkflowGraph().compile()

if __name__ == '__main__':
    config = {"configurable": {"thread_id": "gen_int_13"}}
    result: AddableValuesDict = home_agent.invoke({"messages": "tell me the plot of terminator 2 ?"}, config=config)
    result['messages'][-1].pretty_print()
