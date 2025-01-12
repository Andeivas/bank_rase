FROM python:3.12
RUN mkdir -p /usr/src/app/
WORKDIR /usr/src/app/
ADD . /usr/src/app/
RUN pip install -r requirements.txt
CMD ["streamlit", "run", "main.py", "--server.port=8501", "--server.address=0.0.0.0"]