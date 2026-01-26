"""
Text Extraction Module

Handles extracting text from images and PDFs using Azure Document Intelligence.
"""

import os
from pathlib import Path
from typing import Dict, Optional
from azure.core.credentials import AzureKeyCredential
from azure.ai.formrecognizer import DocumentAnalysisClient
import time

class TextExtractor:
    """
    Handles text extraction from images and PDFs using Azure Document Intelligence.
    """

    def __init__(self, endpoint: str, key: str):
        """
        Initialize the text extractor with Azure credentials.
        
        Args:
            endpoint: Azure Document Intelligence endpoint
            key: Azure Document Intelligence key
        """
        self.endpoint = endpoint
        self.key = key

        credential = AzureKeyCredential(self.key)
        self.client = DocumentAnalysisClient(
            endpoint=self.endpoint, 
            credential=credential
        )

        print(f"✅ Connected to Azure Document Intelligence")
        