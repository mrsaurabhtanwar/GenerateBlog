from langgraph.graph import StateGraph, START, END
from langchain_groq import ChatGroq
from typing import TypedDict, Literal
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from langchain_community.tools import DuckDuckGoSearchResults

load_dotenv()

llm = ChatGroq(
    model="openai/gpt-oss-120b",
    temperature=0.7
)


class BlogState(TypedDict):
    topic: str
    web_results: str
    web_links: list[str]
    outline: str
    blog: str
    review_feedback : str
    review_status: Literal["pass", "revise"]
    review_count: int
    
    
class ReviewLLMOutPut(BaseModel):
   
    review_feedback: str
    review_status: Literal["pass", "revise"]
    
review_llm = llm.with_structured_output(ReviewLLMOutPut, method="json_mode")
    
search_tools = DuckDuckGoSearchResults(num_results=4, output_format="list")
    
def web_search(state: BlogState):
    topic = state["topic"]
    
    links_list = []
    
    print(f"Doing web search for {topic}...")
    try:
        web_results = search_tools.invoke(f"{topic} latest facts news analysis")
        
        if isinstance(web_results, list):
            for item in web_results:
                link = item.get("link")
                links_list.append(link)  
    except Exception:
        web_results = "No live results available"
        
    return{
        "web_results": web_results,
        "web_links": links_list
    }


def create_outline(state: BlogState):
    topic = state["topic"]
    web_search = state["web_results"]
    
    prompt = f"""You are an expert research writer.
    Topic: {topic}
    
    Live Web Research & Facts:
    {web_search}
    
    Create a structured, short, and fact-grounded outline for a blog based on the topic and research above."""
       
    outline = llm.invoke(prompt).content
    return{
        "outline" : outline
    }
    

def create_blog(state: BlogState):
    topic = state["topic"]
    web_search = state["web_results"]
    outline = state["outline"]
    review_feedback = state.get("review_feedback", "")
    review_count = state.get("review_count", 0)
    
    if review_feedback and review_count > 0:
        prompt = f"""You are an expert analytical blogger revising your draft.
        Topic: {topic}
        Outline: {outline}
        Live Facts: {web_search}
        Editorial Critic Feedback to Fix:
        {review_feedback}
        Draft:
        {state.get('blog')}
        Rewrite and improve the blog post strictly addressing all the critic's feedback."""        
    else:
        prompt = f"""You are an expert analytical blogger.
        Topic: {topic}
        
        Research Context:
        {web_search}
        
        Outline:
        {outline}
        Write a detailed, high-quality blog post strictly following the outline and citing the facts where appropriate."""
        
    blog = llm.invoke(prompt).content
    return{
        "blog": blog
    }
    
    
def review_blog(state: BlogState):
    topic = state["topic"]
    outline = state["outline"]
    blog = state["blog"]
    review_count = state.get("review_count", 0)
    
    prompt = f"""You are a strict editorial critic.
    
    Topic: {topic}
    
    Outline:
    {outline}
    
    Draft Blog:
    {blog}
    
    Evaluate the blog based on:
    1. Did it cover all sections in the outline?
    2. Is the tone analytical and engaging?
    3. Is it well-structured with proper formatting?
    
    
    Respond in JSON with 'review_status' ('pass' or 'revise') and 'review_feedback'.
    """
    
    response: ReviewLLMOutPut = review_llm.invoke(prompt)
    
    return{
        "review_feedback" : response.review_feedback,
        "review_status" : response.review_status,
        "review_count" : review_count + 1
    }


def blog_decision(state: BlogState):
    if state.get("review_status") == "pass" or state.get("review_count", 0) >= 3:
        return END
    return "create_blog"

graph = StateGraph(BlogState)

graph.add_node("web_search", web_search)
graph.add_node("create_outline", create_outline)
graph.add_node("review_blog", review_blog)
graph.add_node("create_blog", create_blog)

graph.add_edge(START, "web_search")
graph.add_edge("web_search", "create_outline")
graph.add_edge("create_outline", "create_blog")
graph.add_edge("create_blog", "review_blog")
graph.add_conditional_edges("review_blog", blog_decision, {"create_blog": "create_blog", END: END})

workflow = graph.compile()


if __name__ == "__main__":
    # try:
    #     bytes_png = workflow.get_graph().draw_mermaid_png()
    #     with open("backend/blog_graph.png", "wb") as f:
    #         f.write(bytes_png)
    #     print("Graph saved")
    # except Exception as e:
    #     print(f"Not able to generate graph {e}")
        
    initial_state = {"topic": "Recent developments in ISRO space missions 2026"}
    
    outline_text = ""
    blog_text = ""
    current_node = None
    
    for message_chunk, metadata in workflow.stream(initial_state, stream_mode="messages"):
        node = metadata.get("langgraph_node")
        content = message_chunk.content
        
        if node != current_node:
            current_node = node
            print(f"\n\n--- 🚀 Running Node: [{node}] ---")
            
        if content:
            if node == "create_outline":
                outline_text += content
                print(content, end="", flush=True)
            elif node == "create_blog":
                blog_text += content
                print(content, end="", flush=True)