from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import json
import os
from datetime import datetime

# 데이터베이스 설정
DATABASE_URL = "sqlite:///course_recommender.db"
engine = create_engine(DATABASE_URL)
Base = declarative_base()

# 모델 정의
class Course(Base):
    __tablename__ = "course"
    
    id = Column(Integer, primary_key=True)
    subject_code = Column(String(20))  # 과목코드
    subject_name = Column(String(200))  # 교과목명 (항목_18)
    class_number = Column(String(20))  # 분반
    professor = Column(String(100))  # 담당교수 (항목_9)
    college = Column(String(100))  # 단과대학
    major = Column(String(100))  # 학과
    course_type = Column(String(50))  # 이수구분 (항목_5)
    year = Column(String(20))  # 학년
    semester = Column(String(20))  # 학기
    
    syllabus_id = Column(Integer, ForeignKey("syllabus.id"))
    syllabus = relationship("Syllabus", back_populates="course")
    weekly_plans = relationship("WeeklyPlan", back_populates="course")

class Syllabus(Base):
    __tablename__ = "syllabus"
    
    id = Column(Integer, primary_key=True)
    basic_info = Column(Text)  # 기본 정보 (JSON 형식)
    professor_info = Column(Text)  # 교수 정보 (JSON 형식)
    course_info = Column(Text)  # 강의 정보 (JSON 형식)
    evaluation = Column(Text)  # 평가 방법 (JSON 형식)
    textbook_info = Column(Text)  # 교재 정보 (JSON 형식)
    core_competencies = Column(Text)  # 핵심역량 (JSON 형식)
    
    course = relationship("Course", back_populates="syllabus")

class WeeklyPlan(Base):
    __tablename__ = "weekly_plans"
    
    id = Column(Integer, primary_key=True)
    course_id = Column(Integer, ForeignKey("course.id"))
    week_number = Column(Integer)
    topic = Column(String(200))
    content = Column(Text)
    
    # 관계 설정
    course = relationship("Course", back_populates="weekly_plans")

def init_db():
    """데이터베이스 초기화"""
    Base.metadata.create_all(engine)

def process_json_files(json_dir):
    """폴더 내의 모든 JSON 파일을 처리하여 데이터베이스에 저장"""
    try:
        # 데이터베이스 테이블 생성
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        try:
            # JSON 파일 목록 가져오기
            json_files = [f for f in os.listdir(json_dir) if f.endswith('.json')]
            total_files = len(json_files)
            
            print(f"총 {total_files}개의 JSON 파일을 처리합니다...")
            
            for i, json_file in enumerate(json_files, 1):
                file_path = os.path.join(json_dir, json_file)
                print(f"\n[{i}/{total_files}] {json_file} 처리 중...")
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 기본 정보 추출
                basic_info = data.get("기본정보", {})
                evaluation_info = data.get("평가방법", {})
                core_info = data.get("핵심역량", {})
                
                print(f"기본 정보: {basic_info.get('항목_18', '')} (교과목명)")
                print(f"담당교수: {basic_info.get('항목_9', '')}")
                print(f"이수구분: {basic_info.get('항목_5', '')}")
                
                # 담당교수 정보 추출 로직 개선
                def extract_professor_info(info_dict):
                    # 교수 정보가 포함될 수 있는 모든 항목 확인
                    professor_fields = {
                        "항목_9": "담당교수",
                        "항목_10": "담당교수",
                        "항목_4": "이메일",  # 이메일이 교수 정보와 함께 있을 수 있음
                        "항목_6": "연구실",  # 연구실 정보가 교수 정보와 함께 있을 수 있음
                    }
                    
                    # 각 항목에서 교수 정보 추출 시도
                    for field, field_type in professor_fields.items():
                        value = info_dict.get(field, "")
                        if value and "교수" in value or "교수" in field_type:
                            # 교수 정보에서 이름만 추출
                            parts = value.split()
                            for part in parts:
                                if "교수" in part:
                                    # 교수 앞의 이름 추출
                                    idx = part.find("교수")
                                    if idx > 0:
                                        return part[:idx]
                                    return part
                            return value
                    return ""

                professor = extract_professor_info(basic_info)
                
                # 강의 정보 생성
                course = Course(
                    subject_code=basic_info.get("항목_13", ""),  # 교과목 코드
                    subject_name=basic_info.get("항목_18", ""),  # 교과목명
                    class_number=basic_info.get("항목_11", ""),  # 분반
                    professor=professor,  # 개선된 담당교수 정보
                    college=basic_info.get("항목_1", "").split()[0] if basic_info.get("항목_1") else "",  # 단과대학
                    major=basic_info.get("항목_20", "").split()[0] if basic_info.get("항목_20") else "",  # 학과
                    course_type=basic_info.get("항목_5", ""),  # 이수구분
                    year=basic_info.get("항목_20", "").split()[-1] if basic_info.get("항목_20") else "",  # 학년
                    semester=basic_info.get("항목_0", "").split("/")[0] if basic_info.get("항목_0") else ""  # 학기
                )
                
                print(f"생성된 강의 정보: {course.subject_name} ({course.professor})")
                
                # 강의계획서 정보 생성
                syllabus = Syllabus(
                    basic_info=json.dumps({
                        "email": basic_info.get("항목_4", ""),  # 이메일
                        "course_type": basic_info.get("항목_5", ""),  # 이수구분
                        "professor": basic_info.get("항목_9", ""),  # 담당교수
                        "phone": basic_info.get("항목_10", ""),  # 연락처
                        "subject_name": basic_info.get("항목_18", ""),  # 교과목명
                        "major_year": basic_info.get("항목_20", ""),  # 학과/학년
                        "course_objective": basic_info.get("항목_29", "")  # 수업목표
                    }, ensure_ascii=False),
                    professor_info=json.dumps({
                        "email": basic_info.get("항목_4", ""),  # 이메일
                        "phone": basic_info.get("항목_10", ""),  # 연락처
                        "professor": basic_info.get("항목_9", ""),  # 담당교수
                        "office": basic_info.get("항목_6", ""),  # 연구실
                        "consultation_time": basic_info.get("항목_22", "")  # 상담가능시간
                    }, ensure_ascii=False),
                    course_info=json.dumps({
                        "course_objective": basic_info.get("항목_29", ""),  # 수업목표
                        "classroom": basic_info.get("전주", ""),  # 강의실
                        "schedule": basic_info.get("항목_27", "")  # 요일/시간
                    }, ensure_ascii=False),
                    evaluation=json.dumps({
                        "a_ratio": evaluation_info.get("항목_10", ""),  # A 비율 (상대평가Ⅰ(A40%))
                        "evaluation_method": evaluation_info.get("항목_8", ""),  # 평가방법
                        "midterm": core_info.get("항목_59", ""),  # 중간고사 비율
                        "final": core_info.get("항목_60", ""),  # 기말고사 비율
                        "attendance": core_info.get("항목_61", ""),  # 출석 비율
                        "assignment": core_info.get("항목_62", ""),  # 과제 비율
                        "other": core_info.get("항목_66", "")  # 기타 비율
                    }, ensure_ascii=False),
                    textbook_info=json.dumps({
                        "main_textbook": core_info.get("항목_21", ""),  # 주교재
                        "reference": core_info.get("항목_24", "")  # 참고자료
                    }, ensure_ascii=False),
                    core_competencies=json.dumps({
                        "communication": core_info.get("항목_12", ""),  # 소통역량
                        "creativity": core_info.get("항목_13", ""),  # 창의역량
                        "personality": core_info.get("항목_14", ""),  # 인성역량
                        "practical": core_info.get("항목_15", ""),  # 실무역량
                        "challenge": core_info.get("항목_16", "")  # 도전역량
                    }, ensure_ascii=False)
                )
                
                # 관계 설정
                course.syllabus = syllabus
                
                # 데이터베이스에 저장
                session.add(course)
                print(f"강의 정보 저장 완료: {course.subject_name}")
            
            session.commit()
            print("\n모든 데이터 처리 완료")
            
        except Exception as e:
            session.rollback()
            print(f"데이터 처리 중 오류 발생: {str(e)}")
            raise
        finally:
            session.close()
            
    except Exception as e:
        print(f"파일 처리 중 오류 발생: {str(e)}")
        raise

if __name__ == "__main__":
    # JSON 파일이 있는 폴더 경로
    json_dir = "data/syllabi"
    
    # 폴더 존재 여부 확인
    if not os.path.exists(json_dir):
        print(f"오류: {json_dir} 폴더를 찾을 수 없습니다.")
        print("크롤링한 데이터가 저장된 폴더의 경로를 확인해주세요.")
        exit(1)
    
    # 데이터 처리
    process_json_files(json_dir) 