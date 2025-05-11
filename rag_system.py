from langchain.vectorstores import Chroma
from langchain.embeddings import OpenAIEmbeddings
from langchain.chat_models import ChatOpenAI
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
import os
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# OpenAI API 키 설정
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

class CourseRecommender:
    def __init__(self):
        # VectorDB 로드
        self.embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
        self.vectorstore = Chroma(
            persist_directory="./chroma_db",
            embedding_function=self.embeddings
        )
        
        # LLM 설정
        self.llm = ChatOpenAI(
            model_name="gpt-3.5-turbo",
            temperature=0.7,
            openai_api_key=OPENAI_API_KEY
        )
        
        # 대화 메모리 설정
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        
        # RAG 체인 설정
        self.qa_chain = ConversationalRetrievalChain.from_llm(
            llm=self.llm,
            retriever=self.vectorstore.as_retriever(
                search_kwargs={"k": 3}  # 상위 3개 문서 검색
            ),
            memory=self.memory,
            verbose=True
        )
    
    def get_recommendation(self, query):
        """사용자 질문에 대한 강의 추천"""
        try:
            # RAG 체인 실행
            result = self.qa_chain({"question": query})
            
            return {
                "answer": result["answer"],
                "sources": self._format_sources(result.get("source_documents", []))
            }
        except Exception as e:
            print(f"추천 생성 중 오류 발생: {e}")
            return {
                "answer": "죄송합니다. 추천을 생성하는 중에 오류가 발생했습니다.",
                "sources": []
            }
    
    def _format_sources(self, source_documents):
        """검색된 문서 정보 포맷팅"""
        sources = []
        for doc in source_documents:
            metadata = doc.metadata
            sources.append({
                "subject_name": metadata.get("subject_name", ""),
                "subject_code": metadata.get("subject_code", ""),
                "professor": metadata.get("professor", ""),
                "college": metadata.get("college", ""),
                "major": metadata.get("major", ""),
                "course_type": metadata.get("course_type", "")
            })
        return sources

def main():
    # 추천 시스템 초기화
    recommender = CourseRecommender()
    
    # 테스트
    test_queries = [
        "3학년인데 AI 관련 수업 추천해줘",
        "프로젝트 위주의 수업이 있는지 알려줘",
        "컴퓨터공학부 전공 수업 중 실습이 많은 과목 추천해줘"
    ]
    
    for query in test_queries:
        print(f"\n질문: {query}")
        result = recommender.get_recommendation(query)
        print(f"답변: {result['answer']}")
        print("\n추천 강의:")
        for source in result['sources']:
            print(f"- {source['subject_name']} ({source['professor']})")

if __name__ == "__main__":
    main() 