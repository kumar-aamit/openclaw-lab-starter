import uvicorn

from .config import Settings


def main() -> None:
    settings = Settings.from_env()
    uvicorn.run("baseapp.main:app", host="0.0.0.0", port=settings.port, workers=1, access_log=False)


if __name__ == "__main__":
    main()
