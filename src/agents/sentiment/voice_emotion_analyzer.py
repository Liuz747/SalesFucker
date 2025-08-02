"""
语音情感分析模块

该模块专门处理语音信号中的情感识别。
基于韵律特征和转写文本分析语音情感。

核心功能:
- 语音情感指标识别
- 韵律特征分析
- 转写文本情感提取
- 语音情感融合
"""

from typing import Dict, List, Any


class VoiceEmotionAnalyzer:
    """
    语音情感分析器
    
    专门处理语音信号中的情感特征。
    结合韵律特征和转写文本进行综合分析。
    
    属性:
        voice_emotion_indicators: 语音情感指标词典
    """
    
    def __init__(self):
        self._load_voice_indicators()
    
    def _load_voice_indicators(self):
        """加载语音情感指标"""
        self.voice_emotion_indicators = {
            'excitement': ['太好了', '哇', '真的吗', '太棒了', 'amazing'],
            'concern': ['嗯...', '但是', '不过', '怎么办', '会不会'],
            'hesitation': ['这个...', '那个...', '可能', '也许', '不确定'],
            'satisfaction': ['很好', '满意', '不错', '可以', '正好'],
            'dissatisfaction': ['不行', '不好', '不对', '不合适', '不满意']
        }
    
    def analyze_voice_sentiment(self, transcriptions: List[str]) -> Dict[str, Any]:
        """
        分析语音情感
        
        Args:
            transcriptions: 转写文本列表
            
        Returns:
            语音情感分析结果
        """
        sentiment = {
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
        
        if not transcriptions:
            return sentiment
        
        # 分析转写文本中的语音情感指标
        combined_transcription = ' '.join(transcriptions).lower()
        
        # 检测语音情感模式
        for emotion, indicators in self.voice_emotion_indicators.items():
            count = sum(1 for indicator in indicators if indicator in combined_transcription)
            if count > 0:
                sentiment['emotions'][emotion] = count / len(combined_transcription) * 20
                sentiment['voice_patterns'].append(emotion)
        
        # 分析韵律特征（基于转写文本的简化分析）
        sentiment['prosodic_features'] = self._analyze_prosodic_features(combined_transcription)
        
        # 确定主要情感
        if sentiment['emotions']:
            max_emotion = max(sentiment['emotions'].items(), key=lambda x: x[1])
            if max_emotion[1] > 0.1:
                sentiment['primary_emotion'] = max_emotion[0]
                sentiment['confidence'] = min(max_emotion[1] * 2, 1.0)
        
        return sentiment
    
    def _analyze_prosodic_features(self, text: str) -> Dict[str, Any]:
        """分析韵律特征（基于文本的简化版本）"""
        features = {
            'speech_rate': 'normal',
            'emphasis_level': 'medium',
            'pause_patterns': []
        }
        
        # 基于文本长度和标点推断语速
        words_count = len(text.split())
        punctuation_count = sum(1 for char in text if char in '，。！？,.!?')
        
        if punctuation_count / max(words_count, 1) > 0.3:
            features['speech_rate'] = 'slow'
        elif words_count > 50:
            features['speech_rate'] = 'fast'
        
        # 基于标点推断强调程度
        if '!' in text or '！' in text:
            features['emphasis_level'] = 'high'
        elif '...' in text:
            features['emphasis_level'] = 'low'
        
        return features