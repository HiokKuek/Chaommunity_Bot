FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY orientation_bot ./orientation_bot
EXPOSE 8080
CMD ["uvicorn", "orientation_bot.main:app", "--host", "0.0.0.0", "--port", "8080"]
