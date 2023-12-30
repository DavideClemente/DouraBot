FROM python:3.11

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY ./src ./src
COPY ./db ./db
RUN mkdir ./logs
COPY .env .

CMD [ "python", "./src/bot.py" ]