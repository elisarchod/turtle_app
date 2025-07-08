FROM langchain/langgraph-api:3.11

RUN mkdir -p /movies

ADD . /deps/turtle-app

RUN PYTHONDONTWRITEBYTECODE=1 pip install --no-cache-dir -c /api/constraints.txt -e /deps/*

ENV LANGSERVE_GRAPHS='{"agent": "/deps/turtle-app/turtleapp/src/workflows/graph.py:movie_workflow_agent"}'

WORKDIR /deps/turtle-app

VOLUME ["/movies"]
