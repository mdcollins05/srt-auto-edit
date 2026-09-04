FROM python:3.11-slim
WORKDIR /app
COPY srtautoedit.py test/cases.sh test/run-tests.sh test/generate-expected.sh ./
RUN pip install --no-cache-dir pyyaml srt
ENTRYPOINT ["python", "srtautoedit.py"]
