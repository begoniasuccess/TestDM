from typing import Union
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import os

from app.api.questions import questionRouter
from app.api.files import fileRouter

app = FastAPI()

# 設定靜態資源路徑
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# 註冊路由
app.include_router(fileRouter)
app.include_router(questionRouter)

@app.get("/", response_class=FileResponse)
async def read_root():
    file_path = os.path.join("app/templates", "index.html")
    return FileResponse(file_path)

@app.get("/test")
def read_root():
    return {"Hello": "World"}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}