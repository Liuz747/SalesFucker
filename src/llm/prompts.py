"""
Prompt Template Management

Centralized prompt templates for all agents in the multi-agent system.
Provides consistent prompt engineering across different agent types.
"""

from typing import Dict, Any, List
from string import Template


class PromptManager:
    """
    Centralized prompt template manager
    
    Manages all prompt templates for different agents and conversation contexts.
    Supports dynamic template substitution and multi-tenant customization.
    """
    
    def __init__(self):
        """Initialize prompt templates"""
        self.templates = self._load_prompt_templates()
    
    def _load_prompt_templates(self) -> Dict[str, Dict[str, str]]:
        """Load all prompt templates organized by agent type"""
        return {
            "compliance": {
                "content_analysis": """You are a compliance expert for cosmetic industry marketing.
                
Analyze the following customer message for compliance issues:
- Regulatory violations (health claims, medical terminology)
- Safety concerns (harmful product usage)
- Inappropriate content (offensive language, spam)

Customer message: "${customer_input}"

Respond with JSON:
{
    "status": "approved|flagged|blocked",
    "violations": ["list of specific violations"],
    "severity": "low|medium|high",
    "user_message": "customer-friendly explanation if blocked",
    "recommended_action": "specific action to take"
}

Be thorough but not overly restrictive. Focus on genuine safety and regulatory concerns."""
            },
            
            "sales": {
                "consultation": """You are an expert beauty consultant for ${brand_name}. 
                
Customer Profile:
- Skin type: ${skin_type}
- Concerns: ${concerns}
- Budget: ${budget_range}
- Previous purchases: ${purchase_history}

Conversation History:
${conversation_history}

Current Customer Message: "${customer_input}"

Generate a natural, helpful response that:
1. Addresses their specific concerns
2. Recommends relevant products if appropriate
3. Maintains ${tone} tone (${tone_description})
4. Uses ${strategy} sales approach
5. Asks follow-up questions to better understand needs

Keep response conversational, knowledgeable, and focused on customer value.""",
                
                "product_recommendation": """As a beauty expert, recommend products based on customer analysis.

Customer Analysis:
- Skin Type: ${skin_type}
- Main Concerns: ${main_concerns}
- Lifestyle: ${lifestyle}
- Budget Preference: ${budget_preference}

Available Products Context: ${product_context}

Provide 2-3 specific product recommendations with:
1. Product name and key benefits
2. Why it's perfect for their skin type/concerns
3. How to use it effectively
4. Expected results and timeline

Focus on products that genuinely solve their problems."""
            },
            
            "sentiment": {
                "emotion_analysis": """Analyze the emotional tone and sentiment of this customer message in a beauty consultation context.

Customer Message: "${customer_input}"
Conversation Context: ${conversation_context}

Provide detailed sentiment analysis including:
1. Overall sentiment (positive/negative/neutral)
2. Emotional intensity (1-10 scale)
3. Specific emotions detected (excited, frustrated, confused, etc.)
4. Customer satisfaction level
5. Urgency or concern level

Respond with structured JSON for easy processing."""
            },
            
            "intent": {
                "classification": """
                Analyze the customer's input and conversation history to identify their primary intent, conversation stage, and extract detailed customer profile information.
                
                Customer Input: "{customer_input}"
                Conversation History:
                {conversation_history}

                Extract the following information:

                1. **PRIMARY INTENT** (choose one):
                - "product_inquiry": Asking about a specific product or product category
                - "skin_concern_consultation": Seeking advice for a skin issue
                - "makeup_advice": Asking for makeup tips, color matching, or application
                - "order_status": Inquiring about an existing order
                - "return_policy": Asking about returns or exchanges
                - "general_inquiry": General questions not fitting other categories
                - "purchase_intent": Expressing readiness or strong interest in buying
                - "browsing": Just looking around, no specific immediate need

                2. **CONVERSATION STAGE** (choose one):
                - "greeting": Initial welcome
                - "need_assessment": Gathering information about customer needs
                - "consultation": Providing detailed advice or recommendations
                - "product_education": Explaining product features/benefits
                - "objection_handling": Addressing concerns (price, skepticism)
                - "closing": Attempting to finalize a sale
                - "support": Handling non-sales related queries

                3. **CUSTOMER PROFILE EXTRACTION** (analyze and infer from context):
                
                **Skin Concerns** (list all mentioned, inferred, or implied):
                - acne, dryness, oiliness, sensitivity, aging, dark_spots, large_pores, dullness, redness, uneven_texture
                
                **Product Interests** (what they want to buy/learn about):
                - skincare, makeup, sunscreen, anti_aging, acne_treatment, moisturizers, cleansers, serums, foundations
                
                **Skin Type Indicators** (mentioned or directly inferred):
                - oily, dry, combination, sensitive, normal, mature
                
                **Urgency Level**:
                - low (browsing/research), medium (planning purchase), high (immediate need), critical (special event/emergency)
                
                **Budget Signals** (mentioned or inferred from language):
                - budget_conscious, value_focused, luxury_oriented, price_sensitive, premium_seeking
                
                **Experience Level** (with beauty products):
                - beginner, intermediate, advanced, expert

                Provide a structured JSON response:
                {{
                  "intent": "primary_intent_here",
                  "confidence": 0.85,
                  "conversation_stage": "stage_here",
                  "customer_profile": {{
                    "skin_concerns": ["concern1", "concern2"],
                    "skin_concerns_confidence": [0.9, 0.7],
                    "product_interests": ["interest1", "interest2"],
                    "skin_type_indicators": ["type1"],
                    "urgency": "medium",
                    "budget_signals": ["signal1"],
                    "experience_level": "intermediate"
                  }},
                  "extraction_confidence": 0.82,
                  "reasoning": "Brief explanation of analysis and key indicators found"
                }}
                """
            }
        }
    
    def get_prompt(self, agent_type: str, prompt_type: str, **kwargs) -> str:
        """
        Get formatted prompt template
        
        Args:
            agent_type: Type of agent (compliance, sales, sentiment, intent)
            prompt_type: Specific prompt within agent type
            **kwargs: Template variables for substitution
            
        Returns:
            str: Formatted prompt template
        """
        if agent_type not in self.templates:
            raise ValueError(f"Unknown agent type: {agent_type}")
            
        agent_templates = self.templates[agent_type]
        if prompt_type not in agent_templates:
            raise ValueError(f"Unknown prompt type '{prompt_type}' for agent '{agent_type}'")
        
        template = Template(agent_templates[prompt_type])
        
        # Provide safe defaults for missing variables
        safe_kwargs = {
            "customer_input": "",
            "conversation_history": "No previous conversation",
            "brand_name": "our brand",
            "skin_type": "not specified",
            "concerns": "not specified", 
            "budget_range": "not specified",
            "purchase_history": "none",
            "tone": "friendly",
            "tone_description": "warm and professional",
            "strategy": "consultative",
            "conversation_context": "initial consultation",
            "previous_intent": "unknown",
            **kwargs
        }
        
        return template.safe_substitute(**safe_kwargs)
    
    def format_conversation_history(self, history: List[str], max_entries: int = 5) -> str:
        """
        Format conversation history for prompt inclusion
        
        Args:
            history: List of conversation messages
            max_entries: Maximum number of recent entries to include
            
        Returns:
            str: Formatted conversation history
        """
        if not history:
            return "No previous conversation"
            
        recent_history = history[-max_entries:] if len(history) > max_entries else history
        return "\n".join(f"- {msg}" for msg in recent_history)


# Global prompt manager instance
_prompt_manager: PromptManager = None


def get_prompt_manager() -> PromptManager:
    """Get or create global prompt manager instance"""
    global _prompt_manager
    if _prompt_manager is None:
        _prompt_manager = PromptManager()
    return _prompt_manager