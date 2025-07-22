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
    # 将选择题结果拼进 prompt
    full_prompt = (
        f"应用类型: {req.appType}\n"
        f"核心功能: {', '.join(req.features) or '无'}\n"
        f"预期用户量: {req.userCount}\n"
        f"用户输入标签: {chr(10).join(req.notes) or '无'}\n"
        f"项目描述: {req.prompt}"
    )
    response = await client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system",  "content": "你是一个帮助用户生成软件系统架构设计方案的助手。请用英文回答。"},
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
    """
    基于上一步的架构生成结果，自动生成对应的流程图
    使用与 /api/generate 相同的输入参数，但返回Mermaid图表
    """
    # 使用与generate函数相同的逻辑生成架构描述
    full_prompt = (
        f"应用类型: {req.appType}\n"
        f"核心功能: {', '.join(req.features) or '无'}\n"
        f"预期用户量: {req.userCount}\n"
        f"项目描述: {req.prompt}"
    )
    
    # 首先生成架构描述
    architecture_response = await client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system",  "content": "你是一个帮助用户生成软件系统架构设计方案的助手。请用英文回答。"},
            {"role": "user",    "content": full_prompt}
        ]
    )
    
    architecture_text = architecture_response.choices[0].message.content
    
    # 然后将架构描述转换为Mermaid图表
    diagram_prompt = f"""
    你是一个软件架构专家，请将以下系统架构描述转化为 mermaid.js 的流程图（graph TD 格式），只返回代码块，请不要返回```mermaid以及```，不需要任何解释。

    架构描述如下：
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
        f"应用类型: {req.appType}\n"
        f"核心功能: {', '.join(req.features) or '无'}\n"
        f"预期用户量: {req.userCount}\n"
        f"用户输入标签: {chr(10).join(req.notes) or '无'}\n"
        f"项目描述: {req.prompt}\n"
        f"问题分类: {req.category}"
    )
    user_msg = (
        "基于以上信息，生成一个四选一的选择题。"
        "请提供简短的问题以及A、B、C、D四个答案，不要附加任何额外内容。"
    )
    response = await client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "你是经验丰富的软件顾问，擅长提出关键问题。"},
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

if __name__ == "__main__":    uvicorn.run(app, host="0.0.0.0", port=8000)