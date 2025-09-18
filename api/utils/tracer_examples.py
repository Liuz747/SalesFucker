"""
LangFuse Tracer Usage Examples

This file demonstrates how to use the updated tracer_client.py with LangFuse SDK v3
for comprehensive workflow observation in the MAS multi-agent system.
"""

from typing import Dict, Any
from utils.tracer_client import (
    trace_workflow_step,
    trace_agent_interaction,
    trace_conversation_context,
    trace_llm_generation,
    flush_traces
)


# Example 1: Basic workflow step tracing with decorator
@trace_workflow_step(name="message-preprocessing", as_type="span")
def preprocess_message(message: str, user_id: str) -> Dict[str, Any]:
    """
    预处理用户消息
    """
    return {
        "cleaned_message": message.strip().lower(),
        "user_id": user_id,
        "timestamp": "2025-09-18T10:00:00Z"
    }


# Example 2: Agent-specific tracing
@trace_agent_interaction("sentiment", tenant_id="cosmetic_clinic_001")
def analyze_message_sentiment(message: str) -> Dict[str, Any]:
    """
    使用情感分析智能体处理消息
    """
    # 模拟情感分析逻辑
    return {
        "sentiment": "positive",
        "confidence": 0.92,
        "emotions": ["happy", "excited"]
    }


@trace_agent_interaction("product-expert", tenant_id="cosmetic_clinic_001")
def get_product_recommendations(user_profile: Dict[str, Any]) -> Dict[str, Any]:
    """
    使用产品专家智能体生成推荐
    """
    # 模拟产品推荐逻辑
    return {
        "recommendations": [
            {"product_id": "serum_001", "confidence": 0.95},
            {"product_id": "moisturizer_002", "confidence": 0.88}
        ],
        "reasoning": "Based on skin type analysis"
    }


# Example 3: Complex workflow with context manager
def process_complete_conversation(conversation_id: str, user_message: str, user_id: str):
    """
    完整对话处理流程示例
    """
    # 使用上下文管理器追踪整个对话
    with trace_conversation_context(
        conversation_id=conversation_id,
        user_id=user_id,
        metadata={"workflow_type": "multi-agent-consultation"}
    ) as conversation_span:

        # 步骤1：预处理消息
        preprocessed = preprocess_message(user_message, user_id)
        conversation_span.update(metadata={"step": "preprocessing_complete"})

        # 步骤2：情感分析
        sentiment_result = analyze_message_sentiment(preprocessed["cleaned_message"])
        conversation_span.update(metadata={"step": "sentiment_analysis_complete"})

        # 步骤3：产品推荐
        user_profile = {"skin_type": "dry", "age": 28, "concerns": ["wrinkles"]}
        recommendations = get_product_recommendations(user_profile)
        conversation_span.update(metadata={"step": "recommendations_generated"})

        # 步骤4：生成最终回复
        final_response = generate_consultation_response(
            sentiment_result, recommendations, preprocessed["cleaned_message"]
        )

        # 更新对话span的最终结果
        conversation_span.update(
            output={
                "response": final_response,
                "recommendations_count": len(recommendations["recommendations"]),
                "sentiment": sentiment_result["sentiment"]
            }
        )

        return final_response


@trace_workflow_step(name="response-generation", as_type="generation")
def generate_consultation_response(
    sentiment_result: Dict[str, Any],
    recommendations: Dict[str, Any],
    original_message: str
) -> str:
    """
    生成咨询回复
    """
    # 模拟LLM调用追踪
    trace_llm_generation(
        model="gpt-4",
        prompt=f"Generate response for: {original_message}",
        response="Based on your skin concerns, I recommend...",
        metadata={
            "sentiment": sentiment_result["sentiment"],
            "recommendation_count": len(recommendations["recommendations"])
        }
    )

    return "Based on your skin concerns and our analysis, I recommend these products..."


# Example 4: Error handling demonstration
@trace_workflow_step(name="risky-operation", capture_input=True, capture_output=True)
def potentially_failing_operation(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    演示错误处理的操作
    """
    if not data.get("valid"):
        raise ValueError("Invalid data provided")

    return {"processed": True, "result": "success"}


# Example 5: Usage in application shutdown
def application_shutdown():
    """
    应用程序关闭时的清理操作
    """
    print("Flushing LangFuse traces...")
    flush_traces()
    print("Application shutdown complete")


if __name__ == "__main__":
    # 演示用法
    print("LangFuse Tracer Examples")
    print("========================")

    # 示例对话处理
    try:
        response = process_complete_conversation(
            conversation_id="conv_123456",
            user_message="I'm looking for anti-aging skincare products",
            user_id="user_789"
        )
        print(f"Generated response: {response}")

        # 演示错误处理
        try:
            potentially_failing_operation({"valid": False})
        except ValueError as e:
            print(f"Caught expected error: {e}")

        # 清理
        application_shutdown()

    except Exception as e:
        print(f"Error in example: {e}")
        flush_traces()  # 确保即使出错也发送追踪数据