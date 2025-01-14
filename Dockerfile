# 
FROM python:3.12

# 
WORKDIR /code

RUN apt-get update && apt-get install -y libgl1

RUN pip install --upgrade pip

RUN pip install fastapi uvicorn sqlalchemy psycopg2-binary python-multipart marker-pdf

# COPY ./requirements.txt /code/requirements.txt
# RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# 
COPY ./app /code/app

EXPOSE 8000

# 
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]