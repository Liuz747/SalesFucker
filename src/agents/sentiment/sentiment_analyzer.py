"""
情感分析核心模块

该模块提供文本情感分析的核心功能。
包含中文情感词典和情感识别算法。

核心功能:
- 中文情感词典管理
- 文本情感分析
- 情感强度计算
- 情感指标提取
"""

from typing import Dict, List, Set


class ChineseSentimentAnalyzer:
    """
    中文情感分析器
    
    基于词典的中文情感分析工具。
    支持多种情感类别的识别和量化。
    
    属性:
        positive_words: 正面情感词汇
        negative_words: 负面情感词汇
        concern_words: 担心情感词汇
        enthusiasm_words: 热情情感词汇
    """
    
    def __init__(self):
        self._load_sentiment_dictionaries()
    
    def _load_sentiment_dictionaries(self):
        """加载情感词典"""
        # 中文情感词典
        self.positive_words: Set[str] = {
            '喜欢', '爱', '好', '棒', '完美', '满意', '开心', '高兴', '兴奋',
            '惊喜', '赞', '优秀', '不错', '很好', '太好了', '喜爱', '心动'
        }
        
        self.negative_words: Set[str] = {
            '不好', '差', '失望', '讨厌', '烦', '糟糕', '难受', '郭闷',
            '生气', '愤怒', '沉丧', '伤心', '难过', '不满', '抱怨'
        }
        
        self.concern_words: Set[str] = {
            '担心', '焦虑', '紧张', '害怕', '不安', '忧虑', '疑虑', '顾虑',
            '犹豫', '纠结', '困扰', '问题', '麻烦', '困难'
        }
        
        self.enthusiasm_words: Set[str] = {
            '想要', '渴望', '期待', '迫不及待', '激动', '兴奋', '热情',
            '积极', '主动', '热切', '急需', '立即', '马上'
        }
    
    def analyze_text_sentiment(self, text: str) -> Dict[str, float]:
        """
        分析文本情感
        
        Args:
            text: 要分析的文本
            
        Returns:
            各种情感的得分
        """
        emotions = {
            'positive': 0.0,
            'negative': 0.0,
            'concern': 0.0,
            'enthusiasm': 0.0
        }
        
        # 统计情感词汇
        words = set(text.lower().split())
        text_length = len(text)
        
        if text_length == 0:
            return emotions
        
        # 正面情感
        positive_count = len(words.intersection(self.positive_words))
        emotions['positive'] = positive_count / text_length * 10
        
        # 负面情感
        negative_count = len(words.intersection(self.negative_words))
        emotions['negative'] = negative_count / text_length * 10
        
        # 担心情感
        concern_count = len(words.intersection(self.concern_words))
        emotions['concern'] = concern_count / text_length * 10
        
        # 热情情感
        enthusiasm_count = len(words.intersection(self.enthusiasm_words))
        emotions['enthusiasm'] = enthusiasm_count / text_length * 10
        
        return emotions
    
    def determine_primary_emotion(self, emotions: Dict[str, float]) -> str:
        """确定主要情感"""
        if not emotions:
            return 'neutral'
        
        max_emotion = max(emotions.items(), key=lambda x: x[1])
        
        if max_emotion[1] > 0.2:
            return max_emotion[0]
        else:
            return 'neutral'
    
    def calculate_confidence(self, emotions: Dict[str, float]) -> float:
        """计算情感置信度"""
        total_intensity = sum(emotions.values())
        if total_intensity == 0:
            return 0.5  # 中性置信度
        
        # 归一化置信度
        max_intensity = max(emotions.values())
        confidence = min(max_intensity * 2, 1.0)
        
        return confidence
    
    def extract_emotion_indicators(self, text: str) -> List[str]:
        """提取情感指标"""
        indicators = []
        
        # 检测标点符号情感
        if '!' in text:
            indicators.append('exclamation')
        if '？' in text or '?' in text:
            indicators.append('questioning')
        if '...' in text:
            indicators.append('hesitation')
        
        # 检测重复词汇
        words = text.split()
        if len(set(words)) < len(words) * 0.8:  # 有重复词汇
            indicators.append('repetition')
        
        return indicators