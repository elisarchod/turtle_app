FROM langchain/langgraph-api:3.11



ADD . /deps/turtle-app

RUN PYTHONDONTWRITEBYTECODE=1 pip install --no-cache-dir -c /api/constraints.txt -e /deps/*

ENV LANGSERVE_GRAPHS='{"agent": "/deps/turtle-app/turtleapp/graph.py:agent"}'

WORKDIR /deps/turtle-app
