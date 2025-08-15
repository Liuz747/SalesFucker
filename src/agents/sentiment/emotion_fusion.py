"""
情感融合和历史管理模块

该模块负责将多模态情感分析结果进行融合。
同时管理用户情感历史和生成交互建议。

核心功能:
- 多模态情感融合
- 情感历史管理
- 交互建议生成
- 情感趋势分析
"""

from typing import Dict, Any, List, Optional
from utils import get_current_datetime, InputType


class EmotionFusionManager:
    """
    情感融合管理器
    
    统一管理多模态情感融合、历史记录和交互建议。
    提供智能化的情感综合分析结果。
    
    属性:
        sentiment_weights: 不同模态的权重配置
        emotion_history: 用户情感历史记录
    """
    
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        
        # 情感权重配置
        self.sentiment_weights = {
            'text': 0.4,
            'voice': 0.35,
            'image': 0.25
        }
        
        # 情感历史记录
        self.emotion_history = {}
    
    def combine_sentiments(
        self,
        text_sentiment: Dict[str, Any],
        voice_sentiment: Dict[str, Any],
        image_sentiment: Dict[str, Any],
        input_type: str
    ) -> Dict[str, Any]:
        """
        融合多模态情感分析结果
        
        Args:
            text_sentiment: 文本情感分析结果
            voice_sentiment: 语音情感分析结果
            image_sentiment: 图像情感分析结果
            input_type: 输入类型
            
        Returns:
            融合后的情感分析结果
        """
        combined = {
            'primary_emotion': 'neutral',
            'emotion_scores': {},
            'confidence': 0.5,
            'modality_contributions': {},
            'emotional_intensity': 0.0
        }
        
        # 根据输入类型调整权重
        weights = self._adjust_weights_by_input_type(input_type)
        
        # 融合情感分数
        all_emotions = self._collect_all_emotions(text_sentiment, voice_sentiment, image_sentiment)
        
        for emotion in all_emotions:
            text_score = text_sentiment.get('emotions', {}).get(emotion, 0)
            voice_score = voice_sentiment.get('emotions', {}).get(emotion, 0)
            image_score = image_sentiment.get('emotions', {}).get(emotion, 0)
            
            combined_score = (
                text_score * weights['text'] +
                voice_score * weights['voice'] +
                image_score * weights['image']
            )
            
            combined['emotion_scores'][emotion] = combined_score
        
        # 确定主要情感
        if combined['emotion_scores']:
            primary_emotion = max(combined['emotion_scores'].items(), key=lambda x: x[1])
            if primary_emotion[1] > 0.1:
                combined['primary_emotion'] = primary_emotion[0]
                combined['emotional_intensity'] = primary_emotion[1]
        
        # 计算综合置信度
        text_conf = text_sentiment.get('confidence', 0) * weights['text']
        voice_conf = voice_sentiment.get('confidence', 0) * weights['voice']
        image_conf = image_sentiment.get('confidence', 0) * weights['image']
        
        combined['confidence'] = text_conf + voice_conf + image_conf
        
        # 记录各模态贡献
        combined['modality_contributions'] = weights
        
        return combined
    
    def _adjust_weights_by_input_type(self, input_type: str) -> Dict[str, float]:
        """根据输入类型调整权重"""
        weights = self.sentiment_weights.copy()
        
        if input_type == InputType.VOICE:
            weights['voice'] *= 1.5
            weights['text'] *= 0.8
        elif input_type == InputType.IMAGE:
            weights['image'] *= 1.5
            weights['text'] *= 0.8
        elif input_type == InputType.MULTIMODAL:
            # 多模态时使用默认权重
            pass
        
        # 归一化权重
        total_weight = sum(weights.values())
        for key in weights:
            weights[key] /= total_weight
        
        return weights
    
    def _collect_all_emotions(self, text_sentiment: Dict[str, Any], voice_sentiment: Dict[str, Any], image_sentiment: Dict[str, Any]) -> set:
        """收集所有情感类型"""
        all_emotions = set()
        all_emotions.update(text_sentiment.get('emotions', {}).keys())
        all_emotions.update(voice_sentiment.get('emotions', {}).keys())
        all_emotions.update(image_sentiment.get('emotions', {}).keys())
        return all_emotions
    
    def generate_interaction_suggestions(self, primary_emotion: str, intensity: float) -> List[str]:
        """生成交互建议"""
        suggestions = []
        
        if primary_emotion == 'positive':
            suggestions.extend([
                '保持积极的推荐语调',
                '可以推荐更多相关产品',
                '分享产品使用技巧'
            ])
        elif primary_emotion == 'concern':
            suggestions.extend([
                '使用安抚性语言',
                '提供详细的产品信息',
                '推荐温和、安全的产品'
            ])
        elif primary_emotion == 'hesitation':
            suggestions.extend([
                '提供教育性内容',
                '给出具体的使用指导',
                '减少选择复杂度'
            ])
        elif primary_emotion == 'enthusiasm':
            suggestions.extend([
                '快速响应客户需求',
                '提供热门产品推荐',
                '分享最新美容趋势'
            ])
        
        if intensity > 0.7:
            suggestions.append('情感强度较高，需要特别关注')
        
        return suggestions
    
    def update_emotion_history(self, customer_id: str, sentiment: Dict[str, Any]):
        """更新情感历史"""
        if customer_id not in self.emotion_history:
            self.emotion_history[customer_id] = []
        
        emotion_record = {
            'timestamp': get_current_datetime(),
            'primary_emotion': sentiment.get('primary_emotion', 'neutral'),
            'intensity': sentiment.get('emotional_intensity', 0),
            'confidence': sentiment.get('confidence', 0.5)
        }
        
        self.emotion_history[customer_id].append(emotion_record)
        
        # 只保留最近20条记录
        if len(self.emotion_history[customer_id]) > 20:
            self.emotion_history[customer_id] = self.emotion_history[customer_id][-20:]
    
    def analyze_emotion_trends(self, customer_id: str) -> List[Dict[str, Any]]:
        """分析情感趋势"""
        history = self.emotion_history.get(customer_id, [])
        if len(history) < 3:
            return []
        
        trends = []
        
        # 分析最近的情感变化
        recent_emotions = [record['primary_emotion'] for record in history[-5:]]
        
        if len(set(recent_emotions)) == 1:
            trends.append({
                'trend_type': 'stable',
                'description': f'情感状态稳定：{recent_emotions[0]}'
            })
        elif recent_emotions[-1] != recent_emotions[0]:
            trends.append({
                'trend_type': 'changing',
                'description': f'情感从 {recent_emotions[0]} 变化到 {recent_emotions[-1]}'
            })
        
        # 分析情感强度趋势
        recent_intensities = [record['intensity'] for record in history[-3:]]
        if len(recent_intensities) >= 2:
            if recent_intensities[-1] > recent_intensities[0]:
                trends.append({
                    'trend_type': 'intensifying',
                    'description': '情感强度呈上升趋势'
                })
            elif recent_intensities[-1] < recent_intensities[0]:
                trends.append({
                    'trend_type': 'calming',
                    'description': '情感强度呈下降趋势'
                })
        
        return trends