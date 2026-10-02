FROM python:3.11-slim

WORKDIR /app

COPY smishing_detector/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && pip install gunicorn

COPY smishing_detector/ ./smishing_detector/
RUN gunzip smishing_detector/best_model.pt.gz

WORKDIR /app/smishing_detector
ENV SCAMSHIELD_DEBUG=false
ENV SCAMSHIELD_HOST=0.0.0.0
ENV SCAMSHIELD_PORT=7860

CMD ["gunicorn", "-w", "1", "-b", "0.0.0.0:7860", "--timeout", "120", "app.flask_api:app"]
