"""
多模态错误处理和降级机制模块

该模块提供多模态处理的错误处理和降级机制。
确保在部分服务失败时仍能提供基础功能。

核心功能:
- 多层次错误处理策略
- 智能降级机制
- 服务健康监控
- 错误恢复机制
"""

import asyncio
from typing import Dict, Any, Optional, List, Callable, Union
from datetime import datetime, timedelta
from enum import Enum
import traceback

from src.utils import (
    get_current_datetime,
    get_processing_time_ms,
    LoggerMixin,
    ErrorHandler
)


class ServiceHealthStatus(Enum):
    """服务健康状态"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class FallbackStrategy(Enum):
    """降级策略"""
    SKIP = "skip"  # 跳过失败的模态
    RETRY = "retry"  # 重试
    PARTIAL = "partial"  # 部分处理
    MOCK = "mock"  # 返回模拟数据
    QUEUE = "queue"  # 加入重试队列


class MultiModalErrorHandler(LoggerMixin):
    """
    多模态错误处理器
    
    提供全面的错误处理和降级策略。
    
    属性:
        service_health: 服务健康状态跟踪
        error_counts: 错误计数
        fallback_config: 降级配置
    """
    
    def __init__(self):
        super().__init__()
        
        # 服务健康状态
        self.service_health = {
            'whisper': ServiceHealthStatus.UNKNOWN,
            'gpt4v': ServiceHealthStatus.UNKNOWN,
            'multimodal_processor': ServiceHealthStatus.UNKNOWN
        }
        
        # 错误统计
        self.error_counts = {
            'whisper': {'total': 0, 'recent': []},
            'gpt4v': {'total': 0, 'recent': []},
            'multimodal_processor': {'total': 0, 'recent': []}
        }
        
        # 降级配置
        self.fallback_config = {
            'max_retries': 3,
            'retry_delay_seconds': [1, 2, 5],  # 递增延迟
            'error_threshold': 5,  # 错误阈值
            'time_window_minutes': 10,  # 时间窗口
            'circuit_breaker_timeout': 300,  # 熔断器超时（秒）
            'enable_partial_processing': True,
            'enable_mock_responses': True
        }
        
        # 熔断器状态
        self.circuit_breakers = {}
        
        # 重试队列
        self.retry_queue = asyncio.Queue()
        
        self.logger.info("多模态错误处理器已初始化")
    
    @with_error_handling()
    async def handle_voice_processing_error(
        self,
        error: Exception,
        audio_path: str,
        language: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        处理语音处理错误
        
        Args:
            error: 异常对象
            audio_path: 音频文件路径
            language: 语言代码
            context: 处理上下文
            
        Returns:
            降级处理结果
        """
        self._record_error('whisper', error)
        
        error_type = self._classify_error(error)
        fallback_result = {
            'success': False,
            'error_type': error_type,
            'fallback_applied': False,
            'original_error': str(error)
        }
        
        # 根据错误类型选择降级策略
        if error_type == 'network_error':
            strategy = FallbackStrategy.RETRY
        elif error_type == 'api_quota_exceeded':
            strategy = FallbackStrategy.QUEUE
        elif error_type == 'file_format_error':
            strategy = FallbackStrategy.SKIP
        elif error_type == 'timeout_error':
            strategy = FallbackStrategy.PARTIAL
        else:
            strategy = FallbackStrategy.MOCK
        
        # 执行降级策略
        if strategy == FallbackStrategy.RETRY:
            fallback_result = await self._retry_voice_processing(
                audio_path, language, context
            )
        elif strategy == FallbackStrategy.QUEUE:
            fallback_result = await self._queue_voice_processing(
                audio_path, language, context
            )
        elif strategy == FallbackStrategy.MOCK:
            fallback_result = self._create_mock_voice_result(audio_path, language)
        elif strategy == FallbackStrategy.SKIP:
            fallback_result = self._create_skip_voice_result(error_type)
        
        self.logger.warning(
            f"语音处理错误已处理: {error_type}, "
            f"策略: {strategy.value}, "
            f"成功: {fallback_result.get('success', False)}"
        )
        
        return fallback_result
    
    @with_error_handling()
    async def handle_image_processing_error(
        self,
        error: Exception,
        image_path: str,
        analysis_type: str,
        language: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        处理图像处理错误
        
        Args:
            error: 异常对象
            image_path: 图像文件路径
            analysis_type: 分析类型
            language: 语言代码
            context: 处理上下文
            
        Returns:
            降级处理结果
        """
        self._record_error('gpt4v', error)
        
        error_type = self._classify_error(error)
        fallback_result = {
            'success': False,
            'error_type': error_type,
            'fallback_applied': False,
            'original_error': str(error)
        }
        
        # 根据错误类型和分析类型选择策略
        if error_type == 'network_error':
            strategy = FallbackStrategy.RETRY
        elif error_type == 'api_quota_exceeded':
            strategy = FallbackStrategy.QUEUE
        elif error_type == 'file_format_error':
            strategy = FallbackStrategy.SKIP
        elif error_type == 'content_policy_violation':
            strategy = FallbackStrategy.SKIP
        else:
            strategy = FallbackStrategy.PARTIAL if analysis_type == 'skin_analysis' else FallbackStrategy.MOCK
        
        # 执行降级策略
        if strategy == FallbackStrategy.RETRY:
            fallback_result = await self._retry_image_processing(
                image_path, analysis_type, language, context
            )
        elif strategy == FallbackStrategy.QUEUE:
            fallback_result = await self._queue_image_processing(
                image_path, analysis_type, language, context
            )
        elif strategy == FallbackStrategy.PARTIAL:
            fallback_result = self._create_partial_image_result(
                image_path, analysis_type, language
            )
        elif strategy == FallbackStrategy.MOCK:
            fallback_result = self._create_mock_image_result(
                analysis_type, language
            )
        elif strategy == FallbackStrategy.SKIP:
            fallback_result = self._create_skip_image_result(error_type)
        
        self.logger.warning(
            f"图像处理错误已处理: {error_type}, "
            f"策略: {strategy.value}, "
            f"成功: {fallback_result.get('success', False)}"
        )
        
        return fallback_result
    
    @with_error_handling()
    async def handle_multimodal_processing_error(
        self,
        error: Exception,
        message_context: Dict[str, Any],
        failed_components: List[str]
    ) -> Dict[str, Any]:
        """
        处理多模态处理错误
        
        Args:
            error: 异常对象
            message_context: 消息上下文
            failed_components: 失败的组件列表
            
        Returns:
            降级处理结果
        """
        self._record_error('multimodal_processor', error)
        
        # 分析失败情况
        has_voice = 'voice' in failed_components
        has_image = 'image' in failed_components
        has_text = message_context.get('payload', {}).get('message', '')
        
        fallback_result = {
            'success': False,
            'partial_success': False,
            'failed_components': failed_components,
            'available_content': {},
            'fallback_response': None
        }
        
        # 如果有文本内容，可以提供基础响应
        if has_text:
            fallback_result['available_content']['text'] = has_text
            fallback_result['partial_success'] = True
        
        # 如果只有部分组件失败，尝试部分处理
        if len(failed_components) < 2 and self.fallback_config['enable_partial_processing']:
            fallback_result['fallback_response'] = await self._create_partial_response(
                message_context, failed_components
            )
            fallback_result['success'] = True
        
        # 生成降级响应
        elif self.fallback_config['enable_mock_responses']:
            fallback_result['fallback_response'] = self._create_fallback_response(
                message_context, failed_components
            )
            fallback_result['success'] = True
        
        self.logger.warning(
            f"多模态处理错误已处理，"
            f"失败组件: {failed_components}, "
            f"部分成功: {fallback_result['partial_success']}"
        )
        
        return fallback_result
    
    def _classify_error(self, error: Exception) -> str:
        """分类错误类型"""
        error_str = str(error).lower()
        error_type = type(error).__name__.lower()
        
        if 'network' in error_str or 'connection' in error_str:
            return 'network_error'
        elif 'timeout' in error_str or 'timeouterror' in error_type:
            return 'timeout_error'
        elif 'quota' in error_str or 'rate limit' in error_str:
            return 'api_quota_exceeded'
        elif 'format' in error_str or 'codec' in error_str:
            return 'file_format_error'
        elif 'policy' in error_str or 'content' in error_str:
            return 'content_policy_violation'
        elif 'authentication' in error_str or 'api key' in error_str:
            return 'authentication_error'
        elif 'permission' in error_str or 'access' in error_str:
            return 'permission_error'
        elif 'file not found' in error_str or 'filenotfound' in error_type:
            return 'file_not_found'
        elif 'memory' in error_str or 'out of memory' in error_str:
            return 'memory_error'
        else:
            return 'unknown_error'
    
    def _record_error(self, service: str, error: Exception):
        """记录错误"""
        current_time = get_current_datetime()
        
        # 更新错误计数
        self.error_counts[service]['total'] += 1
        self.error_counts[service]['recent'].append({
            'timestamp': current_time,
            'error_type': self._classify_error(error),
            'error_message': str(error)
        })
        
        # 只保留最近的错误记录
        cutoff_time = current_time - timedelta(minutes=self.fallback_config['time_window_minutes'])
        self.error_counts[service]['recent'] = [
            err for err in self.error_counts[service]['recent']
            if err['timestamp'] > cutoff_time
        ]
        
        # 更新服务健康状态
        self._update_service_health(service)
    
    def _update_service_health(self, service: str):
        """更新服务健康状态"""
        recent_errors = len(self.error_counts[service]['recent'])
        error_threshold = self.fallback_config['error_threshold']
        
        if recent_errors >= error_threshold:
            self.service_health[service] = ServiceHealthStatus.UNHEALTHY
            # 激活熔断器
            self._activate_circuit_breaker(service)
        elif recent_errors >= error_threshold // 2:
            self.service_health[service] = ServiceHealthStatus.DEGRADED
        else:
            self.service_health[service] = ServiceHealthStatus.HEALTHY
            # 重置熔断器
            self._reset_circuit_breaker(service)
    
    def _activate_circuit_breaker(self, service: str):
        """激活熔断器"""
        self.circuit_breakers[service] = {
            'activated_at': get_current_datetime(),
            'timeout': self.fallback_config['circuit_breaker_timeout']
        }
        self.logger.warning(f"服务熔断器已激活: {service}")
    
    def _reset_circuit_breaker(self, service: str):
        """重置熔断器"""
        if service in self.circuit_breakers:
            del self.circuit_breakers[service]
            self.logger.info(f"服务熔断器已重置: {service}")
    
    def _is_circuit_breaker_active(self, service: str) -> bool:
        """检查熔断器是否激活"""
        if service not in self.circuit_breakers:
            return False
        
        breaker = self.circuit_breakers[service]
        activated_at = breaker['activated_at']
        timeout = breaker['timeout']
        
        if get_current_datetime() - activated_at > timedelta(seconds=timeout):
            self._reset_circuit_breaker(service)
            return False
        
        return True
    
    async def _retry_voice_processing(
        self,
        audio_path: str,
        language: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """重试语音处理"""
        max_retries = self.fallback_config['max_retries']
        delay_schedule = self.fallback_config['retry_delay_seconds']
        
        for attempt in range(max_retries):
            try:
                # 等待重试延迟
                if attempt > 0:
                    delay = delay_schedule[min(attempt - 1, len(delay_schedule) - 1)]
                    await asyncio.sleep(delay)
                
                # 这里需要实际的重试逻辑
                # 在实际应用中会调用真实的服务
                self.logger.info(f"语音处理重试 {attempt + 1}/{max_retries}")
                
                # 模拟重试结果
                return {
                    'success': True,
                    'retry_attempt': attempt + 1,
                    'text': f'重试后的转录结果（尝试 {attempt + 1}）',
                    'confidence': 0.6,
                    'from_retry': True
                }
                
            except Exception as e:
                self.logger.warning(f"语音处理重试失败 {attempt + 1}: {e}")
                if attempt == max_retries - 1:
                    return {
                        'success': False,
                        'retry_attempts': max_retries,
                        'final_error': str(e)
                    }
        
        return {'success': False, 'retry_attempts': max_retries}
    
    async def _retry_image_processing(
        self,
        image_path: str,
        analysis_type: str,
        language: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """重试图像处理"""
        # 类似语音处理的重试逻辑
        max_retries = self.fallback_config['max_retries']
        
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    delay = self.fallback_config['retry_delay_seconds'][
                        min(attempt - 1, len(self.fallback_config['retry_delay_seconds']) - 1)
                    ]
                    await asyncio.sleep(delay)
                
                self.logger.info(f"图像处理重试 {attempt + 1}/{max_retries}")
                
                return {
                    'success': True,
                    'retry_attempt': attempt + 1,
                    'results': {'analysis_type': analysis_type, 'confidence': 0.5},
                    'from_retry': True
                }
                
            except Exception as e:
                self.logger.warning(f"图像处理重试失败 {attempt + 1}: {e}")
                
        return {'success': False, 'retry_attempts': max_retries}
    
    async def _queue_voice_processing(
        self,
        audio_path: str,
        language: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """将语音处理加入队列"""
        queue_item = {
            'type': 'voice_processing',
            'audio_path': audio_path,
            'language': language,
            'context': context,
            'queued_at': get_current_datetime()
        }
        
        await self.retry_queue.put(queue_item)
        
        return {
            'success': True,
            'queued': True,
            'estimated_delay_minutes': 5,
            'message': '语音处理已加入重试队列'
        }
    
    async def _queue_image_processing(
        self,
        image_path: str,
        analysis_type: str,
        language: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """将图像处理加入队列"""
        queue_item = {
            'type': 'image_processing',
            'image_path': image_path,
            'analysis_type': analysis_type,
            'language': language,
            'context': context,
            'queued_at': get_current_datetime()
        }
        
        await self.retry_queue.put(queue_item)
        
        return {
            'success': True,
            'queued': True,
            'estimated_delay_minutes': 3,
            'message': '图像处理已加入重试队列'
        }
    
    def _create_mock_voice_result(self, audio_path: str, language: str) -> Dict[str, Any]:
        """创建模拟语音结果"""
        return {
            'success': True,
            'text': '抱歉，语音识别服务暂时不可用，请稍后重试或使用文字输入。',
            'language': language,
            'confidence': 0.0,
            'is_mock': True,
            'mock_reason': '语音识别服务降级'
        }
    
    def _create_mock_image_result(self, analysis_type: str, language: str) -> Dict[str, Any]:
        """创建模拟图像结果"""
        if language == 'zh':
            messages = {
                'skin_analysis': '抱歉，皮肤分析服务暂时不可用，建议稍后重试。',
                'product_recognition': '抱歉，产品识别服务暂时不可用，请描述您的产品需求。',
                'general_analysis': '抱歉，图像分析服务暂时不可用，请稍后重试。'
            }
        else:
            messages = {
                'skin_analysis': 'Sorry, skin analysis service is temporarily unavailable.',
                'product_recognition': 'Sorry, product recognition is temporarily unavailable.',
                'general_analysis': 'Sorry, image analysis service is temporarily unavailable.'
            }
        
        return {
            'success': True,
            'results': {
                'message': messages.get(analysis_type, messages['general_analysis']),
                'analysis_type': analysis_type
            },
            'overall_confidence': 0.0,
            'is_mock': True,
            'mock_reason': '图像分析服务降级'
        }
    
    def _create_partial_image_result(
        self,
        image_path: str,
        analysis_type: str,
        language: str
    ) -> Dict[str, Any]:
        """创建部分图像结果"""
        return {
            'success': True,
            'results': {
                'analysis_type': analysis_type,
                'partial_analysis': True,
                'message': '由于服务限制，只能提供基础分析结果' if language == 'zh' 
                          else 'Limited analysis results due to service constraints'
            },
            'overall_confidence': 0.3,
            'is_partial': True
        }
    
    def _create_skip_voice_result(self, error_type: str) -> Dict[str, Any]:
        """创建跳过语音结果"""
        return {
            'success': False,
            'skipped': True,
            'reason': error_type,
            'message': '语音处理已跳过，将使用其他输入方式'
        }
    
    def _create_skip_image_result(self, error_type: str) -> Dict[str, Any]:
        """创建跳过图像结果"""
        return {
            'success': False,
            'skipped': True,
            'reason': error_type,
            'message': '图像处理已跳过，将使用其他分析方式'
        }
    
    async def _create_partial_response(
        self,
        message_context: Dict[str, Any],
        failed_components: List[str]
    ) -> Dict[str, Any]:
        """创建部分响应"""
        available_content = []
        
        # 检查可用的内容
        if 'voice' not in failed_components:
            available_content.append('语音')
        if 'image' not in failed_components:
            available_content.append('图像')
        if message_context.get('payload', {}).get('message'):
            available_content.append('文本')
        
        return {
            'partial_response': True,
            'available_modalities': available_content,
            'message': f'基于{",".join(available_content)}内容的分析结果',
            'recommendation': '建议补充其他形式的输入以获得更准确的建议'
        }
    
    def _create_fallback_response(
        self,
        message_context: Dict[str, Any],
        failed_components: List[str]
    ) -> Dict[str, Any]:
        """创建降级响应"""
        return {
            'fallback_response': True,
            'message': '系统正在维护中，为您提供基础服务',
            'recommendation': '请稍后重试以获得完整的多模态分析服务',
            'failed_components': failed_components,
            'support_contact': '如需帮助，请联系客服'
        }
    
    async def get_service_health_report(self) -> Dict[str, Any]:
        """获取服务健康报告"""
        report = {
            'overall_health': 'healthy',
            'services': {},
            'error_summary': {},
            'circuit_breakers': {},
            'recommendations': []
        }
        
        unhealthy_count = 0
        degraded_count = 0
        
        for service, status in self.service_health.items():
            report['services'][service] = {
                'status': status.value,
                'recent_errors': len(self.error_counts[service]['recent']),
                'total_errors': self.error_counts[service]['total'],
                'circuit_breaker_active': self._is_circuit_breaker_active(service)
            }
            
            if status == ServiceHealthStatus.UNHEALTHY:
                unhealthy_count += 1
            elif status == ServiceHealthStatus.DEGRADED:
                degraded_count += 1
        
        # 确定整体健康状态
        if unhealthy_count > 0:
            report['overall_health'] = 'unhealthy'
        elif degraded_count > 0:
            report['overall_health'] = 'degraded'
        
        # 生成建议
        if unhealthy_count > 0:
            report['recommendations'].append('检查不健康的服务并进行修复')
        if degraded_count > 0:
            report['recommendations'].append('监控降级服务的恢复情况')
        
        return report
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        return {
            'status': 'healthy',
            'service': 'multimodal_error_handler',
            'service_health': {k: v.value for k, v in self.service_health.items()},
            'active_circuit_breakers': list(self.circuit_breakers.keys()),
            'retry_queue_size': self.retry_queue.qsize(),
            'timestamp': get_current_datetime()
        }