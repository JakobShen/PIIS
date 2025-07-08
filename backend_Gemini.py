import os
from typing import List
from fastapi import FastAPI, Request, Body
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from google import generativeai as genai
from dotenv import load_dotenv
import uvicorn

load_dotenv('api.env')

class RequestBody(BaseModel):
    prompt: str
    appType: str
    features: List[str]
    userCount: str
    notes: List[str]

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure Gemini client
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
gemini_model = genai.GenerativeModel("gemini-2.5-flash")  # or "gemini-1.5-flash"

@app.post("/api/generate")
async def generate(req: RequestBody):
    # Construct the prompt
    full_prompt = (
        f"你是一个帮助用户生成软件系统架构设计方案的助手。请用英文回答。\n"
        f"应用类型: {req.appType}\n"
        f"核心功能: {', '.join(req.features) or '无'}\n"
        f"预期用户量: {req.userCount}\n"
        f"用户输入标签: {chr(10).join(req.notes) or '无'}\n"
        f"项目描述: {req.prompt}"
    )
    
    # Generate content with Gemini
    response = gemini_model.generate_content(full_prompt)
    return {"result": response.text}

@app.post('/generate_diagram')
async def generate_diagram(req: RequestBody):
    """
    基于上一步的架构生成结果，自动生成对应的流程图
    """
    # First generate architecture description
    full_prompt = (
        f"你是一个帮助用户生成软件系统架构设计方案的助手。请用英文回答。\n"
        f"应用类型: {req.appType}\n"
        f"核心功能: {', '.join(req.features) or '无'}\n"
        f"预期用户量: {req.userCount}\n"
        f"项目描述: {req.prompt}"
    )
    
    architecture_response = gemini_model.generate_content(full_prompt)
    architecture_text = architecture_response.text
    
    # Then convert to Mermaid diagram
    diagram_prompt = f"""
    你是一个软件架构专家，请将以下系统架构描述转化为 mermaid.js 的流程图（graph TD 格式），
    只返回代码块，请不要返回```mermaid以及```，不需要任何解释。

    架构描述如下：
    {architecture_text}
    """
    
    try:
        diagram_response = gemini_model.generate_content(diagram_prompt)
        diagram_code = diagram_response.text
        
        # Clean up the response
        if "```mermaid" in diagram_code:
            diagram_code = diagram_code.split("```mermaid")[1].split("```")[0].strip()
        elif "```" in diagram_code:
            diagram_code = diagram_code.split("```")[1].strip()
            
        return {
            "diagram": diagram_code,
            "architecture": architecture_text
        }
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/note_hint")
async def note_hint(data: dict = Body(...)):
    existing_notes = data.get("existingNotes", "")
    title = data.get("title", "New Note")
    content = data.get("content", "")

    full_prompt = (
        f"You are helping a user design a software architecture using sticky notes.\n"
        f"The user has already written the following notes:\n\n"
        f"{existing_notes}\n\n"
        f"Now they added a new note titled: {title}.\n"
    )

    if content:
        full_prompt += (
            f"The note already contains the following text:\n{content}\n"
            f"Please provide a suggestion to continue or complete this note so it complements the others."
        )
    else:
        full_prompt += "Please suggest content for this note that complements the existing ones."

    response = gemini_model.generate_content(full_prompt)
    return {"suggestion": response.text.strip()}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
