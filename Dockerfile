FROM python:3.11

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY ./src ./src
COPY ./db ./db
COPY ./logs ./logs
COPY .env .

CMD [ "python", "./src/bot.py" ]