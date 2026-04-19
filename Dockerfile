FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# handle.txtをデフォルト値として保存しておく（ボリュームが空の場合にコピー）
RUN cp data/handle.txt /handle.txt.default
CMD ["sh", "-c", "[ ! -f data/handle.txt ] && cp /handle.txt.default data/handle.txt; python bot.py"]
