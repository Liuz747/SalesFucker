"""
图像情感分析模块

该模块专门处理图像中的情感信息提取。
从皮肤分析、产品识别和图像描述中推断情感状态。

核心功能:
- 皮肤分析情感推断
- 产品兴趣度分析
- 图像描述情感识别
- 视觉线索提取
"""

from typing import Dict, Any, List


class ImageEmotionAnalyzer:
    """
    图像情感分析器
    
    从图像分析结果中推断用户的情感状态。
    主要通过皮肤状态、产品兴趣和视觉线索进行分析。
    
    属性:
        emotion_keywords: 情感关键词词典
    """
    
    def __init__(self):
        self._load_emotion_keywords()
    
    def _load_emotion_keywords(self):
        """加载情感关键词"""
        self.emotion_keywords = {
            'positive': ['good', 'nice', 'beautiful', '好', '美', '满意', '健康'],
            'concern': ['problem', 'issue', 'concern', '问题', '担心', '缺陷', '问题'],
            'interest': ['want', 'like', 'interested', '想要', '喜欢', '感兴趣'],
            'satisfaction': ['satisfied', 'happy', 'pleased', '满意', '开心', '高兴']
        }
    
    def analyze_image_sentiment(self, image_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析图像情感
        
        Args:
            image_analysis: 图像分析结果
            
        Returns:
            图像情感分析结果
        """
        sentiment = {
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
        
        if not image_analysis:
            return sentiment
        
        # 分析图像中的情感线索
        for attachment_id, analysis_data in image_analysis.items():
            results = analysis_data.get('results', {})
            
            # 从皮肤分析推断情感状态
            if 'skin_concerns' in results:
                sentiment = self._infer_emotion_from_skin_analysis(sentiment, results)
            
            # 从产品识别推断兴趣度
            if 'products' in results:
                sentiment = self._infer_emotion_from_product_interest(sentiment, results)
            
            # 从通用分析推断情感
            if 'overall_description' in results:
                sentiment = self._infer_emotion_from_description(sentiment, results)
        
        # 确定主要情感
        if sentiment['emotions']:
            max_emotion = max(sentiment['emotions'].items(), key=lambda x: x[1])
            if max_emotion[1] > 0.1:
                sentiment['primary_emotion'] = max_emotion[0]
                sentiment['confidence'] = max_emotion[1]
        
        return sentiment
    
    def _infer_emotion_from_skin_analysis(self, sentiment: Dict[str, Any], results: Dict[str, Any]) -> Dict[str, Any]:
        """从皮肤分析推断情感"""
        skin_concerns = results.get('skin_concerns', [])
        
        if skin_concerns:
            # 有皮肤问题可能表示担心
            concern_level = len(skin_concerns) / 5.0  # 最多5个问题
            sentiment['emotions']['concern'] = min(concern_level, 1.0)
            sentiment['visual_cues'].append('skin_concerns_detected')
        else:
            # 无明显问题可能表示满意
            sentiment['emotions']['satisfaction'] = 0.7
            sentiment['visual_cues'].append('good_skin_condition')
        
        return sentiment
    
    def _infer_emotion_from_product_interest(self, sentiment: Dict[str, Any], results: Dict[str, Any]) -> Dict[str, Any]:
        """从产品兴趣推断情感"""
        products = results.get('products', [])
        
        if products:
            # 产品识别表示积极兴趣
            interest_level = len(products) / 3.0  # 最多3个产品
            sentiment['emotions']['positive'] = min(interest_level, 1.0)
            sentiment['visual_cues'].append('product_interest_shown')
        
        return sentiment
    
    def _infer_emotion_from_description(self, sentiment: Dict[str, Any], results: Dict[str, Any]) -> Dict[str, Any]:
        """从描述推断情感"""
        description = results.get('overall_description', '').lower()
        
        # 简单的情感词汇检测
        for emotion_type, keywords in self.emotion_keywords.items():
            for keyword in keywords:
                if keyword.lower() in description:
                    if emotion_type in sentiment['emotions']:
                        sentiment['emotions'][emotion_type] += 0.3
                    elif emotion_type == 'interest':
                        sentiment['emotions']['positive'] += 0.3
        
        return sentiment