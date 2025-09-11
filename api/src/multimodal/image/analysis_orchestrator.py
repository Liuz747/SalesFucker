"""
图像分析协调器模块

该模块协调不同类型的图像分析任务，包括皮肤分析、产品识别和通用分析。
提供智能分析类型选择和结果聚合功能。

核心功能:
- 智能分析类型检测
- 多种分析结果聚合
- 批量图像处理
- 分析质量评估
"""

import asyncio
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import uuid

from utils import (
    get_current_datetime,
    get_processing_time_ms,
    LoggerMixin,
    ProcessingType,
    MultiModalConstants
)
from .gpt4v_service import GPT4VService
from .image_processor import ImageProcessor


class ImageAnalysisOrchestrator(LoggerMixin):
    """
    图像分析协调器类
    
    协调和管理图像分析任务的执行。
    提供智能分析类型选择和结果优化。
    
    属性:
        gpt4v_service: GPT-4V分析服务
        image_processor: 图像预处理器
        analysis_cache: 分析结果缓存
    """
    
    def __init__(self, openai_api_key: str):
        """
        初始化图像分析协调器
        
        Args:
            openai_api_key: OpenAI API密钥
        """
        super().__init__()
        
        # 初始化服务
        self.gpt4v_service = GPT4VService(openai_api_key)
        self.image_processor = ImageProcessor()
        
        # 分析配置
        self.analysis_cache = {}
        self.confidence_threshold = 0.6
        
        self.logger.info("图像分析协调器已初始化")
    
    async def analyze_image_comprehensive(
        self,
        image_path: str,
        analysis_types: Optional[List[str]] = None,
        language: str = 'zh',
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        综合图像分析
        
        Args:
            image_path: 图像文件路径
            analysis_types: 指定的分析类型列表
            language: 分析语言
            context: 分析上下文
            
        Returns:
            综合分析结果
        """
        start_time = datetime.now()
        context = context or {}
        
        self.logger.info(f"开始综合图像分析: {image_path}")
        
        try:
            # 图像预处理
            processed_result = await self.image_processor.process_image_file(
                image_path,
                optimize_quality=True,
                resize_if_needed=True
            )
            
            processed_path = processed_result['processed_path']
            
            # 图像质量验证
            quality_result = await self.image_processor.validate_image_quality(processed_path)
            
            if not quality_result['is_acceptable']:
                self.logger.warning(f"图像质量不佳: {image_path}")
            
            # 智能分析类型检测
            if not analysis_types:
                analysis_types = await self._detect_analysis_types(processed_path, context)
            
            # 执行分析
            analysis_results = await self._execute_multiple_analyses(
                processed_path,
                analysis_types,
                language,
                context
            )
            
            # 结果聚合和优化
            comprehensive_result = await self._aggregate_analysis_results(
                analysis_results,
                quality_result,
                processed_result['metadata']
            )
            
            processing_time = get_processing_time_ms(start_time)
            
            # 清理临时文件
            if processed_path != image_path:
                await self.image_processor.cleanup_temp_files([processed_path])
            
            comprehensive_result.update({
                'processing_time_ms': processing_time,
                'image_quality': quality_result,
                'processed_metadata': processed_result['metadata'],
                'analysis_types_used': analysis_types
            })
            
            self.logger.info(
                f"综合图像分析完成: {image_path}, "
                f"耗时: {processing_time}ms, "
                f"分析类型: {analysis_types}"
            )
            
            return comprehensive_result
            
        except Exception as e:
            self.logger.error(f"综合图像分析失败: {image_path}, 错误: {e}")
            raise
    
    async def _detect_analysis_types(
        self,
        image_path: str,
        context: Dict[str, Any]
    ) -> List[str]:
        """
        智能检测分析类型
        
        Args:
            image_path: 图像路径
            context: 分析上下文
            
        Returns:
            建议的分析类型列表
        """
        try:
            # 先进行通用分析以确定图像内容
            general_result = await self.gpt4v_service.analyze_general(image_path, 'zh')
            
            analysis_types = []
            
            # 根据通用分析结果确定具体分析类型
            results = general_result.get('results', {})
            image_type = results.get('image_type', '')
            main_subjects = results.get('main_subjects', [])
            suggested_types = results.get('suggested_analysis_types', [])
            
            # 基于图像类型判断
            if 'selfie' in image_type.lower() or 'face' in image_type.lower():
                analysis_types.append(ProcessingType.SKIN_ANALYSIS)
            
            if 'product' in image_type.lower() or any('product' in subject.lower() for subject in main_subjects):
                analysis_types.append(ProcessingType.PRODUCT_RECOGNITION)
            
            # 基于建议类型
            for suggested_type in suggested_types:
                if 'skin' in suggested_type.lower() and ProcessingType.SKIN_ANALYSIS not in analysis_types:
                    analysis_types.append(ProcessingType.SKIN_ANALYSIS)
                elif 'product' in suggested_type.lower() and ProcessingType.PRODUCT_RECOGNITION not in analysis_types:
                    analysis_types.append(ProcessingType.PRODUCT_RECOGNITION)
            
            # 基于上下文信息
            if context.get('user_intent') == 'skin_analysis':
                if ProcessingType.SKIN_ANALYSIS not in analysis_types:
                    analysis_types.append(ProcessingType.SKIN_ANALYSIS)
            elif context.get('user_intent') == 'product_inquiry':
                if ProcessingType.PRODUCT_RECOGNITION not in analysis_types:
                    analysis_types.append(ProcessingType.PRODUCT_RECOGNITION)
            
            # 如果没有检测到特定类型，使用通用分析
            if not analysis_types:
                analysis_types.append(ProcessingType.IMAGE_ANALYSIS)
            
            self.logger.info(f"智能检测到分析类型: {analysis_types}")
            return analysis_types
            
        except Exception as e:
            self.logger.warning(f"分析类型检测失败: {e}")
            return [ProcessingType.IMAGE_ANALYSIS]  # 默认使用通用分析
    
    async def _execute_multiple_analyses(
        self,
        image_path: str,
        analysis_types: List[str],
        language: str,
        context: Dict[str, Any]
    ) -> Dict[str, Dict[str, Any]]:
        """
        执行多种分析
        
        Args:
            image_path: 图像路径
            analysis_types: 分析类型列表
            language: 分析语言
            context: 分析上下文
            
        Returns:
            各种分析结果字典
        """
        analysis_tasks = []
        task_types = []
        
        # 创建分析任务
        for analysis_type in analysis_types:
            if analysis_type == ProcessingType.SKIN_ANALYSIS:
                task = self.gpt4v_service.analyze_skin(image_path, language)
            elif analysis_type == ProcessingType.PRODUCT_RECOGNITION:
                task = self.gpt4v_service.recognize_product(image_path, language)
            else:
                task = self.gpt4v_service.analyze_general(image_path, language)
            
            analysis_tasks.append(task)
            task_types.append(analysis_type)
        
        # 并发执行分析
        try:
            results = await asyncio.gather(*analysis_tasks, return_exceptions=True)
            
            analysis_results = {}
            for i, result in enumerate(results):
                analysis_type = task_types[i]
                if isinstance(result, Exception):
                    self.logger.error(f"分析失败 {analysis_type}: {result}")
                    analysis_results[analysis_type] = {
                        'status': 'error',
                        'error': str(result),
                        'results': {},
                        'overall_confidence': 0.0
                    }
                else:
                    analysis_results[analysis_type] = result
            
            return analysis_results
            
        except Exception as e:
            self.logger.error(f"多种分析执行失败: {e}")
            raise
    
    async def _aggregate_analysis_results(
        self,
        analysis_results: Dict[str, Dict[str, Any]],
        quality_result: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        聚合分析结果
        
        Args:
            analysis_results: 各种分析结果
            quality_result: 图像质量结果
            metadata: 图像元数据
            
        Returns:
            聚合后的综合结果
        """
        # 收集所有成功的分析结果
        successful_analyses = {
            k: v for k, v in analysis_results.items() 
            if v.get('overall_confidence', 0) >= self.confidence_threshold
        }
        
        # 计算总体置信度
        if successful_analyses:
            total_confidence = sum(
                result.get('overall_confidence', 0) 
                for result in successful_analyses.values()
            ) / len(successful_analyses)
        else:
            total_confidence = 0.0
        
        # 提取关键发现
        key_findings = []
        detected_objects = []
        recommendations = []
        
        for analysis_type, result in successful_analyses.items():
            results_data = result.get('results', {})
            
            if analysis_type == ProcessingType.SKIN_ANALYSIS:
                skin_concerns = results_data.get('skin_concerns', [])
                for concern in skin_concerns:
                    key_findings.append({
                        'type': 'skin_concern',
                        'description': concern.get('description', ''),
                        'severity': concern.get('severity', ''),
                        'confidence': concern.get('confidence', 0)
                    })
                
                skin_recommendations = results_data.get('recommendations', [])
                recommendations.extend(skin_recommendations)
                
            elif analysis_type == ProcessingType.PRODUCT_RECOGNITION:
                products = results_data.get('products', [])
                for product in products:
                    detected_objects.append({
                        'type': 'product',
                        'name': product.get('name', ''),
                        'brand': product.get('brand', ''),
                        'confidence': product.get('confidence', 0)
                    })
                    
                    key_findings.append({
                        'type': 'product_detected',
                        'description': f"检测到产品: {product.get('name', '')}",
                        'confidence': product.get('confidence', 0)
                    })
            
            elif analysis_type == ProcessingType.IMAGE_ANALYSIS:
                observations = results_data.get('key_observations', [])
                for obs in observations:
                    key_findings.append({
                        'type': 'general_observation',
                        'description': obs.get('observation', ''),
                        'relevance': obs.get('relevance', ''),
                        'confidence': obs.get('confidence', 0)
                    })
        
        # 生成摘要
        summary = self._generate_analysis_summary(
            successful_analyses,
            key_findings,
            detected_objects
        )
        
        return {
            'overall_confidence': total_confidence,
            'summary': summary,
            'key_findings': key_findings,
            'detected_objects': detected_objects,
            'recommendations': recommendations,
            'detailed_results': analysis_results,
            'successful_analyses': list(successful_analyses.keys()),
            'failed_analyses': [
                k for k, v in analysis_results.items() 
                if v.get('overall_confidence', 0) < self.confidence_threshold
            ],
            'analysis_quality': {
                'image_quality_score': quality_result.get('overall_score', 0),
                'total_confidence': total_confidence,
                'successful_analysis_count': len(successful_analyses),
                'is_reliable': total_confidence >= 0.7 and quality_result.get('overall_score', 0) >= 0.5
            }
        }
    
    def _generate_analysis_summary(
        self,
        analyses: Dict[str, Dict[str, Any]],
        findings: List[Dict[str, Any]],
        objects: List[Dict[str, Any]]
    ) -> str:
        """生成分析摘要"""
        summary_parts = []
        
        if ProcessingType.SKIN_ANALYSIS in analyses:
            skin_result = analyses[ProcessingType.SKIN_ANALYSIS].get('results', {})
            skin_type = skin_result.get('skin_type', '')
            concerns_count = len(skin_result.get('skin_concerns', []))
            
            if skin_type:
                summary_parts.append(f"检测到{skin_type}肌肤")
            if concerns_count > 0:
                summary_parts.append(f"发现{concerns_count}个肌肤问题")
        
        if ProcessingType.PRODUCT_RECOGNITION in analyses:
            product_result = analyses[ProcessingType.PRODUCT_RECOGNITION].get('results', {})
            product_count = product_result.get('product_count', 0)
            
            if product_count > 0:
                summary_parts.append(f"识别到{product_count}个化妆品产品")
        
        if ProcessingType.IMAGE_ANALYSIS in analyses:
            general_result = analyses[ProcessingType.IMAGE_ANALYSIS].get('results', {})
            image_type = general_result.get('image_type', '')
            
            if image_type:
                summary_parts.append(f"图像类型: {image_type}")
        
        if not summary_parts:
            summary_parts.append("完成基础图像分析")
        
        return "；".join(summary_parts)
    
    async def batch_analyze_images(
        self,
        image_paths: List[str],
        analysis_types: Optional[List[str]] = None,
        language: str = 'zh'
    ) -> List[Dict[str, Any]]:
        """
        批量分析图像
        
        Args:
            image_paths: 图像路径列表
            analysis_types: 分析类型列表
            language: 分析语言
            
        Returns:
            批量分析结果列表
        """
        self.logger.info(f"开始批量图像分析，图像数量: {len(image_paths)}")
        
        # 创建分析任务
        tasks = [
            self.analyze_image_comprehensive(
                image_path,
                analysis_types,
                language
            )
            for image_path in image_paths
        ]
        
        # 并发执行
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理结果
        batch_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.error(f"批量分析失败 {image_paths[i]}: {result}")
                batch_results.append({
                    'image_path': image_paths[i],
                    'status': 'error',
                    'error': str(result),
                    'analysis_result': None
                })
            else:
                batch_results.append({
                    'image_path': image_paths[i],
                    'status': 'success',
                    'analysis_result': result
                })
        
        successful_count = len([r for r in batch_results if r['status'] == 'success'])
        self.logger.info(f"批量图像分析完成，成功: {successful_count}/{len(image_paths)}")
        
        return batch_results
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            gpt4v_health = await self.gpt4v_service.health_check()
            processor_health = await self.image_processor.health_check()
            
            overall_status = "healthy"
            if (gpt4v_health['status'] != 'healthy' or 
                processor_health['status'] != 'healthy'):
                overall_status = "degraded"
            
            return {
                'status': overall_status,
                'service': 'image_analysis_orchestrator',
                'gpt4v_service': gpt4v_health,
                'image_processor': processor_health,
                'confidence_threshold': self.confidence_threshold,
                'timestamp': get_current_datetime()
            }
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': get_current_datetime()
            }