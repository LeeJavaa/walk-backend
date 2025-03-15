"""
File handling utilities for the Walk API.

This module provides utilities for handling file uploads and processing.
"""
import os
import tempfile
import shutil
from typing import IO, Optional
from fastapi import UploadFile
import logging

logger = logging.getLogger(__name__)

def save_upload_file(upload_file: UploadFile, destination: Optional[str] = None) -> str:
    """
    Save an uploaded file to a temporary location or specified destination.

    Args:
        upload_file: The uploaded file
        destination: Optional destination path

    Returns:
        Path to the saved file
    """
    try:
        # If no destination is provided, create a temporary file
        if destination is None:
            suffix = os.path.splitext(upload_file.filename)[1]
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
                destination = temp_file.name

        # Save the uploaded file
        with open(destination, "wb") as buffer:
            # Read in chunks to handle large files
            shutil.copyfileobj(upload_file.file, buffer)

        logger.info(f"File saved to {destination}")
        return destination

    except Exception as e:
        logger.error(f"Error saving uploaded file: {str(e)}")
        raise

    finally:
        # Make sure to close the file
        upload_file.file.close()