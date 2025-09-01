"""
GPT-4V图像分析服务

该模块提供基于OpenAI GPT-4V的图像分析服务。
支持皮肤分析、产品识别和通用图像理解。

核心功能:
- GPT-4V API集成和调用
- 图像编码和上传处理
- 中英文双语分析结果
- 置信度评估和结果验证
"""

import asyncio
import aiofiles
import base64
from typing import Dict, Any, Optional, List
from datetime import datetime
import openai
from pathlib import Path

from utils import (
    get_current_datetime,
    get_processing_time_ms,
    LoggerMixin,
    with_error_handling,
    MultiModalConstants,
    ProcessingType
)


class GPT4VService(LoggerMixin):
    """
    GPT-4V图像分析服务类
    
    提供基于OpenAI GPT-4V的图像分析能力。
    支持多种分析类型和中英文输出。
    
    属性:
        client: OpenAI客户端
        timeout: 处理超时时间
        max_image_size: 最大图像尺寸
    """
    
    def __init__(self, api_key: str):
        """
        初始化GPT-4V服务
        
        Args:
            api_key: OpenAI API密钥
        """
        super().__init__()
        self.client = openai.AsyncOpenAI(api_key=api_key)
        self.timeout = MultiModalConstants.IMAGE_PROCESSING_TIMEOUT / 1000  # 转换为秒
        self.max_image_size = MultiModalConstants.MAX_IMAGE_SIZE
        
        self.logger.info("GPT-4V图像分析服务已初始化")
    
    @with_error_handling()
    async def analyze_skin(self, image_path: str, language: str = 'zh') -> Dict[str, Any]:
        """
        分析皮肤状态
        
        Args:
            image_path: 图像文件路径
            language: 输出语言（zh/en）
            
        Returns:
            皮肤分析结果
        """
        start_time = datetime.now()
        self.logger.info(f"开始皮肤分析: {image_path}")
        
        try:
            # 构建皮肤分析提示词
            prompt = self._build_skin_analysis_prompt(language)
            
            # 调用GPT-4V分析
            analysis_result = await self._analyze_image_with_prompt(image_path, prompt)
            
            # 处理皮肤分析结果
            processed_result = self._process_skin_analysis_result(analysis_result, language)
            
            processing_time = get_processing_time_ms(start_time)
            processed_result['processing_time_ms'] = processing_time
            processed_result['analysis_type'] = ProcessingType.SKIN_ANALYSIS
            
            self.logger.info(
                f"皮肤分析完成: {image_path}, "
                f"耗时: {processing_time}ms, "
                f"识别问题数: {len(processed_result.get('skin_concerns', []))}"
            )
            
            return processed_result
            
        except Exception as e:
            self.logger.error(f"皮肤分析失败: {image_path}, 错误: {e}")
            raise
    
    @with_error_handling()
    async def recognize_product(self, image_path: str, language: str = 'zh') -> Dict[str, Any]:
        """
        识别化妆品产品
        
        Args:
            image_path: 图像文件路径
            language: 输出语言（zh/en）
            
        Returns:
            产品识别结果
        """
        start_time = datetime.now()
        self.logger.info(f"开始产品识别: {image_path}")
        
        try:
            # 构建产品识别提示词
            prompt = self._build_product_recognition_prompt(language)
            
            # 调用GPT-4V分析
            analysis_result = await self._analyze_image_with_prompt(image_path, prompt)
            
            # 处理产品识别结果
            processed_result = self._process_product_recognition_result(analysis_result, language)
            
            processing_time = get_processing_time_ms(start_time)
            processed_result['processing_time_ms'] = processing_time
            processed_result['analysis_type'] = ProcessingType.PRODUCT_RECOGNITION
            
            self.logger.info(
                f"产品识别完成: {image_path}, "
                f"耗时: {processing_time}ms, "
                f"识别产品数: {len(processed_result.get('products', []))}"
            )
            
            return processed_result
            
        except Exception as e:
            self.logger.error(f"产品识别失败: {image_path}, 错误: {e}")
            raise
    
    @with_error_handling()
    async def analyze_general(self, image_path: str, language: str = 'zh') -> Dict[str, Any]:
        """
        通用图像分析
        
        Args:
            image_path: 图像文件路径
            language: 输出语言（zh/en）
            
        Returns:
            通用分析结果
        """
        start_time = datetime.now()
        self.logger.info(f"开始通用图像分析: {image_path}")
        
        try:
            # 构建通用分析提示词
            prompt = self._build_general_analysis_prompt(language)
            
            # 调用GPT-4V分析
            analysis_result = await self._analyze_image_with_prompt(image_path, prompt)
            
            # 处理通用分析结果
            processed_result = self._process_general_analysis_result(analysis_result, language)
            
            processing_time = get_processing_time_ms(start_time)
            processed_result['processing_time_ms'] = processing_time
            processed_result['analysis_type'] = ProcessingType.IMAGE_ANALYSIS
            
            self.logger.info(
                f"通用图像分析完成: {image_path}, "
                f"耗时: {processing_time}ms"
            )
            
            return processed_result
            
        except Exception as e:
            self.logger.error(f"通用图像分析失败: {image_path}, 错误: {e}")
            raise
    
    async def _analyze_image_with_prompt(self, image_path: str, prompt: str) -> str:
        """
        使用提示词分析图像
        
        Args:
            image_path: 图像路径
            prompt: 分析提示词
            
        Returns:
            GPT-4V响应文本
        """
        try:
            # 编码图像
            base64_image = await self._encode_image(image_path)
            
            # 构建消息
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}",
                                "detail": "high"
                            }
                        }
                    ]
                }
            ]
            
            # 调用GPT-4V API
            response = await asyncio.wait_for(
                self.client.chat.completions.create(
                    model="gpt-4-vision-preview",
                    messages=messages,
                    max_tokens=1000,
                    temperature=0.1  # 降低随机性提高一致性
                ),
                timeout=self.timeout
            )
            
            return response.choices[0].message.content
            
        except asyncio.TimeoutError:
            raise Exception(f"图像分析超时（{self.timeout}秒）")
        except Exception as e:
            raise Exception(f"GPT-4V API调用失败: {e}")
    
    async def _encode_image(self, image_path: str) -> str:
        """
        编码图像为base64
        
        Args:
            image_path: 图像路径
            
        Returns:
            base64编码字符串
        """
        try:
            async with aiofiles.open(image_path, "rb") as image_file:
                image_data = await image_file.read()
                return base64.b64encode(image_data).decode('utf-8')
        except Exception as e:
            raise Exception(f"图像编码失败: {e}")
    
    def _build_skin_analysis_prompt(self, language: str) -> str:
        """构建皮肤分析提示词"""
        if language == 'en':
            return """Please analyze this facial image for skincare assessment. Provide detailed analysis in the following JSON format:

{
    "skin_concerns": [
        {
            "type": "concern_type",
            "severity": "mild/moderate/severe",
            "location": "area_description",
            "description": "detailed_description",
            "confidence": 0.0-1.0
        }
    ],
    "skin_type": "dry/oily/combination/sensitive/normal",
    "skin_tone": "fair/medium/dark",
    "visible_issues": ["acne", "wrinkles", "dark_spots", "dryness", "oiliness"],
    "recommendations": [
        {
            "category": "product_category",
            "action": "specific_recommendation",
            "priority": "high/medium/low"
        }
    ],
    "overall_condition": "description",
    "confidence_score": 0.0-1.0,
    "analysis_notes": "additional_observations"
}

Focus on visible skin characteristics, concerns, and provide actionable skincare recommendations."""
        else:
            return """请分析这张面部图像进行护肤评估。请以以下JSON格式提供详细分析：

{
    "skin_concerns": [
        {
            "type": "问题类型",
            "severity": "轻微/中等/严重",
            "location": "区域描述",
            "description": "详细描述",
            "confidence": 0.0-1.0
        }
    ],
    "skin_type": "干性/油性/混合性/敏感性/中性",
    "skin_tone": "浅色/中等色/深色",
    "visible_issues": ["痘痘", "皱纹", "色斑", "干燥", "出油"],
    "recommendations": [
        {
            "category": "产品类别",
            "action": "具体建议",
            "priority": "高/中/低"
        }
    ],
    "overall_condition": "整体状况描述",
    "confidence_score": 0.0-1.0,
    "analysis_notes": "额外观察"
}

重点关注可见的皮肤特征、问题，并提供可行的护肤建议。"""
    
    def _build_product_recognition_prompt(self, language: str) -> str:
        """构建产品识别提示词"""
        if language == 'en':
            return """Please identify and analyze cosmetic/beauty products in this image. Provide detailed information in the following JSON format:

{
    "products": [
        {
            "name": "product_name",
            "brand": "brand_name",
            "category": "product_category",
            "type": "specific_type",
            "description": "product_description",
            "visible_features": ["feature1", "feature2"],
            "confidence": 0.0-1.0,
            "location": "position_in_image"
        }
    ],
    "product_count": 0,
    "main_categories": ["skincare", "makeup", "tools"],
    "overall_assessment": "general_description",
    "confidence_score": 0.0-1.0,
    "analysis_notes": "additional_observations"
}

Focus on identifying specific cosmetic products, brands, and providing useful product information."""
        else:
            return """请识别和分析图像中的化妆品/美容产品。请以以下JSON格式提供详细信息：

{
    "products": [
        {
            "name": "产品名称",
            "brand": "品牌名称", 
            "category": "产品类别",
            "type": "具体类型",
            "description": "产品描述",
            "visible_features": ["特征1", "特征2"],
            "confidence": 0.0-1.0,
            "location": "在图像中的位置"
        }
    ],
    "product_count": 0,
    "main_categories": ["护肤品", "彩妆", "工具"],
    "overall_assessment": "整体评价",
    "confidence_score": 0.0-1.0,
    "analysis_notes": "额外观察"
}

重点识别具体的化妆品产品、品牌，并提供有用的产品信息。"""
    
    def _build_general_analysis_prompt(self, language: str) -> str:
        """构建通用分析提示词"""
        if language == 'en':
            return """Please analyze this image in the context of beauty and cosmetics. Provide comprehensive analysis in the following JSON format:

{
    "image_type": "selfie/product_photo/makeup_look/skincare_routine",
    "main_subjects": ["subject1", "subject2"],
    "beauty_context": "context_description",
    "key_observations": [
        {
            "observation": "what_you_see",
            "relevance": "beauty_relevance",
            "confidence": 0.0-1.0
        }
    ],
    "suggested_analysis_types": ["skin_analysis", "product_recognition", "makeup_assessment"],
    "overall_description": "comprehensive_description",
    "confidence_score": 0.0-1.0,
    "analysis_notes": "additional_insights"
}

Focus on beauty and cosmetic-related aspects of the image."""
        else:
            return """请在美容和化妆品的背景下分析这张图像。请以以下JSON格式提供综合分析：

{
    "image_type": "自拍/产品照片/妆容展示/护肤过程",
    "main_subjects": ["主题1", "主题2"],
    "beauty_context": "美容背景描述",
    "key_observations": [
        {
            "observation": "观察到的内容",
            "relevance": "美容相关性",
            "confidence": 0.0-1.0
        }
    ],
    "suggested_analysis_types": ["皮肤分析", "产品识别", "妆容评估"],
    "overall_description": "综合描述",
    "confidence_score": 0.0-1.0,
    "analysis_notes": "额外见解"
}

重点关注图像中与美容和化妆品相关的方面。"""
    
    def _process_skin_analysis_result(self, raw_result: str, language: str) -> Dict[str, Any]:
        """处理皮肤分析结果"""
        try:
            import json
            import re
            
            # 尝试提取JSON
            json_match = re.search(r'\{.*\}', raw_result, re.DOTALL)
            if json_match:
                result_data = json.loads(json_match.group())
            else:
                # 降级到文本解析
                result_data = self._parse_text_result(raw_result, 'skin_analysis')
            
            # 标准化和验证结果
            return self._standardize_skin_result(result_data, language)
            
        except Exception as e:
            self.logger.warning(f"结果解析失败，使用降级方案: {e}")
            return self._create_fallback_skin_result(raw_result, language)
    
    def _process_product_recognition_result(self, raw_result: str, language: str) -> Dict[str, Any]:
        """处理产品识别结果"""
        try:
            import json
            import re
            
            # 尝试提取JSON
            json_match = re.search(r'\{.*\}', raw_result, re.DOTALL)
            if json_match:
                result_data = json.loads(json_match.group())
            else:
                # 降级到文本解析
                result_data = self._parse_text_result(raw_result, 'product_recognition')
            
            # 标准化和验证结果
            return self._standardize_product_result(result_data, language)
            
        except Exception as e:
            self.logger.warning(f"结果解析失败，使用降级方案: {e}")
            return self._create_fallback_product_result(raw_result, language)
    
    def _process_general_analysis_result(self, raw_result: str, language: str) -> Dict[str, Any]:
        """处理通用分析结果"""
        try:
            import json
            import re
            
            # 尝试提取JSON
            json_match = re.search(r'\{.*\}', raw_result, re.DOTALL)
            if json_match:
                result_data = json.loads(json_match.group())
            else:
                # 降级到文本解析
                result_data = self._parse_text_result(raw_result, 'general_analysis')
            
            # 标准化和验证结果
            return self._standardize_general_result(result_data, language)
            
        except Exception as e:
            self.logger.warning(f"结果解析失败，使用降级方案: {e}")
            return self._create_fallback_general_result(raw_result, language)
    
    def _standardize_skin_result(self, data: Dict[str, Any], language: str) -> Dict[str, Any]:
        """标准化皮肤分析结果"""
        return {
            'results': {
                'skin_concerns': data.get('skin_concerns', []),
                'skin_type': data.get('skin_type', '未知'),
                'skin_tone': data.get('skin_tone', '未知'),
                'visible_issues': data.get('visible_issues', []),
                'recommendations': data.get('recommendations', []),
                'overall_condition': data.get('overall_condition', ''),
                'analysis_notes': data.get('analysis_notes', '')
            },
            'confidence_scores': {
                'overall': data.get('confidence_score', 0.5),
                'skin_type': 0.8,  # 默认置信度
                'concerns': 0.7
            },
            'objects': [
                {
                    'type': 'face',
                    'confidence': data.get('confidence_score', 0.5)
                }
            ],
            'overall_confidence': data.get('confidence_score', 0.5),
            'language': language,
            'raw_response': str(data)
        }
    
    def _standardize_product_result(self, data: Dict[str, Any], language: str) -> Dict[str, Any]:
        """标准化产品识别结果"""
        products = data.get('products', [])
        return {
            'results': {
                'products': products,
                'product_count': len(products),
                'main_categories': data.get('main_categories', []),
                'overall_assessment': data.get('overall_assessment', ''),
                'analysis_notes': data.get('analysis_notes', '')
            },
            'confidence_scores': {
                'overall': data.get('confidence_score', 0.5),
                'product_identification': 0.7
            },
            'objects': [
                {
                    'type': 'product',
                    'name': product.get('name', 'Unknown'),
                    'confidence': product.get('confidence', 0.5)
                }
                for product in products
            ],
            'overall_confidence': data.get('confidence_score', 0.5),
            'language': language,
            'raw_response': str(data)
        }
    
    def _standardize_general_result(self, data: Dict[str, Any], language: str) -> Dict[str, Any]:
        """标准化通用分析结果"""
        return {
            'results': {
                'image_type': data.get('image_type', '未知'),
                'main_subjects': data.get('main_subjects', []),
                'beauty_context': data.get('beauty_context', ''),
                'key_observations': data.get('key_observations', []),
                'suggested_analysis_types': data.get('suggested_analysis_types', []),
                'overall_description': data.get('overall_description', ''),
                'analysis_notes': data.get('analysis_notes', '')
            },
            'confidence_scores': {
                'overall': data.get('confidence_score', 0.5)
            },
            'objects': [],
            'overall_confidence': data.get('confidence_score', 0.5),
            'language': language,
            'raw_response': str(data)
        }
    
    def _create_fallback_skin_result(self, raw_text: str, language: str) -> Dict[str, Any]:
        """创建皮肤分析降级结果"""
        return {
            'results': {
                'skin_concerns': [],
                'skin_type': '需要进一步分析' if language == 'zh' else 'requires_further_analysis',
                'overall_condition': raw_text[:200] + '...' if len(raw_text) > 200 else raw_text,
                'analysis_notes': '使用文本分析结果' if language == 'zh' else 'using_text_analysis'
            },
            'confidence_scores': {'overall': 0.3},
            'objects': [],
            'overall_confidence': 0.3,
            'language': language,
            'raw_response': raw_text,
            'fallback': True
        }
    
    def _create_fallback_product_result(self, raw_text: str, language: str) -> Dict[str, Any]:
        """创建产品识别降级结果"""
        return {
            'results': {
                'products': [],
                'product_count': 0,
                'overall_assessment': raw_text[:200] + '...' if len(raw_text) > 200 else raw_text,
                'analysis_notes': '使用文本分析结果' if language == 'zh' else 'using_text_analysis'
            },
            'confidence_scores': {'overall': 0.3},
            'objects': [],
            'overall_confidence': 0.3,
            'language': language,
            'raw_response': raw_text,
            'fallback': True
        }
    
    def _create_fallback_general_result(self, raw_text: str, language: str) -> Dict[str, Any]:
        """创建通用分析降级结果"""
        return {
            'results': {
                'image_type': '通用图像' if language == 'zh' else 'general_image',
                'overall_description': raw_text[:200] + '...' if len(raw_text) > 200 else raw_text,
                'analysis_notes': '使用文本分析结果' if language == 'zh' else 'using_text_analysis'
            },
            'confidence_scores': {'overall': 0.3},
            'objects': [],
            'overall_confidence': 0.3,
            'language': language,
            'raw_response': raw_text,
            'fallback': True
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            return {
                'status': 'healthy',
                'service': 'gpt4v',
                'timeout': self.timeout,
                'max_image_size': self.max_image_size,
                'timestamp': get_current_datetime()
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': get_current_datetime()
            }