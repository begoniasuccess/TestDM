from fastapi import APIRouter, status, HTTPException, Depends, FastAPI, File, UploadFile, WebSocket, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from datetime import datetime
from typing import List, Annotated, Optional
import time
import shutil
import os
import uuid

import app.models
from app.database import SessionLocal, Base, engine
from sqlalchemy import delete
from sqlalchemy.orm import Session

from marker.convert import convert_single_pdf
from marker.models import load_all_models

fileRouter = APIRouter()

# 在資料庫中建立剛剛models中設定好的資料結構
app.models.Base.metadata.create_all(bind=engine)

# Pydantic 模型定義
class FileBase(BaseModel):
    # id:int
    fileName:str
    uploadedAt: Optional[int]=None
    fileType:int
    status:Optional[int]=None
    parsedPath:Optional[str] = None

# 獲取資料庫會話
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]

# CREATE
@fileRouter.post("/api/files")
def create_files(file: FileBase, db:db_dependency):
    # 防止重複的fileName出現
    result = db.query(app.models.Files).filter(app.models.Files.fileName == file.fileName).first()
    if result:
        raise HTTPException(status_code=404, detail='This file name already exists!')

    new_file = app.models.Files(
        fileName=file.fileName,
        uploadedAt=int(time.time()),
        fileType=file.fileType,
        status=app.models.Status.Uploading.value
    )
    db.add(new_file)
    db.commit()
    db.refresh(new_file)
    return JSONResponse(
        content={"message": "success", "data": new_file.id},
        status_code=status.HTTP_201_CREATED
    )

# READ
@fileRouter.get('/api/files/{id}')
def read_question(id:int, db:db_dependency):
    result = db.query(app.models.Files).filter(app.models.Files.id == id).first()
    if not result:
        raise HTTPException(status_code=404, detail='File not found.')
    data = {"id": result.id, "fileName": result.fileName, "uploadedAt": result.uploadedAt, "fileType": result.fileType, "status": result.status, "parsedPath": result.parsedPath} 
    return JSONResponse(content={"message": "success", "data": data})

# READ All
@fileRouter.get('/api/files')
def read_question(db:db_dependency):
    result = db.query(app.models.Files).all()
    if not result:
        return JSONResponse(content={"message": "success", "data": []})
    data_list = [{"id": item.id, "fileName": item.fileName, "uploadedAt": item.uploadedAt, "fileType": item.fileType, "status": item.status, "parsedPath": item.parsedPath} for item in result]
    return JSONResponse(content={"message": "success", "data": data_list})

# DELETE
@fileRouter.delete('/api/files/{id}', status_code=status.HTTP_204_NO_CONTENT)
def delete_file(id: int, db: db_dependency):
    file_to_delete = db.query(app.models.Files).filter(app.models.Files.id == id).first()
    
    if not file_to_delete:
        raise HTTPException(status_code=404, detail='File not found.')
    
    db.delete(file_to_delete)
    db.commit()  

    # 刪除檔案
    file_name, file_extension = os.path.splitext(os.path.basename(file_to_delete.fileName))
    if os.path.exists(UPLOAD_DIRECTORY):        
        file_path = os.path.join(UPLOAD_DIRECTORY, file_name + ".pdf")   
        try:
            if os.path.isfile(file_path):
                os.remove(file_path)
        except Exception as e:
            print(f"刪除 {file_path} 時發生錯誤: {e}")

    if os.path.exists(PARSED_DIRECTORY):
        file_path2 = os.path.join(PARSED_DIRECTORY, file_name + ".txt")   
        try:
            if os.path.isfile(file_path2):
                os.remove(file_path2)
        except Exception as e:
            print(f"刪除 {file_path2} 時發生錯誤: {e}")

    return JSONResponse(content={"message": "success", "data": {}})  # 返回成功消息，数据为空


UPLOAD_DIRECTORY = "./uploads"
PARSED_DIRECTORY = "./static/parsed"

# Upload
@fileRouter.post("/api/upload/{id}")
def upload_file(id: int, db:db_dependency, file: UploadFile = File(...)):
    result = db.query(app.models.Files).filter(app.models.Files.id == id).first()
    if not result:
        raise HTTPException(status_code=404, detail='File not found.')
    
    if not file:
        raise HTTPException(status_code=404, detail='Please select a file.')
    
    try:
        # 修改紀錄
        result.status = app.models.Status.Parsing.value
        db.commit()
        db.refresh(result)

        # 上傳檔案
        os.makedirs(UPLOAD_DIRECTORY, exist_ok=True)

        file_location = os.path.join(UPLOAD_DIRECTORY, file.filename)
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)  # 保存文件

        return JSONResponse(content={"message": "success", "filename": file.filename}, status_code=201)
    except Exception as e:
        db.delete(result)
        db.commit()  
        raise HTTPException(status_code=500, detail=str(e))
    
# Parse
@fileRouter.post("/api/parse/{id}")
def parse_file(id: int, db:db_dependency):
    result = db.query(app.models.Files).filter(app.models.Files.id == id).first()
    if not result:
        raise HTTPException(status_code=404, detail='File not found.')
    
    file_path = UPLOAD_DIRECTORY + "/" + result.fileName
    if not (os.path.exists(file_path) and os.path.isfile(file_path)):
        db.delete(result)
        db.commit()
        raise HTTPException(status_code=404, detail="File does not exist.")
    
    # 開始進行轉換
    os.makedirs(PARSED_DIRECTORY, exist_ok=True)
    file_name, file_extension = os.path.splitext(os.path.basename(file_path))
    try:
        model_lst = load_all_models()
        full_text, images, out_meta = convert_single_pdf(file_path, model_lst)

        # 保存文本内容
        text_path = os.path.join(PARSED_DIRECTORY, file_name + ".txt")
        with open(text_path, "w", encoding="utf-8") as text_file:
            text_file.write(full_text)

        # # 保存图片
        # for image_name, image in images.items():
        #     image_path = os.path.join(PARSED_DIRECTORY, f"{image_name}.png")  # 使用字典的键作为文件名
        #     image.save(image_path)  # 假設 image 是 Pillow Image 對象

        # 修改紀錄
        result.status = app.models.Status.Completed.value
        result.parsedPath = text_path
        db.commit()
        db.refresh(result)

        return JSONResponse(content={"message": "success", "data":text_path}, status_code=200)
    except Exception as e:
         # 修改紀錄
        result.status = app.models.Status.Failed.value
        db.commit()
        db.refresh(result)
        raise HTTPException(status_code=500, detail=str(e))
    

# RESET
@fileRouter.delete('/api/reset', status_code=status.HTTP_204_NO_CONTENT)
async def reset_system(db: db_dependency):
    # 刪除資料庫紀錄
    file_to_delete = db.query(app.models.Files).all()
    
    if file_to_delete:
        try:
            # 刪除特定模型表的所有資料
            db.execute(delete(app.models.Files))
            db.commit()
            print("所有資料已成功刪除。")
        except Exception as e:
            db.rollback()
            print(f"刪除失敗: {e}")


    # 刪除檔案
    if os.path.exists(UPLOAD_DIRECTORY):
        for filename in os.listdir(UPLOAD_DIRECTORY):
            file_path = os.path.join(UPLOAD_DIRECTORY, filename)            
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print(f"刪除 {file_path} 時發生錯誤: {e}")

    if os.path.exists(PARSED_DIRECTORY):
        for filename2 in os.listdir(PARSED_DIRECTORY):
            file_path2 = os.path.join(PARSED_DIRECTORY, filename2)            
            try:
                if os.path.isfile(file_path2):
                    os.remove(file_path2)
                elif os.path.isdir(file_path2):
                    shutil.rmtree(file_path2)
            except Exception as e:
                print(f"刪除 {file_path2} 時發生錯誤: {e}")

    return JSONResponse(content={"message": "success"})  # 返回成功消息，数据为空

# Test
@fileRouter.get("/api/test")
async def test(db:db_dependency):

    return JSONResponse(content={"message": "success", "data":""}, status_code=200)

# 紀錄WebSocket連接
active_connections = {}

async def notify_task_complete(websocket:WebSocket):
    await websocket.send_text("Task completed")

@fileRouter.websocket("/ws/{task_id}")
async def websocket_endpoint(websocket:WebSocket, task_id:str):
    await websocket.accept()
    active_connections[task_id] = websocket
    try:
        while True:
            await websocket.receive_text()
    except:
        pass
    finally:
        del active_connections[task_id]

# simulate long task
def long_task(task_id:str):
    time.sleep(5)
    websocket = active_connections.get(task_id)
    if websocket:
        import asyncio
    asyncio.run(notify_task_complete(websocket))

@fileRouter.get("/start_task")
async def start_task(background_tasks:BackgroundTasks):
    task_id = str(uuid.uuid4()) # generate random unique code
    background_tasks.add_task(long_task, task_id)
    return JSONResponse(content={"message": "Task started"}, status_code=200)
