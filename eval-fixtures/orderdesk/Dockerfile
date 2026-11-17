FROM python:3.12-slim
WORKDIR /app
COPY orderdesk/ orderdesk/
COPY scripts/ scripts/
ENV ORDERDESK_DB=/data/orderdesk.db
EXPOSE 8080
CMD ["python3", "-m", "orderdesk.server"]
