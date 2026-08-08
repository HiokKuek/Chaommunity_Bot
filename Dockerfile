FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY orientation_bot ./orientation_bot
CMD ["python", "-m", "orientation_bot.main"]
