"""LLM-based MCP detection classifier.

Reference: FR-020 (≤400ms p95 inference latency), FR-022 (LLM judge), US4
"""
import hashlib
import json
import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

import anthropic
from .cache import ClassificationCache


class JudgeClassifier:
    """LLM-based classifier for MCP detections using Claude."""

    def __init__(
        self,
        api_key: str,
        model: str = "claude-3-5-sonnet-20241022",
        cache_enabled: bool = True,
        cache_ttl_seconds: int = 3600,
    ):
        """Initialize the judge classifier.

        Args:
            api_key: Anthropic API key
            model: Claude model to use
            cache_enabled: Enable response caching
            cache_ttl_seconds: Cache TTL in seconds
        """
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.cache = ClassificationCache() if cache_enabled else None
        self.cache_ttl = timedelta(seconds=cache_ttl_seconds)

        # System prompt for classification
        self.system_prompt = """You are a security analyst specializing in Model Context Protocol (MCP) server detection.

Your task is to analyze evidence about a detected MCP server and classify it as either:
1. AUTHORIZED: Legitimate, expected MCP server used for valid business purposes
2. SUSPECT: Unclear legitimacy, requires further investigation
3. UNAUTHORIZED: Likely malicious or policy-violating MCP server

Consider these factors:
- File paths and locations (production vs dev vs unusual locations)
- Process names and command-line arguments
- Network patterns (common ports vs unusual ports)
- Context clues from manifest files
- Typical enterprise software patterns

Provide your classification with a confidence score (0-100) and brief reasoning."""

    def classify(
        self,
        detection_data: Dict[str, Any],
        bypass_cache: bool = False,
    ) -> Dict[str, Any]:
        """Classify a detection using the LLM.

        Args:
            detection_data: Detection evidence and metadata
            bypass_cache: Skip cache lookup

        Returns:
            Classification result with verdict, confidence, and reasoning
        """
        start_time = time.time()

        # Check cache first
        if self.cache and not bypass_cache:
            cache_key = self._generate_cache_key(detection_data)
            cached_result = self.cache.get(cache_key)
            if cached_result:
                cached_result["cache_hit"] = True
                cached_result["inference_time_ms"] = 0
                return cached_result

        # Build prompt from detection data
        user_prompt = self._build_user_prompt(detection_data)

        # Call Claude API
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                system=self.system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ],
            )

            # Parse response
            response_text = message.content[0].text
            result = self._parse_response(response_text)

            # Calculate inference time
            inference_time = (time.time() - start_time) * 1000  # ms
            result["inference_time_ms"] = inference_time
            result["cache_hit"] = False
            result["model"] = self.model

            # Cache the result
            if self.cache:
                cache_key = self._generate_cache_key(detection_data)
                self.cache.set(cache_key, result, ttl=self.cache_ttl)

            return result

        except Exception as e:
            raise RuntimeError(f"LLM inference failed: {str(e)}")

    def _build_user_prompt(self, detection_data: Dict[str, Any]) -> str:
        """Build user prompt from detection data.

        Args:
            detection_data: Detection evidence

        Returns:
            Formatted prompt string
        """
        prompt_parts = ["Please analyze this MCP server detection:\n"]

        # Add evidence details
        if "evidence" in detection_data:
            prompt_parts.append("\nEvidence:")
            for i, evidence in enumerate(detection_data["evidence"], 1):
                prompt_parts.append(f"\n{i}. Type: {evidence.get('type', 'unknown')}")
                prompt_parts.append(f"   Source: {evidence.get('source', 'unknown')}")

                if "file_path" in evidence:
                    prompt_parts.append(f"   File: {evidence['file_path']}")

                if "process_name" in evidence:
                    prompt_parts.append(f"   Process: {evidence['process_name']}")

                if "snippet" in evidence:
                    # Truncate snippet for prompt
                    snippet = evidence["snippet"][:500]
                    prompt_parts.append(f"   Snippet:\n   {snippet}")

        # Add context
        if "host_id" in detection_data:
            prompt_parts.append(f"\nHost ID (hashed): {detection_data['host_id'][:16]}...")

        if "timestamp" in detection_data:
            prompt_parts.append(f"Detection time: {detection_data['timestamp']}")

        prompt_parts.append("\nProvide your classification in this exact format:")
        prompt_parts.append("CLASSIFICATION: [AUTHORIZED|SUSPECT|UNAUTHORIZED]")
        prompt_parts.append("CONFIDENCE: [0-100]")
        prompt_parts.append("REASONING: [your analysis]")

        return "\n".join(prompt_parts)

    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """Parse LLM response into structured format.

        Args:
            response_text: Raw LLM response

        Returns:
            Parsed classification result
        """
        classification = "suspect"  # Default
        confidence = 50
        reasoning = response_text

        # Parse structured fields
        lines = response_text.split("\n")
        for line in lines:
            line = line.strip()

            if line.startswith("CLASSIFICATION:"):
                value = line.split(":", 1)[1].strip().lower()
                if value in ["authorized", "suspect", "unauthorized"]:
                    classification = value

            elif line.startswith("CONFIDENCE:"):
                try:
                    confidence = int(line.split(":", 1)[1].strip())
                    confidence = max(0, min(100, confidence))  # Clamp 0-100
                except ValueError:
                    pass

            elif line.startswith("REASONING:"):
                reasoning = line.split(":", 1)[1].strip()

        # Map classification to score contribution (FR-003: judge weight = 5)
        score_contribution = self._classification_to_score(classification)

        return {
            "classification": classification,
            "confidence": confidence,
            "reasoning": reasoning,
            "score_contribution": score_contribution,
            "raw_response": response_text,
        }

    def _classification_to_score(self, classification: str) -> int:
        """Map classification to score contribution.

        Args:
            classification: authorized, suspect, or unauthorized

        Returns:
            Score contribution (judge weight = 5 per FR-003)
        """
        # Judge weight is 5, but adjust based on classification
        if classification == "unauthorized":
            return 5  # Full weight
        elif classification == "suspect":
            return 3  # Partial weight
        elif classification == "authorized":
            return 0  # No weight (reduces score)
        return 3  # Default to suspect

    def _generate_cache_key(self, detection_data: Dict[str, Any]) -> str:
        """Generate cache key from detection data.

        Args:
            detection_data: Detection evidence

        Returns:
            SHA256 hash as cache key
        """
        # Create canonical representation
        canonical = json.dumps(detection_data, sort_keys=True)
        return hashlib.sha256(canonical.encode()).hexdigest()

    def batch_classify(
        self,
        detections: List[Dict[str, Any]],
        max_parallel: int = 5,
    ) -> List[Dict[str, Any]]:
        """Classify multiple detections in batch.

        Args:
            detections: List of detection data
            max_parallel: Maximum parallel requests

        Returns:
            List of classification results
        """
        # For now, process sequentially
        # TODO: Implement async/parallel processing
        results = []
        for detection in detections:
            try:
                result = self.classify(detection)
                results.append(result)
            except Exception as e:
                results.append({
                    "error": str(e),
                    "classification": "suspect",  # Default on error
                    "confidence": 0,
                    "score_contribution": 3,
                })

        return results

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics.

        Returns:
            Cache hit rate and other stats
        """
        if not self.cache:
            return {"cache_enabled": False}

        return self.cache.get_stats()
