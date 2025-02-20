from dotenv import load_dotenv
from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Dict
from langgraph.checkpoint.sqlite import SqliteSaver
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from tavily import TavilyClient
import os
import logging

# Load environment variables
_ = load_dotenv()

# Initialize memory and model
memory = SqliteSaver.from_conn_string(":memory:")
model = ChatOpenAI(model="gpt-4o-mini", temperature=0)
tavily = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])

MAX_TOKENS = 120_000

class AgentDB(BaseModel):
    id: str = Field(alias="_id")
    name: str
    files: List[Dict] = []
    websites: List[Dict] = []
    messages: List[Dict] = []

class AgentState(TypedDict):
    """State definition for the agent's workflow."""
    task: str
    plan: str
    draft: str
    critique: str
    content: List[str]
    revision_number: int
    max_revisions: int
    has_agent_content: bool

class Queries(BaseModel):
    queries: List[str]

# Updated PROMPTS to handle primary sources
PROMPTS = {
    "PLAN": """You are an expert writer tasked with writing a high level outline of an essay. \
Write such an outline for the user provided topic. Give an outline of the essay along with any relevant notes \
or instructions for the sections.""",

    "WRITE": """You are an essay assistant tasked with writing excellent 5-paragraph essays. \
Generate the best essay possible for the user's request and the initial outline. \
If the user provides critique, respond with a revised version of your previous attempts. \
Pay special attention to any content marked as [VERIFIED SOURCE] as these are primary sources that should be prioritized. \
Utilize all the information below as needed: 

------

{content}""",

    "REFLECT": """You are a teacher grading an essay submission. \
Generate critique and recommendations for the user's submission. \
Provide detailed recommendations, including requests for length, depth, style, etc.""",

    "RESEARCH_PLAN": """You are a researcher charged with providing information that can \
be used when writing the following essay. Generate a list of search queries that will gather \
any relevant information. Only generate 3 queries max.""",

    "RESEARCH_CRITIQUE": """You are a researcher charged with providing information that can \
be used when making any requested revisions (as outlined below). \
Generate a list of search queries that will gather any relevant information. Only generate 3 queries max."""
}

def plan_node(state: AgentState):
    messages = [
        SystemMessage(content=PROMPTS["PLAN"]), 
        HumanMessage(content=state['task'])
    ]
    response = model.invoke(messages)
    return {"plan": response.content}

def read_agent_content_node(state: AgentState, agent_db: AgentDB):
    """Read content from agent's files and websites, marking them as verified sources"""
    content = []
    total_tokens = 0
    
    # Process files first (as they're likely primary sources)
    if agent_db and agent_db["files"]:
        for file in agent_db["files"]:
            if file.get("content"):
                if isinstance(file["content"], dict):
                    file_content = file["content"]["content"]
                    new_tokens = file["content"].get("token_count", 0)
                    # Skip this file if it would exceed token limit
                    if total_tokens + new_tokens <= MAX_TOKENS:
                        total_tokens += new_tokens
                        content.append(f"[VERIFIED SOURCE - File '{file.get('name', 'unnamed')}'] {file_content}")
                    else:
                        logging.warning(f"Skipping file {file.get('name', 'unnamed')} to stay within token limit")
                else:
                    content.append(f"[VERIFIED SOURCE - File '{file.get('name', 'unnamed')}'] {file['content']}")
    
    # Process websites with remaining token budget
    if agent_db and agent_db["websites"]:
        for website in agent_db["websites"]:
            if website.get("content"):
                if isinstance(website["content"], dict):
                    web_content = website["content"]["content"]
                    new_tokens = website["content"].get("token_count", 0)
                    # Skip this website if it would exceed token limit
                    if total_tokens + new_tokens <= MAX_TOKENS:
                        total_tokens += new_tokens
                        content.append(f"[VERIFIED SOURCE - Website '{website.get('url', 'unknown')}'] {web_content}")
                    else:
                        logging.warning(f"Skipping website {website.get('url', 'unknown')} to stay within token limit")
                else:
                    content.append(f"[VERIFIED SOURCE - Website '{website.get('url', 'unknown')}'] {website['content']}")
    
    return {
        "content": content,
        "has_agent_content": bool(content),
        "total_source_tokens": total_tokens
    }

def research_plan_node(state: AgentState):
    """Generate additional research only if needed"""
    content = state.get("content", [])
    
    # If we already have agent content, be more selective about additional research
    if state.get("has_agent_content"):
        queries = model.with_structured_output(Queries).invoke([
            SystemMessage(content="Using the verified sources as primary information, identify only critical gaps that need additional research. Generate maximum 2 queries."),
            HumanMessage(content=state['task'])
        ])
        # Limit additional research when we have primary sources
        max_results = 1
    else:
        queries = model.with_structured_output(Queries).invoke([
            SystemMessage(content=PROMPTS["RESEARCH_PLAN"]),
            HumanMessage(content=state['task'])
        ])
        max_results = 2

    for q in queries.queries:
        response = tavily.search(query=q, max_results=max_results)
        for r in response['results']:
            content.append(f"[Supplementary Source] {r['content']}")
    
    return {"content": content}

def generation_node(state: AgentState):
    content = "\n\n".join(state['content'] or [])
    user_message = HumanMessage(
        content=f"{state['task']}\n\nHere is my plan:\n\n{state['plan']}")
    messages = [
        SystemMessage(
            content=PROMPTS["WRITE"].format(content=content)
        ),
        user_message
    ]
    response = model.invoke(messages)
    return {
        "draft": response.content, 
        "revision_number": state.get("revision_number", 1) + 1
    }

def reflection_node(state: AgentState):
    messages = [
        SystemMessage(content=PROMPTS["REFLECT"]), 
        HumanMessage(content=state['draft'])
    ]
    response = model.invoke(messages)
    return {"critique": response.content}

def research_critique_node(state: AgentState):
    """Modified to respect primary sources when gathering additional information"""
    queries = model.with_structured_output(Queries).invoke([
        SystemMessage(content=PROMPTS["RESEARCH_CRITIQUE"]),
        HumanMessage(content=state['critique'])
    ])
    content = state['content'] or []
    
    # Limit additional research if we have primary sources
    max_results = 1 if state.get("has_agent_content") else 2
    
    for q in queries.queries:
        response = tavily.search(query=q, max_results=max_results)
        for r in response['results']:
            content.append(f"[Supplementary Source] {r['content']}")
    return {"content": content}

def should_continue(state):
    if state["revision_number"] > state["max_revisions"]:
        return END
    return "reflect"

def generate_graph(agent_db: AgentDB):
    builder = StateGraph(AgentState)
    builder.add_node("planner", plan_node)
    builder.add_node("research_plan", research_plan_node)
    builder.add_node("generate", generation_node)
    builder.add_node("reflect", reflection_node)
    builder.add_node("research_critique", research_critique_node)
    print(agent_db)
    if agent_db and (agent_db["files"] or agent_db["websites"]):
        builder.add_node("read_agent_content", lambda state: read_agent_content_node(state, agent_db))
        builder.set_entry_point("planner")
        builder.add_edge("planner", "read_agent_content")
        builder.add_edge("read_agent_content", "research_plan")
    else:
        builder.set_entry_point("planner")
        builder.add_edge("planner", "research_plan")
    
    builder.add_edge("research_plan", "generate")
    builder.add_conditional_edges(
        "generate", 
        should_continue, 
        {END: END, "reflect": "reflect"}
    )
    builder.add_edge("reflect", "research_critique")
    builder.add_edge("research_critique", "generate")
    
    return builder.compile()

def begin_research(task: str, max_revisions: int = 2, agent_db: AgentDB = None):
    graph = generate_graph(agent_db)
    thread = {"configurable": {"thread_id": "1"}}
    final_state = None
    
    initial_state = {
        'task': task,
        "max_revisions": max_revisions,
        "revision_number": 1,
        "has_agent_content": False
    }
    
    for state in graph.stream(initial_state, thread):
        final_state = state
        print(f"Current state: {state}")
    
    if final_state:
        return final_state['generate']['draft']
    return "No draft was generated."
