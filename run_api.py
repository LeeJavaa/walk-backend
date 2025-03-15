#!/usr/bin/env python
"""
Script to run the Walk API.
"""
import uvicorn
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("walk-api")


def main():
    """Entry point for the API server."""
    try:
        # Load environment variables
        load_dotenv()

        # Run the FastAPI application
        logger.info("Starting Walk API server")
        uvicorn.run(
            "src.infrastructure.api.main:app",
            host="0.0.0.0",
            port=8000,
            reload=True
        )
    except Exception as e:
        logger.error(f"Error starting API server: {str(e)}", exc_info=True)
        return 1

    return 0


if __name__ == "__main__":
    exit(main())