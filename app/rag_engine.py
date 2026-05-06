import os
import requests
import chromadb
from dotenv import load_dotenv
from pypdf import PdfReader
from typing import List

class RAGEngine:
    def __init__(self):
        # 加载配置（自动找项目根目录的.env）
        load_dotenv(override=True)
        print("✅ 开始初始化RAG引擎...")

        # 1. 读取并校验API Key
        self.api_key = os.getenv("API_KEY")
        if not self.api_key or self.api_key.strip() == "":
            raise ValueError("❌ 致命错误：API_KEY 未配置或为空，请检查.env文件")
        print(f"🔑 API Key加载成功（前5位: {self.api_key[:5]}）")

        # 2. 初始化向量数据库（路径从配置读取）
        self.persist_dir = os.getenv("VECTOR_DB_DIR", "./vector_db")
        os.makedirs(self.persist_dir, exist_ok=True)
        
        self.client = chromadb.PersistentClient(path=self.persist_dir)
        self.collection = self.client.get_or_create_collection(
            name="smart_campus",
            metadata={"description": "智联校园AI助手知识库"}
        )
        print(f"✅ 向量数据库初始化成功（路径：{self.persist_dir}）")

    def _get_embedding(self, text: str) -> List[float] | None:
        """调用硅基流动API生成文本向量（bge-m3模型）"""
        if not text.strip():
            print("❌ 空文本无法生成向量")
            return None
        
        url = f"{os.getenv('BASE_URL', 'https://api.siliconflow.cn/v1')}/embeddings"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "BAAI/bge-m3",
            "input": text,
            "encoding_format": "float"
        }
        
        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            if response.status_code == 200:
                return response.json()['data'][0]['embedding']
            else:
                print(f"❌ 向量生成失败（状态码{response.status_code}）：{response.text}")
                return None
        except Exception as e:
            print(f"❌ 向量生成请求异常：{str(e)}")
            return None

    def _extract_text_from_pdf(self, file_path: str) -> List[str]:
        """从PDF中提取文本，按页分块"""
        try:
            reader = PdfReader(file_path)
            texts = []
            for page_num, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text and page_text.strip():
                    # 简单分块：按段落拆分（可根据需求优化为更小的块）
                    paragraphs = [p.strip() for p in page_text.split('\n\n') if p.strip()]
                    texts.extend(paragraphs)
                    print(f"📄 PDF第{page_num+1}页提取到{len(paragraphs)}个有效段落")
            return texts
        except Exception as e:
            print(f"❌ PDF文本提取失败：{str(e)}")
            return []

    def ingest_pdf(self, file_path: str):
        """处理PDF文档：提取文本 -> 向量化 -> 存储到向量库"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"❌ PDF文件不存在：{file_path}")
        
        print(f"📖 开始处理PDF：{file_path}")
        # 1. 提取PDF文本
        text_chunks = self._extract_text_from_pdf(file_path)
        if not text_chunks:
            raise ValueError("❌ PDF中未提取到有效文本")
        
        # 2. 生成向量并入库
        ids = []
        embeddings = []
        documents = []
        
        for idx, chunk in enumerate(text_chunks):
            embedding = self._get_embedding(chunk)
            if embedding:
                # 生成唯一ID（文件名+索引）
                file_name = os.path.basename(file_path).replace('.pdf', '')
                ids.append(f"{file_name}_chunk_{idx}")
                embeddings.append(embedding)
                documents.append(chunk)
        
        # 3. 批量入库
        if ids:
            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=documents
            )
            print(f"✅ 成功入库{len(ids)}个文本片段（总计{len(text_chunks)}个片段）")
        else:
            raise RuntimeError("❌ 无有效向量生成，入库失败")

    def search(self, query: str, k: int = 3) -> List[str]:
        """检索与查询最相关的k个文档片段"""
        # 生成查询向量
        query_embedding = self._get_embedding(query)
        if not query_embedding:
            print("❌ 查询向量生成失败，返回空结果")
            return []
            
        # 向量检索
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=k,
            include=["documents"]
        )
        
        # 返回去重后的文档列表
        unique_docs = list(dict.fromkeys(results['documents'][0]))  # 去重
        print(f"🔍 检索到{len(unique_docs)}个相关文档片段")
        return unique_docs

if __name__ == "__main__":
    """测试RAG引擎"""
    try:
        engine = RAGEngine()
        # 测试PDF处理（替换为你的测试PDF路径）
        test_pdf = "test.pdf"
        if os.path.exists(test_pdf):
            engine.ingest_pdf(test_pdf)
            # 测试检索
            res = engine.search("食堂有什么规定？", k=5)
            print("📝 检索结果：")
            for i, doc in enumerate(res):
                print(f"{i+1}. {doc[:100]}...")  # 只打印前100字符
        else:
            print(f"⚠️ 测试PDF不存在：{test_pdf}")
    except Exception as e:
        print(f"❌ 引擎测试失败：{str(e)}")