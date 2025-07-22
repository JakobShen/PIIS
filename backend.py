import os
from typing import List
from fastapi import FastAPI, Request,Body
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from openai import AsyncOpenAI
from dotenv import load_dotenv
import uvicorn

load_dotenv('api.env')

class RequestBody(BaseModel):
    prompt: str
    appType: str
    features: List[str]
    userCount: str
    notes: List[str]

class MCQRequest(RequestBody):
    category: str

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

client = AsyncOpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url="https://dseek.aikeji.vip/v1"
)

@app.post("/api/generate")
async def generate(req: RequestBody):
    # Build the prompt in English
    full_prompt = (
        f"Application type: {req.appType}\n"
        f"Core features: {', '.join(req.features) or 'None'}\n"
        f"Expected user count: {req.userCount}\n"
        f"User input notes: {chr(10).join(req.notes) or 'None'}\n"
        f"Project description: {req.prompt}"
    )
    response = await client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {
                "role": "system",
                "content": "You are an assistant that helps users design software system architectures. Answer in English.",
            },
            {"role": "user",    "content": full_prompt}
        ]
    )
    return {"result": response.choices[0].message.content}

# 启动： uvicorn backend:app --reload --host 0.0.0.0 --port 8000

# 生成diagram部分 - 修改为使用上一步的架构生成结果
class DiagramRequest(BaseModel):
    # 不再需要用户手动输入架构描述，而是使用上一步生成的结果
    pass

@app.post('/generate_diagram')
async def generate_diagram(req: RequestBody):
    """Auto-generate a diagram based on the previously generated architecture."""
    # Use the same logic as the generate function
    full_prompt = (
        f"Application type: {req.appType}\n"
        f"Core features: {', '.join(req.features) or 'None'}\n"
        f"Expected user count: {req.userCount}\n"
        f"Project description: {req.prompt}"
    )
    
    # 首先生成架构描述
    architecture_response = await client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {
                "role": "system",
                "content": "You are an assistant that helps users design software system architectures. Answer in English.",
            },
            {"role": "user",    "content": full_prompt}
        ]
    )
    
    architecture_text = architecture_response.choices[0].message.content
    
    # Then convert the architecture description to a Mermaid diagram
    diagram_prompt = f"""
You are a software architecture expert. Convert the following architecture description into a mermaid.js flowchart (graph TD format). Return only the code block without ```mermaid``` or ``` and provide no explanation.

Architecture description:
{architecture_text}
    """
    
    try:
        diagram_response = await client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": diagram_prompt}],
            temperature=0.5
        )
        diagram_code = diagram_response.choices[0].message.content
        
        # 确保 diagram_code 是一个字符串再进行处理
        if diagram_code:
            # 提取Mermaid代码块，去除可能存在的markdown标记
            if "```mermaid" in diagram_code:
                # 提取被 ```mermaid 和 ``` 包裹的内容
                start = diagram_code.find("```mermaid") + len("```mermaid")
                end = diagram_code.rfind("```")
                if start < end:
                    diagram_code = diagram_code[start:end].strip()
            elif "```" in diagram_code:
                # 提取被 ``` 和 ``` 包裹的内容
                start = diagram_code.find("```") + len("```")
                end = diagram_code.rfind("```")
                if start < end:
                    diagram_code = diagram_code[start:end].strip()

        return {
            "diagram": diagram_code,
            "architecture": architecture_text  # 同时返回架构描述，方便前端显示
        }
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/generate_mcq")
async def generate_mcq(req: MCQRequest):
    prompt = (
        f"Application type: {req.appType}\n"
        f"Core features: {', '.join(req.features) or 'None'}\n"
        f"Expected user count: {req.userCount}\n"
        f"User input notes: {chr(10).join(req.notes) or 'None'}\n"
        f"Project description: {req.prompt}\n"
        f"Question category: {req.category}"
    )
    user_msg = (
        "Based on the above information, ask a multiple-choice question that clarifies unspecified or missing project requirements."
        "Focus on aspects that are underdescribed or might have been overlooked."
        "Provide a short question with exactly four options labeled A, B, C and D, and include no extra text."
    )
    response = await client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "You are an experienced software consultant skilled at asking key questions."},
            {"role": "user", "content": prompt + "\n" + user_msg}
        ]
    )
    return {"mcq": response.choices[0].message.content.strip()}

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

    response = await client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "You are an expert software architect assistant."},
            {"role": "user", "content": full_prompt}
        ]
    )

    return {"suggestion": response.choices[0].message.content.strip()}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

    uvicorn.run(app, host="0.0.0.0", port=8000)