FROM python:3.9-slim

# 1. Setup User (Wajib untuk HF Spaces)
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

WORKDIR $HOME/app


COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt


COPY --chown=user . .


EXPOSE 7860
CMD ["gunicorn", "-b", "0.0.0.0:7860", "src.app:app", "--timeout", "120"]