FROM opendronemap/odm:latest

RUN apt update
RUN pip install pandas

# Entry point
ENTRYPOINT ["python3", "/code/run.py"]