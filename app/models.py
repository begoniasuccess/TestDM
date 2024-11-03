# 從SQLAlchemy引入相應的參數，來設定models
from sqlalchemy import Column, String, Boolean, Integer, ForeignKey

# 從database.py引入剛剛設定好的Base，並用它來建立要存入資料庫的資料形態
from app.database import Base

from enum import Enum

# 建立class並繼承Base，設定存入的tablename，並設定PK，還有各個column存入的資料形態
class Question(Base):
    __tablename__= 'questions'

    id = Column(Integer, primary_key=True, index=True)
    question_text = Column(String)

class Choices(Base):
    __tablename__= 'choices'

    id = Column(Integer, primary_key=True, index=True)
    choice_text = Column(String, index=True)
    is_correct = Column(Boolean, default=False)
    question_id = Column(Integer, ForeignKey("questions.id"))

class Files(Base):
    __tablename__= 'files'

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    fileName = Column(String, index=True)
    uploadedAt = Column(Integer)
    fileType = Column(Integer, default=1)
    status = Column(Integer)
    parsedPath = Column(String, index=True)

####
class FileType(Enum):
    PDF = 1

class Status(Enum):
    Uploading = 1
    Parsing = 2
    Completed = 3
    Failed = 9