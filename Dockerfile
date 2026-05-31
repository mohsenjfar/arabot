FROM python:3.11-slim

WORKDIR /ara

COPY requirements.txt /ara/requirements.txt

RUN pip install -r /ara/requirements.txt

COPY . /ara/.

CMD ["python", "-m", "src.app.bot.main"]