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

class MCQRequest(RequestBody):
    category: str

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
        f"You are an assistant that helps users design software system architectures. Answer in English.\n"
        f"Application type: {req.appType}\n"
        f"Core features: {', '.join(req.features) or 'None'}\n"
        f"Expected user count: {req.userCount}\n"
        f"User input notes: {chr(10).join(req.notes) or 'None'}\n"
        f"Project description: {req.prompt}"
    )
    
    # Generate content with Gemini
    response = gemini_model.generate_content(full_prompt)
    return {"result": response.text}

@app.post('/generate_diagram')
async def generate_diagram(req: RequestBody):
    """
    Automatically generate a diagram based on the previously generated architecture.
    """
    # First generate architecture description
    full_prompt = (
        f"You are an assistant that helps users design software system architectures. Answer in English.\n"
        f"Application type: {req.appType}\n"
        f"Core features: {', '.join(req.features) or 'None'}\n"
        f"Expected user count: {req.userCount}\n"
        f"Project description: {req.prompt}"
    )
    
    architecture_response = gemini_model.generate_content(full_prompt)
    architecture_text = architecture_response.text
    
    # Then convert to Mermaid diagram
    diagram_prompt = f"""
    You are a software architecture expert. Convert the following architecture description into a mermaid.js flowchart (graph TD format).
    Return only the code block without ```mermaid``` or ``` and provide no explanation. The arrows in the diagram should be reasonably clear.
    The code must render correctly in the Mermaid Live Editor. Put words in brackets in quotes, e.g., ["Mobile"], not [Mobile]
    Example:
    graph TD
        A["Mobile App (iOS Android)"] --> B["API Gateway (Load Balancer)"]
        B --> C["Matchmaking Service"]
        B --> D["Game Server (WebSockets)"]
        D --> E["Redis (PubSub, Cache)"]
        D --> F["PostgreSQL (Persistent Data)"]
        C --> D
        C --> G["User Service (ProfilesAuth)"]
        G --> F
        G --> E

    Architecture description:
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

@app.post("/api/generate_mcq")
async def generate_mcq(req: MCQRequest):
    base_prompt = (
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
        "Please provide only the question and four options A, B, C and D."
    )
    response = gemini_model.generate_content(base_prompt + "\n" + user_msg)
    return {"mcq": response.text.strip()}

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
