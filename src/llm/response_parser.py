"""
LLM Response Parser

Utilities for parsing and validating LLM responses into structured data.
Handles JSON parsing, fallback responses, and data validation.
"""

import json
import logging
from typing import Dict, Any, Optional, Union

logger = logging.getLogger(__name__)


class ResponseParser:
    """
    LLM response parsing utilities
    
    Provides robust parsing of LLM responses with fallback handling
    and data validation for structured outputs.
    """
    
    @staticmethod
    def parse_json_response(response: str, fallback: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Parse JSON response from LLM with fallback
        
        Args:
            response: Raw LLM response text
            fallback: Default response if parsing fails
            
        Returns:
            Dict: Parsed JSON data or fallback
        """
        try:
            # Try to parse as JSON
            parsed = json.loads(response)
            if isinstance(parsed, dict):
                return parsed
            else:
                logger.warning(f"LLM response is not a JSON object: {type(parsed)}")
                return fallback or {}
                
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM response as JSON: {e}")
            
            # Try to extract JSON from response text
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                try:
                    extracted = response[json_start:json_end]
                    return json.loads(extracted)
                except json.JSONDecodeError:
                    pass
            
            return fallback or {}
    
    @staticmethod
    def parse_compliance_response(response: str) -> Dict[str, Any]:
        """
        Parse compliance analysis response
        
        Args:
            response: LLM response for compliance check
            
        Returns:
            Dict: Structured compliance result
        """
        fallback = {
            "status": "approved",
            "violations": [],
            "severity": "low",
            "user_message": "",
            "recommended_action": "proceed",
            "fallback": True
        }
        
        parsed = ResponseParser.parse_json_response(response, fallback)
        
        # Validate required fields
        if "status" not in parsed or parsed["status"] not in ["approved", "flagged", "blocked"]:
            parsed["status"] = "approved"
        
        if "violations" not in parsed or not isinstance(parsed["violations"], list):
            parsed["violations"] = []
            
        if "severity" not in parsed or parsed["severity"] not in ["low", "medium", "high"]:
            parsed["severity"] = "low"
        
        return parsed
    
    @staticmethod
    def parse_sentiment_response(response: str) -> Dict[str, Any]:
        """
        Parse sentiment analysis response
        
        Args:
            response: LLM response for sentiment analysis
            
        Returns:
            Dict: Structured sentiment result
        """
        fallback = {
            "sentiment": "neutral",
            "score": 0.0,
            "confidence": 0.5,
            "emotions": [],
            "intensity": 5,
            "fallback": True
        }
        
        parsed = ResponseParser.parse_json_response(response, fallback)
        
        # Validate sentiment field
        if "sentiment" not in parsed or parsed["sentiment"] not in ["positive", "negative", "neutral"]:
            parsed["sentiment"] = "neutral"
        
        # Validate score range
        if "score" not in parsed or not isinstance(parsed["score"], (int, float)):
            parsed["score"] = 0.0
        else:
            parsed["score"] = max(-1.0, min(1.0, float(parsed["score"])))
        
        # Validate confidence range
        if "confidence" not in parsed or not isinstance(parsed["confidence"], (int, float)):
            parsed["confidence"] = 0.5
        else:
            parsed["confidence"] = max(0.0, min(1.0, float(parsed["confidence"])))
        
        return parsed
    
    @staticmethod
    def parse_intent_response(response: str) -> Dict[str, Any]:
        """
        Parse intent classification response
        
        Args:
            response: LLM response for intent analysis
            
        Returns:
            Dict: Structured intent result
        """
        fallback = {
            "intent": "browsing",
            "category": "general",
            "confidence": 0.5,
            "urgency": "medium",
            "decision_stage": "awareness",
            "fallback": True
        }
        
        parsed = ResponseParser.parse_json_response(response, fallback)
        
        # Validate intent field
        valid_intents = ["browsing", "interested", "comparing", "ready_to_buy", "post_purchase"]
        if "intent" not in parsed or parsed["intent"] not in valid_intents:
            parsed["intent"] = "browsing"
        
        # Validate category
        valid_categories = ["skincare", "makeup", "fragrance", "tools", "general"]
        if "category" not in parsed or parsed["category"] not in valid_categories:
            parsed["category"] = "general"
        
        # Validate urgency
        valid_urgency = ["low", "medium", "high"]
        if "urgency" not in parsed or parsed["urgency"] not in valid_urgency:
            parsed["urgency"] = "medium"
        
        return parsed


def parse_structured_response(response: str, response_type: str) -> Dict[str, Any]:
    """
    Parse structured LLM response based on type
    
    Args:
        response: Raw LLM response
        response_type: Type of response (compliance, sentiment, intent)
        
    Returns:
        Dict: Parsed and validated response
    """
    if response_type == "compliance":
        return ResponseParser.parse_compliance_response(response)
    elif response_type == "sentiment":
        return ResponseParser.parse_sentiment_response(response)
    elif response_type == "intent":
        return ResponseParser.parse_intent_response(response)
    else:
        logger.warning(f"Unknown response type: {response_type}")
        return ResponseParser.parse_json_response(response, {})