FROM python:3.11
COPY . /root/.
RUN pip3 install -r /root/requirements.txt
CMD python /root/tasks/telegram_bot/main.py
