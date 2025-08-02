"""
选择引擎模块

负责最终的供应商选择逻辑。
"""

import random
from typing import List

from ..base_provider import BaseProvider, ProviderError
from .models import RoutingContext, ProviderScore


class SelectionEngine:
    """选择引擎类"""
    
    def __init__(self):
        """初始化选择引擎"""
        pass
    
    def select_provider(
        self, 
        provider_scores: List[ProviderScore], 
        context: RoutingContext
    ) -> BaseProvider:
        """选择最终的供应商"""
        if not provider_scores:
            raise ProviderError("没有可评分的供应商", None, "NO_SCORABLE_PROVIDERS")
        
        # 如果是重试，避免选择之前失败的供应商
        if context.retry_count > 0 and context.previous_provider:
            for score in provider_scores:
                if score.provider.provider_type != context.previous_provider:
                    return score.provider
        
        # 质量阈值过滤
        qualified_scores = [
            score for score in provider_scores 
            if score.total_score >= context.quality_threshold
        ]
        
        if not qualified_scores:
            # 降低阈值重试
            qualified_scores = provider_scores[:3]  # 取前3名
        
        # 加入随机性以避免总是选择同一供应商
        if len(qualified_scores) > 1:
            # 前20%的供应商参与随机选择
            top_count = max(1, len(qualified_scores) // 5)
            top_scores = qualified_scores[:top_count]
            
            # 基于得分的加权随机选择
            weights = [score.total_score for score in top_scores]
            selected_score = random.choices(top_scores, weights=weights, k=1)[0]
            
            return selected_score.provider
        else:
            return qualified_scores[0].provider