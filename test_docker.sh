# 停止並移除容器
docker stop testContainer
docker rm testContainer

# 移除映像
docker rmi test

# 建立新的映像
docker build -t test .

# 啟動新的容器
docker run -d --name testContainer -p 8000:8000 test