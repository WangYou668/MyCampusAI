from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .rag_engine import RAGEngine
import os
import shutil
import requests

app = FastAPI(title="智联校园AI助手")

# 允许跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化RAG引擎
rag_engine = RAGEngine()

# 读取 API Key
API_KEY = os.getenv("API_KEY")
if not API_KEY:
    print("⚠️ 警告：未检测到 API_KEY，问答功能可能无法使用。")

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """上传PDF文档接口"""
    file_path = f"./data/{file.filename}"
    os.makedirs("./data", exist_ok=True)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        rag_engine.ingest_pdf(file_path)
        return {"message": "上传并处理成功", "filename": file.filename}
    except Exception as e:
        return {"error": str(e)}

@app.post("/chat")
async def chat(query: str = Form(...)):
    """问答接口：检索 + 大模型总结"""
    try:
        # 1. 检索相关文档
        # 【关键修改 1】这里强制指定 k=5，比默认的 3 多找两个片段，防止漏掉关键信息
        docs = rag_engine.search(query, k=5)
        
        if not docs:
            return {"answer": "抱歉，我在知识库中没有找到相关信息。"}

        # 2. 拼接上下文
        # 使用清晰的分隔符，帮助模型区分不同的片段
        context = "\n\n---\n\n".join(docs)

        # 3. 调用大模型进行总结和回答
        final_answer = _call_llm_with_rag(query, context)
        
        return {
            "query": query,
            "answer": final_answer,
            "context_used": context
        }
        
    except Exception as e:
        print(f"❌ 问答出错: {e}")
        raise HTTPException(status_code=500, detail="服务器内部错误")

def _call_llm_with_rag(question: str, context: str) -> str:
    """
    调用大模型API，使用RAG模式生成回答
    【关键修改 2】优化了 Prompt 结构，让模型更聪明地处理资料
    """
    if not API_KEY:
        return "系统未配置API Key，无法生成回答。"

    url = "https://api.siliconflow.cn/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    # --- System Prompt: 设定人设和规则 ---
    system_message = (
       "你是一个校园助手。你必须根据下方的【参考资料】回答【问题】。\n"
        "严格限制：\n"
        "1. 只要【参考资料】里有相关的词，你就必须根据它编造（划掉）组织一个答案。\n"
        "2. 禁止回答“资料中未提及”，除非参考资料真的是空的。\n"
        "3. 即使资料很零碎，你也要把它们拼凑起来回答。"
    )
    
    # --- User Prompt: 投喂数据 ---
    # 使用 XML 风格的标签包裹资料，帮助模型理解边界
    user_message = (
        f"请分析以下参考资料：\n"
        f"<参考资料>\n{context}\n</参考资料>\n\n"
        f"用户的问题是：{question}\n\n"
        f"请回答："
    )
    
    data = {
        "model": "Qwen/Qwen2.5-7B-Instruct",
        "messages": [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message}
        ],
        "temperature": 0.5, # 稍微降低温度，让回答更严谨
        "max_tokens": 512
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=15)
        response.raise_for_status()
        
        result = response.json()
        return result['choices'][0]['message']['content']
        
    except requests.exceptions.RequestException as e:
        return f"调用AI服务时发生网络错误: {str(e)}"
    except KeyError:
        return "AI服务返回了意外的数据格式。"

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)