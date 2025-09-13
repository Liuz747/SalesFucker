"""
情感分析智能体多模态增强模块

该模块为情感分析智能体提供多模态情感识别能力。
结合语音语调、面部表情和文本内容，提供更准确的情感分析。
重构后采用模块化设计，提高代码组织性和可维护性。

核心功能:
- 多模态情感融合分析
- 语音语调情感识别
- 面部表情情感检测
- 情感历史追踪和趋势分析
"""

from typing import Dict, Any, Optional

from utils import (
    get_current_datetime,
    LoggerMixin,
    InputType
)
from core.agents.sentiment.sentiment_analyzer import ChineseSentimentAnalyzer
from core.agents.sentiment.voice_emotion_analyzer import VoiceEmotionAnalyzer
from core.agents.sentiment.image_emotion_analyzer import ImageEmotionAnalyzer
from core.agents.sentiment.emotion_fusion import EmotionFusionManager


class MultimodalSentimentAnalyzer(LoggerMixin):
    """
    多模态情感分析器
    
    融合文本、语音和图像信息进行综合情感分析。
    提供更准确的客户情感状态评估。
    
    属性:
        tenant_id: 租户标识符
        text_analyzer: 文本情感分析器
        voice_analyzer: 语音情感分析器
        image_analyzer: 图像情感分析器
        fusion_manager: 情感融合管理器
    """
    
    def __init__(self, tenant_id: str):
        """
        初始化多模态情感分析器
        
        Args:
            tenant_id: 租户标识符
        """
        super().__init__()
        self.tenant_id = tenant_id
        
        # 初始化各模态分析器
        self.text_analyzer = ChineseSentimentAnalyzer()
        self.voice_analyzer = VoiceEmotionAnalyzer()
        self.image_analyzer = ImageEmotionAnalyzer()
        
        # 初始化融合管理器
        self.fusion_manager = EmotionFusionManager(tenant_id)
        
        self.logger.info(f"多模态情感分析器已初始化: {tenant_id}")
    
    async def analyze_multimodal_sentiment(
        self,
        message_context: Dict[str, Any],
        customer_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        多模态情感分析
        
        Args:
            message_context: 消息上下文，包含多模态数据
            customer_id: 客户标识符
            
        Returns:
            综合情感分析结果
        """
        input_type = message_context.get('input_type', InputType.TEXT)
        
        # 分析各模态的情感
        text_sentiment = await self._analyze_text_sentiment(message_context)
        voice_sentiment = await self._analyze_voice_sentiment(message_context)
        image_sentiment = await self._analyze_image_sentiment(message_context)
        
        # 融合多模态情感分析
        combined_sentiment = self.fusion_manager.combine_sentiments(
            text_sentiment, voice_sentiment, image_sentiment, input_type
        )
        
        # 生成情感洞察
        sentiment_insights = await self._generate_sentiment_insights(
            combined_sentiment, customer_id
        )
        
        # 更新情感历史
        if customer_id:
            self.fusion_manager.update_emotion_history(customer_id, combined_sentiment)
        
        result = {
            'overall_sentiment': combined_sentiment,
            'modality_breakdown': {
                'text': text_sentiment,
                'voice': voice_sentiment,
                'image': image_sentiment
            },
            'sentiment_insights': sentiment_insights,
            'confidence': combined_sentiment.get('confidence', 0.5),
            'timestamp': get_current_datetime()
        }
        
        self.logger.debug(f"多模态情感分析完成: {combined_sentiment.get('primary_emotion', 'neutral')}")
        
        return result
    
    async def _analyze_text_sentiment(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """分析文本情感"""
        sentiment = {
            'primary_emotion': 'neutral',
            'emotions': {},
            'confidence': 0.5,
            'indicators': []
        }
        
        try:
            # 获取文本内容
            text_sources = self._collect_text_sources(context)
            
            if not text_sources:
                return sentiment
            
            # 分析组合文本
            combined_text = ' '.join(text_sources).lower()
            
            # 词汇情感分析
            sentiment['emotions'] = self.text_analyzer.analyze_text_sentiment(combined_text)
            
            # 确定主要情感
            sentiment['primary_emotion'] = self.text_analyzer.determine_primary_emotion(sentiment['emotions'])
            
            # 计算置信度
            sentiment['confidence'] = self.text_analyzer.calculate_confidence(sentiment['emotions'])
            
            # 提取情感指标
            sentiment['indicators'] = self.text_analyzer.extract_emotion_indicators(combined_text)
            
        except Exception as e:
            self.logger.warning(f"文本情感分析失败: {e}")
        
        return sentiment
    
    async def _analyze_voice_sentiment(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """分析语音情感"""
        try:
            transcriptions = context.get('transcriptions', [])
            if not transcriptions:
                return self._get_default_voice_sentiment()
            
            return self.voice_analyzer.analyze_voice_sentiment(transcriptions)
            
        except Exception as e:
            self.logger.warning(f"语音情感分析失败: {e}")
            return self._get_default_voice_sentiment()
    
    async def _analyze_image_sentiment(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """分析图像情感"""
        try:
            image_analysis = context.get('image_analysis', {})
            if not image_analysis:
                return self._get_default_image_sentiment()
            
            return self.image_analyzer.analyze_image_sentiment(image_analysis)
            
        except Exception as e:
            self.logger.warning(f"图像情感分析失败: {e}")
            return self._get_default_image_sentiment()
    
    def _collect_text_sources(self, context: Dict[str, Any]) -> list:
        """收集文本数据源"""
        text_sources = []
        
        # 原始文本
        original_text = context.get('payload', {}).get('message', '')
        if original_text:
            text_sources.append(original_text)
        
        # 转录文本
        transcriptions = context.get('transcriptions', [])
        text_sources.extend(transcriptions)
        
        # 组合内容
        combined_content = context.get('combined_content', '')
        if combined_content:
            text_sources.append(combined_content)
        
        return text_sources
    
    def _get_default_voice_sentiment(self) -> Dict[str, Any]:
        """获取默认语音情感结果"""
        return {
            'primary_emotion': 'neutral',
            'emotions': {
                'excitement': 0.0,
                'concern': 0.0,
                'hesitation': 0.0,
                'satisfaction': 0.0
            },
            'confidence': 0.0,
            'voice_patterns': [],
            'prosodic_features': {}
        }
    
    def _get_default_image_sentiment(self) -> Dict[str, Any]:
        """获取默认图像情感结果"""
        return {
            'primary_emotion': 'neutral',
            'emotions': {
                'positive': 0.0,
                'concern': 0.0,
                'confidence': 0.0,
                'satisfaction': 0.0
            },
            'confidence': 0.0,
            'facial_analysis': {},
            'visual_cues': []
        }
    
    async def _generate_sentiment_insights(
        self,
        combined_sentiment: Dict[str, Any],
        customer_id: Optional[str]
    ) -> Dict[str, Any]:
        """生成情感洞察"""
        insights = {
            'emotional_state': 'neutral',
            'engagement_level': 'medium',
            'recommendation_tone': 'standard',
            'interaction_suggestions': [],
            'emotion_trends': []
        }
        
        primary_emotion = combined_sentiment.get('primary_emotion', 'neutral')
        intensity = combined_sentiment.get('emotional_intensity', 0)
        
        # 确定情感状态和建议
        insights.update(self._determine_emotional_state(primary_emotion))
        
        # 生成交互建议
        insights['interaction_suggestions'] = self.fusion_manager.generate_interaction_suggestions(
            primary_emotion, intensity
        )
        
        # 获取情感趋势（如果有历史数据）
        if customer_id and customer_id in self.fusion_manager.emotion_history:
            insights['emotion_trends'] = self.fusion_manager.analyze_emotion_trends(customer_id)
        
        return insights
    
    def _determine_emotional_state(self, primary_emotion: str) -> Dict[str, str]:
        """确定情感状态和推荐语调"""
        if primary_emotion in ['positive', 'enthusiasm', 'satisfaction']:
            return {
                'emotional_state': 'positive',
                'engagement_level': 'high',
                'recommendation_tone': 'enthusiastic'
            }
        elif primary_emotion in ['negative', 'concern']:
            return {
                'emotional_state': 'concerned',
                'engagement_level': 'medium',
                'recommendation_tone': 'reassuring'
            }
        elif primary_emotion in ['hesitation']:
            return {
                'emotional_state': 'uncertain',
                'engagement_level': 'low',
                'recommendation_tone': 'educational'
            }
        else:
            return {
                'emotional_state': 'neutral',
                'engagement_level': 'medium',
                'recommendation_tone': 'standard'
            }
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        return {
            'status': 'healthy',
            'service': 'multimodal_sentiment_analyzer',
            'tenant_id': self.tenant_id,
            'statistics': {
                'tracked_customers': len(self.fusion_manager.emotion_history),
                'sentiment_weights': self.fusion_manager.sentiment_weights,
                'analyzers_status': {
                    'text_analyzer': 'active',
                    'voice_analyzer': 'active',
                    'image_analyzer': 'active'
                }
            },
            'timestamp': get_current_datetime()
        }