"""Entry point for running thalimage with uvicorn."""

import uvicorn

from thalimage.config import get_settings


def main() -> None:
    settings = get_settings()
    uvicorn.run(
        "thalimage.app:create_app",
        factory=True,
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )


if __name__ == "__main__":
    main()
