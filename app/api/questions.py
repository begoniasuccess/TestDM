from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Annotated

import app.models
from app.database import SessionLocal, Base, engine
from sqlalchemy.orm import Session

questionRouter = APIRouter()

# 在資料庫中建立剛剛app.models中設定好的資料結構
app.models.Base.metadata.create_all(bind=engine)

# Pydantic 模型定義
class ChoiceBase(BaseModel):
    choice_text:str
    is_correct:bool

class QuestionBase(BaseModel):
    question_text:str
    choices:List[ChoiceBase]

# 獲取資料庫會話
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 一個db的dependency，可以看做是要操作的db，這裡的Depends對應get_db，get_db對應SessionLocal    
db_dependency = Annotated[Session, Depends(get_db)]

# CREATE
@questionRouter.post("/api/questions")
async def create_questions(question: QuestionBase, db:db_dependency):
    db_question = app.models.Question(question_text=question.question_text)
    db.add(db_question)
    db.commit()
    db.refresh(db_question)
    for choice in question.choices:
        db_choice = app.models.Choices(choice_text=choice.choice_text, is_correct=choice.is_correct, question_id=db_question.id)
        db.add(db_choice)
    db.commit()


# READ
@questionRouter.get('/api/questions/{question_id}')
async def read_question(question_id:int, db:db_dependency):
    result = db.query(app.models.Question).filter(app.models.Question.id == question_id).first()
    if not result:
        raise HTTPException(status_code=404, detail='Question is not found.')
    data = {"id": result.id, "question_text": result.question_text} 
    return JSONResponse(content={"message": "success", "data": data})
    

# READ Mulitple items
@questionRouter.get('/choices/{question_id}')
async def read_choices(question_id:int, db:db_dependency):
    result = db.query(app.models.Choices).filter(app.models.Choices.question_id == question_id).all()
    if not result:
        raise HTTPException(status_code=404, detail='Choice is not found.')    
    data_list = [{"id": item.id, "choice_text": item.choice_text, "is_correct": item.is_correct, "question_id": item.question_id} for item in result]
    return JSONResponse(content={"message": "success", "data": data_list})