"""
Image Understanding Tool
=========================

Handles image analysis using Gemini Vision API and OCR.
Supports image description, object detection, text extraction, and more.
"""

import base64
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class ImageTool:
    """
    Image understanding tool for Bijou.

    Provides image analysis capabilities using Google Gemini Vision API.
    Supports: image description, OCR, object detection, scene understanding.
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Image tool.

        Args:
            api_key: Google AI API key for Gemini Vision
        """
        self.api_key = api_key or os.getenv("GOOGLE_AI_API_KEY")
        self.gemini_endpoint = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
        self._initialized = bool(self.api_key)

        if not self._initialized:
            logger.warning(
                "Image tool initialized without API key. Set GOOGLE_AI_API_KEY."
            )

    def analyze_image(
        self,
        image_path: str,
        prompt: Optional[str] = None,
        detail_level: str = "medium",
    ) -> Dict[str, Any]:
        """
        Analyze an image using Gemini Vision.

        Args:
            image_path: Path to image file or URL
            prompt: Custom prompt for analysis (default: general description)
            detail_level: Level of detail - "low", "medium", "high"

        Returns:
            Dictionary with analysis results

        Example:
            >>> tool = ImageTool()
            >>> result = tool.analyze_image("photo.jpg", "What's in this image?")
            >>> print(result["description"])
        """
        if not self._initialized:
            return {"success": False, "error": "API key not configured"}

        try:
            # Read and encode image
            image_data = self._load_image(image_path)
            if not image_data:
                return {"success": False, "error": "Failed to load image"}

            # Default prompt if none provided
            if prompt is None:
                prompt = "Describe this image in detail. Include objects, people, text, colors, and context."

            # Adjust prompt based on detail level
            if detail_level == "high":
                prompt += " Provide extensive detail about all visible elements."
            elif detail_level == "low":
                prompt += " Provide a brief summary."

            # Call Gemini Vision API
            result = self._call_gemini_vision(image_data, prompt)

            if result.get("success"):
                return {
                    "success": True,
                    "description": result.get("text", ""),
                    "prompt": prompt,
                    "detail_level": detail_level,
                }
            else:
                return result

        except Exception as e:
            logger.error(f"Failed to analyze image: {e}")
            return {"success": False, "error": str(e)}

    def extract_text(self, image_path: str) -> Dict[str, Any]:
        """
        Extract text from an image (OCR).

        Args:
            image_path: Path to image file

        Returns:
            Dictionary with extracted text

        Example:
            >>> tool = ImageTool()
            >>> result = tool.extract_text("document.jpg")
            >>> print(result["text"])
        """
        prompt = """Extract all visible text from this image.
        Preserve formatting, line breaks, and structure.
        If there's no text, say 'No text found'.
        Return only the extracted text, nothing else."""

        result = self.analyze_image(image_path, prompt=prompt)

        if result.get("success"):
            return {
                "success": True,
                "text": result.get("description", ""),
                "image_path": image_path,
            }
        else:
            return result

    def identify_objects(self, image_path: str) -> Dict[str, Any]:
        """
        Identify objects in an image.

        Args:
            image_path: Path to image file

        Returns:
            Dictionary with identified objects

        Example:
            >>> tool = ImageTool()
            >>> result = tool.identify_objects("scene.jpg")
            >>> print(result["objects"])
        """
        prompt = """List all objects and items visible in this image.
        For each object, provide:
        1. Object name
        2. Approximate location in the image
        3. Any relevant details (color, size, state)

        Format as a numbered list."""

        result = self.analyze_image(image_path, prompt=prompt)

        if result.get("success"):
            return {
                "success": True,
                "objects": result.get("description", ""),
                "image_path": image_path,
            }
        else:
            return result

    def answer_question(self, image_path: str, question: str) -> Dict[str, Any]:
        """
        Answer a question about an image.

        Args:
            image_path: Path to image file
            question: Question to answer

        Returns:
            Dictionary with answer

        Example:
            >>> tool = ImageTool()
            >>> result = tool.answer_question("photo.jpg", "How many people are in this photo?")
            >>> print(result["answer"])
        """
        result = self.analyze_image(image_path, prompt=question)

        if result.get("success"):
            return {
                "success": True,
                "question": question,
                "answer": result.get("description", ""),
                "image_path": image_path,
            }
        else:
            return result

    def analyze_document(self, image_path: str) -> Dict[str, Any]:
        """
        Analyze a document image (invoice, receipt, form, etc.).

        Args:
            image_path: Path to document image

        Returns:
            Dictionary with document analysis

        Example:
            >>> tool = ImageTool()
            >>> result = tool.analyze_document("invoice.jpg")
            >>> print(result["analysis"])
        """
        prompt = """Analyze this document image.
        Extract and provide:
        1. Document type (invoice, receipt, form, letter, etc.)
        2. Key information (dates, amounts, names, addresses)
        3. All visible text and numbers
        4. Any signatures or stamps
        5. Document structure and sections

        Format the response clearly."""

        result = self.analyze_image(image_path, prompt=prompt)

        if result.get("success"):
            return {
                "success": True,
                "analysis": result.get("description", ""),
                "document_type": self._extract_document_type(
                    result.get("description", "")
                ),
                "image_path": image_path,
            }
        else:
            return result

    def compare_images(
        self, image_path1: str, image_path2: str, focus: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Compare two images and describe differences.

        Args:
            image_path1: Path to first image
            image_path2: Path to second image
            focus: Specific aspect to focus on (optional)

        Returns:
            Dictionary with comparison results
        """
        # Analyze both images
        prompt1 = "Describe this image in detail."
        prompt2 = "Describe this image in detail."

        result1 = self.analyze_image(image_path1, prompt=prompt1)
        result2 = self.analyze_image(image_path2, prompt=prompt2)

        if not (result1.get("success") and result2.get("success")):
            return {"success": False, "error": "Failed to analyze one or both images"}

        # Note: For true comparison, would need multi-image API support
        # This is a sequential analysis approach
        return {
            "success": True,
            "image1_analysis": result1.get("description", ""),
            "image2_analysis": result2.get("description", ""),
            "note": "Sequential analysis - for best results, compare descriptions manually or use multi-image API when available",
        }

    def _load_image(self, image_path: str) -> Optional[str]:
        """
        Load and encode image to base64.

        Args:
            image_path: Path to image file or URL

        Returns:
            Base64 encoded image string or None
        """
        try:
            # Check if it's a URL
            if image_path.startswith(("http://", "https://")):
                # Download image
                response = httpx.get(image_path, timeout=30.0)
                response.raise_for_status()
                image_bytes = response.content
            else:
                # Read local file
                with open(image_path, "rb") as f:
                    image_bytes = f.read()

            # Encode to base64
            return base64.b64encode(image_bytes).decode("utf-8")

        except Exception as e:
            logger.error(f"Failed to load image: {e}")
            return None

    def _call_gemini_vision(self, image_base64: str, prompt: str) -> Dict[str, Any]:
        """
        Call Gemini Vision API.

        Args:
            image_base64: Base64 encoded image
            prompt: Analysis prompt

        Returns:
            Dictionary with API response
        """
        try:
            # Detect image format (assume JPEG if unknown)
            mime_type = "image/jpeg"
            if image_base64.startswith("/9j/"):
                mime_type = "image/jpeg"
            elif image_base64.startswith("iVBORw0KGgo"):
                mime_type = "image/png"

            # Build request
            url = f"{self.gemini_endpoint}?key={self.api_key}"
            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": prompt},
                            {
                                "inline_data": {
                                    "mime_type": mime_type,
                                    "data": image_base64,
                                }
                            },
                        ]
                    }
                ]
            }

            # Call API
            response = httpx.post(url, json=payload, timeout=60.0)
            response.raise_for_status()

            result = response.json()

            # Extract text from response
            if "candidates" in result and len(result["candidates"]) > 0:
                candidate = result["candidates"][0]
                if "content" in candidate and "parts" in candidate["content"]:
                    text = candidate["content"]["parts"][0].get("text", "")
                    return {"success": True, "text": text}

            return {"success": False, "error": "No valid response from API"}

        except httpx.HTTPStatusError as e:
            logger.error(f"Gemini Vision API error: {e.response.status_code}")
            return {
                "success": False,
                "error": f"API error {e.response.status_code}: {e.response.text}",
            }
        except Exception as e:
            logger.error(f"Failed to call Gemini Vision API: {e}")
            return {"success": False, "error": str(e)}

    def _extract_document_type(self, analysis_text: str) -> str:
        """
        Extract document type from analysis text.

        Args:
            analysis_text: Analysis result text

        Returns:
            Document type string
        """
        text_lower = analysis_text.lower()

        # Common document types
        types = [
            "invoice",
            "receipt",
            "form",
            "letter",
            "contract",
            "resume",
            "cv",
            "report",
            "statement",
            "certificate",
        ]

        for doc_type in types:
            if doc_type in text_lower:
                return doc_type

        return "unknown"
