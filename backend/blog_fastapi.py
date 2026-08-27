from sqlalchemy.orm import Session
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from backend.blog_generation import workflow
from database.blog_database import sessionLocal, BLOGTABLE

app = FastAPI(title="Agentic Blog Writer API", description="API for generating blogs using LangGraph and FastAPI", version="1.0.0")

def get_db():
    db = sessionLocal()
    try:
        if db:
            yield db
    finally:
        db.close()
        

def stream_and_save_blog(blog_id: str, topic: str, db: Session):
    outline_text = ""
    blog_text = ""
    web_results_text = ""
    web_links_list = []
    initial_state = {"topic": topic}
    
    for mode, data in workflow.stream(initial_state, stream_mode=["messages", "updates"]):
        if mode == "messages":
            message_chunk, metadata = data
            node = metadata.get("langgraph_node")
            content = message_chunk.content
            
            if content:
                if node == "create_outline":
                    outline_text += content
                elif node == "create_blog":
                    blog_text += content
                    
                yield content
        
        elif mode == "updates":
            for node_name, state_update in data.items():
                if node_name == "web_search":
                    web_results_text = state_update.get("web_results", "")
                    web_links_list = state_update.get("web_links", [])
                elif node_name == "create_blog":
                    blog_text = state_update.get("blog", blog_text)

    try:        
        new_row = BLOGTABLE(
            blog_id = blog_id,
            web_results = str(web_results_text),
            web_links = ", ".join(web_links_list) if web_links_list else "",
            topic = topic,
            outline = outline_text,
            blog = blog_text
        )
        db.add(new_row)
        db.commit()
        db.refresh(new_row)
        print("Data Added in DB")
    except Exception as e:
        db.rollback()
        print(f"Unable to add DB : {e}")
    

@app.get("/")
def home_page():
    return{
        "msg": "api is running",
        "use": "/docs"
    }

@app.post("/write-blog")
def stream_tokens(blog_id: str, topic: str, db: Session = Depends(get_db)):
    return StreamingResponse(
        stream_and_save_blog(blog_id, topic, db),
        media_type="text/plain"
    )


@app.get("/blog-ids")
def blog_ids(db: Session = Depends(get_db)):
    records = db.query(BLOGTABLE.blog_id, BLOGTABLE.topic).order_by(BLOGTABLE.created_at.desc()).all()
    return [{"blog_id": row.blog_id, "topic": row.topic} for row in records]


@app.get("/blog-ids/{blog_id}")
def blog_history_id(blog_id, db: Session = Depends(get_db)):
    query = db.query(BLOGTABLE).filter(BLOGTABLE.blog_id == blog_id).first()
    try:
        if query:
            return{
                "blog_id": query.blog_id,
                "topic": query.topic,
                "web_links": query.web_links,
                "outline": query.outline,
                "blog": query.blog,
                "created_at": query.created_at
            }
    except Exception as e:
        return{
            "msg": "blog id does not exists"
        }
        
@app.delete("/delete-blog/{blog_id}")
def delete_blog(blog_id, db: Session = Depends(get_db)):
    blog_row = db.query(BLOGTABLE).filter(BLOGTABLE.blog_id == blog_id).first()
    try:
        if blog_row:
            db.delete(blog_row)
            db.commit()
            return{"msg": f"blog deleted successfully."}
        else:
            return{
                "msg": f"blog id {blog_id} not found in database!"
            }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to perform this operation."
        )