"""
产品专家智能体多模态集成模块

该模块为产品专家智能体提供多模态输入处理能力。
结合语音转录和图像分析结果，提供更精准的产品推荐。

核心功能:
- 多模态输入分析和整合
- 图像驱动的产品推荐
- 语音情感增强的推荐策略
- 多模态上下文保持
"""

from typing import Dict, Any, List, Optional
import asyncio
from datetime import datetime

from utils import (
    get_current_datetime,
    LoggerMixin,
    ProcessingType,
    InputType
)


class MultimodalProductAnalyzer(LoggerMixin):
    """
    多模态产品分析器
    
    分析多模态输入并提供增强的产品推荐策略。
    
    属性:
        tenant_id: 租户标识符
        analysis_cache: 分析结果缓存
    """
    
    def __init__(self, tenant_id: str):
        """
        初始化多模态产品分析器
        
        Args:
            tenant_id: 租户标识符
        """
        super().__init__()
        self.tenant_id = tenant_id
        self.analysis_cache = {}
        
        self.logger.info(f"多模态产品分析器已初始化: {tenant_id}")
    
    async def analyze_multimodal_context(
        self,
        message_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        分析多模态上下文
        
        Args:
            message_context: 消息上下文，包含多模态处理结果
            
        Returns:
            增强的分析结果
        """
        input_type = message_context.get('input_type', InputType.TEXT)
        
        analysis_result = {
            'input_type': input_type,
            'enhancement_factors': {},
            'recommendation_weights': {},
            'priority_adjustments': {},
            'content_analysis': {}
        }
        
        # 分析语音输入
        if input_type in [InputType.VOICE, InputType.MULTIMODAL]:
            voice_analysis = await self._analyze_voice_context(message_context)
            analysis_result['enhancement_factors']['voice'] = voice_analysis
        
        # 分析图像输入
        if input_type in [InputType.IMAGE, InputType.MULTIMODAL]:
            image_analysis = await self._analyze_image_context(message_context)
            analysis_result['enhancement_factors']['image'] = image_analysis
        
        # 生成推荐策略调整
        strategy_adjustments = await self._generate_strategy_adjustments(
            analysis_result['enhancement_factors']
        )
        analysis_result['strategy_adjustments'] = strategy_adjustments
        
        return analysis_result
    
    async def _analyze_voice_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """分析语音上下文"""
        voice_analysis = {
            'has_transcription': False,
            'emotional_indicators': {},
            'urgency_level': 'normal',
            'confidence_factors': [],
            'recommendation_modifiers': {}
        }
        
        try:
            transcriptions = context.get('transcriptions', [])
            if transcriptions:
                voice_analysis['has_transcription'] = True
                
                # 分析转录文本中的情感指标
                combined_text = ' '.join(transcriptions)
                emotional_indicators = self._extract_emotional_indicators(combined_text)
                voice_analysis['emotional_indicators'] = emotional_indicators
                
                # 评估紧急程度
                urgency = self._assess_urgency_from_voice(combined_text)
                voice_analysis['urgency_level'] = urgency
                
                # 生成推荐调整因子
                modifiers = self._generate_voice_modifiers(emotional_indicators, urgency)
                voice_analysis['recommendation_modifiers'] = modifiers
                
                self.logger.debug(f"语音分析完成: 情感={emotional_indicators}, 紧急度={urgency}")
        
        except Exception as e:
            self.logger.warning(f"语音上下文分析失败: {e}")
        
        return voice_analysis
    
    async def _analyze_image_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """分析图像上下文"""
        image_analysis = {
            'has_analysis': False,
            'skin_insights': {},
            'product_matches': [],
            'visual_preferences': {},
            'recommendation_priorities': {}
        }
        
        try:
            image_analysis_results = context.get('image_analysis', {})
            
            if image_analysis_results:
                image_analysis['has_analysis'] = True
                
                # 处理每个图像的分析结果
                for attachment_id, analysis_data in image_analysis_results.items():
                    await self._process_image_analysis(
                        attachment_id, 
                        analysis_data, 
                        image_analysis
                    )
                
                self.logger.debug(f"图像分析完成: {len(image_analysis_results)}个图像")
        
        except Exception as e:
            self.logger.warning(f"图像上下文分析失败: {e}")
        
        return image_analysis
    
    async def _process_image_analysis(
        self,
        attachment_id: str,
        analysis_data: Dict[str, Any],
        image_analysis: Dict[str, Any]
    ):
        """处理单个图像的分析结果"""
        results = analysis_data.get('results', {})
        
        # 处理皮肤分析结果
        if 'skin_concerns' in results:
            skin_insights = self._extract_skin_insights(results)
            image_analysis['skin_insights'][attachment_id] = skin_insights
        
        # 处理产品识别结果
        if 'products' in results:
            product_matches = self._extract_product_matches(results)
            image_analysis['product_matches'].extend(product_matches)
        
        # 提取视觉偏好
        if 'overall_assessment' in results:
            visual_prefs = self._extract_visual_preferences(results)
            image_analysis['visual_preferences'][attachment_id] = visual_prefs
    
    def _extract_emotional_indicators(self, text: str) -> Dict[str, Any]:
        """从文本中提取情感指标"""
        indicators = {
            'enthusiasm': 0.0,
            'concern': 0.0,
            'urgency': 0.0,
            'satisfaction': 0.0,
            'confusion': 0.0
        }
        
        text_lower = text.lower()
        
        # 热情指标
        enthusiasm_words = ['喜欢', '爱', '想要', '好看', '漂亮', '完美', '太棒了']
        indicators['enthusiasm'] = sum(1 for word in enthusiasm_words if word in text_lower) / len(text_lower) * 10
        
        # 担忧指标
        concern_words = ['担心', '问题', '不好', '过敏', '敏感', '痘痘', '干燥']
        indicators['concern'] = sum(1 for word in concern_words if word in text_lower) / len(text_lower) * 10
        
        # 紧急指标
        urgency_words = ['急需', '马上', '立即', '尽快', '今天', '现在']
        indicators['urgency'] = sum(1 for word in urgency_words if word in text_lower) / len(text_lower) * 10
        
        # 满意度指标
        satisfaction_words = ['满意', '满足', '够了', '不错', '可以']
        indicators['satisfaction'] = sum(1 for word in satisfaction_words if word in text_lower) / len(text_lower) * 10
        
        # 困惑指标
        confusion_words = ['不知道', '不确定', '什么', '怎么', '哪个']
        indicators['confusion'] = sum(1 for word in confusion_words if word in text_lower) / len(text_lower) * 10
        
        return indicators
    
    def _assess_urgency_from_voice(self, text: str) -> str:
        """从语音文本评估紧急程度"""
        urgent_phrases = ['急需', '马上要', '立即', '现在就要', '今天必须']
        high_phrases = ['尽快', '快点', '着急', '赶时间']
        
        text_lower = text.lower()
        
        if any(phrase in text_lower for phrase in urgent_phrases):
            return 'urgent'
        elif any(phrase in text_lower for phrase in high_phrases):
            return 'high'
        else:
            return 'normal'
    
    def _generate_voice_modifiers(
        self, 
        emotional_indicators: Dict[str, float], 
        urgency: str
    ) -> Dict[str, Any]:
        """生成基于语音的推荐调整因子"""
        modifiers = {
            'recommendation_count': 3,  # 默认推荐数量
            'detail_level': 'standard',
            'tone_adjustment': 'neutral',
            'priority_boost': []
        }
        
        # 根据情感调整推荐策略
        if emotional_indicators.get('enthusiasm', 0) > 0.3:
            modifiers['recommendation_count'] = 5
            modifiers['tone_adjustment'] = 'enthusiastic'
            modifiers['priority_boost'].append('trending_products')
        
        if emotional_indicators.get('concern', 0) > 0.3:
            modifiers['detail_level'] = 'detailed'
            modifiers['tone_adjustment'] = 'reassuring'
            modifiers['priority_boost'].append('sensitive_skin_products')
        
        if emotional_indicators.get('confusion', 0) > 0.3:
            modifiers['detail_level'] = 'educational'
            modifiers['tone_adjustment'] = 'explanatory'
            modifiers['priority_boost'].append('beginner_friendly')
        
        # 根据紧急程度调整
        if urgency == 'urgent':
            modifiers['recommendation_count'] = 2
            modifiers['priority_boost'].append('fast_delivery')
        elif urgency == 'high':
            modifiers['priority_boost'].append('quick_results')
        
        return modifiers
    
    def _extract_skin_insights(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """提取皮肤分析洞察"""
        insights = {
            'skin_type': results.get('skin_type', ''),
            'primary_concerns': [],
            'secondary_concerns': [],
            'recommendation_focus': []
        }
        
        # 分析皮肤问题的严重程度
        skin_concerns = results.get('skin_concerns', [])
        for concern in skin_concerns:
            severity = concern.get('severity', 'mild')
            concern_type = concern.get('type', '')
            
            if severity in ['severe', 'moderate']:
                insights['primary_concerns'].append(concern_type)
            else:
                insights['secondary_concerns'].append(concern_type)
        
        # 生成推荐焦点
        insights['recommendation_focus'] = self._generate_skin_focus(insights)
        
        return insights
    
    def _extract_product_matches(self, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """提取产品匹配信息"""
        matches = []
        
        products = results.get('products', [])
        for product in products:
            if product.get('confidence', 0) > 0.6:  # 只考虑高置信度的识别
                matches.append({
                    'name': product.get('name', ''),
                    'brand': product.get('brand', ''),
                    'category': product.get('category', ''),
                    'confidence': product.get('confidence', 0),
                    'action': 'complement'  # 默认为互补推荐
                })
        
        return matches
    
    def _extract_visual_preferences(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """提取视觉偏好信息"""
        preferences = {
            'style_indicators': [],
            'color_preferences': [],
            'product_categories': []
        }
        
        # 从分析结果中提取偏好指标
        overall_assessment = results.get('overall_assessment', '')
        if overall_assessment:
            # 简单的关键词提取（可以后续优化为更复杂的NLP分析）
            if '自然' in overall_assessment or 'natural' in overall_assessment.lower():
                preferences['style_indicators'].append('natural')
            if '时尚' in overall_assessment or 'fashion' in overall_assessment.lower():
                preferences['style_indicators'].append('trendy')
        
        return preferences
    
    def _generate_skin_focus(self, insights: Dict[str, Any]) -> List[str]:
        """生成皮肤关注焦点"""
        focus_areas = []
        
        primary_concerns = insights.get('primary_concerns', [])
        skin_type = insights.get('skin_type', '')
        
        # 根据主要问题生成焦点
        concern_mapping = {
            '痘痘': 'acne_treatment',
            '色斑': 'brightening',
            '皱纹': 'anti_aging',
            '干燥': 'hydration',
            '出油': 'oil_control'
        }
        
        for concern in primary_concerns:
            if concern in concern_mapping:
                focus_areas.append(concern_mapping[concern])
        
        # 根据肌肤类型添加基础护理
        if '干性' in skin_type:
            focus_areas.append('moisturizing')
        elif '油性' in skin_type:
            focus_areas.append('cleansing')
        elif '敏感性' in skin_type:
            focus_areas.append('gentle_care')
        
        return focus_areas
    
    async def _generate_strategy_adjustments(
        self,
        enhancement_factors: Dict[str, Any]
    ) -> Dict[str, Any]:
        """生成推荐策略调整"""
        adjustments = {
            'search_keywords': [],
            'filter_criteria': {},
            'ranking_weights': {},
            'presentation_style': 'standard'
        }
        
        # 处理语音增强因子
        voice_factors = enhancement_factors.get('voice', {})
        if voice_factors.get('has_transcription'):
            voice_modifiers = voice_factors.get('recommendation_modifiers', {})
            
            # 调整推荐数量
            if 'recommendation_count' in voice_modifiers:
                adjustments['max_recommendations'] = voice_modifiers['recommendation_count']
            
            # 调整呈现风格
            adjustments['presentation_style'] = voice_modifiers.get('tone_adjustment', 'standard')
            
            # 添加优先级提升
            priority_boosts = voice_modifiers.get('priority_boost', [])
            adjustments['priority_categories'] = priority_boosts
        
        # 处理图像增强因子
        image_factors = enhancement_factors.get('image', {})
        if image_factors.get('has_analysis'):
            # 基于皮肤分析调整搜索
            skin_insights = image_factors.get('skin_insights', {})
            for attachment_id, insights in skin_insights.items():
                focus_areas = insights.get('recommendation_focus', [])
                adjustments['search_keywords'].extend(focus_areas)
            
            # 基于产品匹配调整过滤
            product_matches = image_factors.get('product_matches', [])
            if product_matches:
                matched_brands = [match['brand'] for match in product_matches if match['brand']]
                adjustments['filter_criteria']['preferred_brands'] = matched_brands
        
        return adjustments
    
    async def enhance_product_search(
        self,
        base_query: str,
        multimodal_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        基于多模态分析增强产品搜索
        
        Args:
            base_query: 基础搜索查询
            multimodal_analysis: 多模态分析结果
            
        Returns:
            增强的搜索参数
        """
        strategy_adjustments = multimodal_analysis.get('strategy_adjustments', {})
        
        enhanced_query = {
            'base_query': base_query,
            'enhanced_keywords': [],
            'filters': {},
            'ranking_adjustments': {},
            'max_results': 10
        }
        
        # 添加增强关键词
        additional_keywords = strategy_adjustments.get('search_keywords', [])
        enhanced_query['enhanced_keywords'] = additional_keywords
        
        # 组合完整查询
        full_keywords = [base_query] + additional_keywords
        enhanced_query['combined_query'] = ' '.join(full_keywords)
        
        # 设置过滤条件
        filter_criteria = strategy_adjustments.get('filter_criteria', {})
        enhanced_query['filters'] = filter_criteria
        
        # 调整结果数量
        max_recommendations = strategy_adjustments.get('max_recommendations', 10)
        enhanced_query['max_results'] = max_recommendations
        
        # 设置优先级类别
        priority_categories = strategy_adjustments.get('priority_categories', [])
        enhanced_query['priority_categories'] = priority_categories
        
        return enhanced_query
    
    async def format_multimodal_recommendations(
        self,
        recommendations: List[Dict[str, Any]],
        multimodal_analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        格式化多模态推荐结果
        
        Args:
            recommendations: 基础推荐列表
            multimodal_analysis: 多模态分析结果
            
        Returns:
            格式化的推荐结果
        """
        strategy_adjustments = multimodal_analysis.get('strategy_adjustments', {})
        presentation_style = strategy_adjustments.get('presentation_style', 'standard')
        
        formatted_recommendations = []
        
        for rec in recommendations:
            formatted_rec = rec.copy()
            
            # 根据呈现风格调整描述
            if presentation_style == 'enthusiastic':
                formatted_rec['tone'] = 'enthusiastic'
                formatted_rec['description_style'] = 'exciting'
            elif presentation_style == 'reassuring':
                formatted_rec['tone'] = 'reassuring'
                formatted_rec['description_style'] = 'gentle'
            elif presentation_style == 'explanatory':
                formatted_rec['tone'] = 'educational'
                formatted_rec['description_style'] = 'detailed'
            
            # 添加多模态相关性说明
            formatted_rec['multimodal_relevance'] = self._explain_multimodal_relevance(
                rec, multimodal_analysis
            )
            
            formatted_recommendations.append(formatted_rec)
        
        return formatted_recommendations
    
    def _explain_multimodal_relevance(
        self,
        recommendation: Dict[str, Any],
        analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """解释多模态相关性"""
        relevance = {
            'visual_match': False,
            'voice_preference_match': False,
            'skin_analysis_match': False,
            'explanation': []
        }
        
        # 检查图像分析匹配
        image_factors = analysis.get('enhancement_factors', {}).get('image', {})
        if image_factors.get('has_analysis'):
            skin_insights = image_factors.get('skin_insights', {})
            for insights in skin_insights.values():
                focus_areas = insights.get('recommendation_focus', [])
                if any(area in recommendation.get('category', '').lower() for area in focus_areas):
                    relevance['skin_analysis_match'] = True
                    relevance['explanation'].append('基于您的肌肤分析结果推荐')
        
        # 检查语音偏好匹配
        voice_factors = analysis.get('enhancement_factors', {}).get('voice', {})
        if voice_factors.get('has_transcription'):
            emotional_indicators = voice_factors.get('emotional_indicators', {})
            if emotional_indicators.get('enthusiasm', 0) > 0.3:
                relevance['voice_preference_match'] = True
                relevance['explanation'].append('符合您表达的兴趣偏好')
        
        return relevance