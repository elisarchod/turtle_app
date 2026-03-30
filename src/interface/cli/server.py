from core.utils import logger


def main():
    import uvicorn
    logger.info("Starting FastAPI server...")
    uvicorn.run("interface.api.app:app", host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
