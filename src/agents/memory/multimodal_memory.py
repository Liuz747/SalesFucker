"""
记忆智能体多模态增强模块

该模块为记忆智能体提供多模态数据存储和检索能力。
支持语音转录、图像分析结果的持久化和上下文管理。

核心功能:
- 多模态对话历史存储
- 图像分析结果持久化
- 语音偏好和模式记录
- 多模态用户画像构建
"""

from typing import Dict, Any, List, Optional
import asyncio
from datetime import datetime, timedelta
import json
import hashlib

from src.utils import (
    get_current_datetime,
    LoggerMixin,
    with_error_handling,
    ProcessingType,
    InputType,
    ProcessingStatus
)


class MultimodalMemoryManager(LoggerMixin):
    """
    多模态记忆管理器
    
    管理多模态对话数据的存储、检索和分析。
    构建包含语音和视觉偏好的用户画像。
    
    属性:
        tenant_id: 租户标识符
        multimodal_storage: 多模态数据存储
        user_profiles: 用户多模态画像
    """
    
    def __init__(self, tenant_id: str):
        """
        初始化多模态记忆管理器
        
        Args:
            tenant_id: 租户标识符
        """
        super().__init__()
        self.tenant_id = tenant_id
        
        # 多模态数据存储
        self.multimodal_storage = {
            'conversations': {},  # 按对话ID存储多模态历史
            'voice_patterns': {},  # 用户语音模式
            'visual_preferences': {},  # 用户视觉偏好
            'analysis_cache': {}  # 分析结果缓存
        }
        
        # 用户画像缓存
        self.user_profiles = {}
        self.profile_update_time = {}
        
        self.logger.info(f"多模态记忆管理器已初始化: {tenant_id}")
    
    @with_error_handling()
    async def store_multimodal_conversation(
        self,
        conversation_id: str,
        customer_id: str,
        multimodal_message: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        存储多模态对话数据
        
        Args:
            conversation_id: 对话标识符
            customer_id: 客户标识符
            multimodal_message: 多模态消息数据
            
        Returns:
            存储结果
        """
        try:
            timestamp = get_current_datetime()
            
            # 初始化对话存储
            if conversation_id not in self.multimodal_storage['conversations']:
                self.multimodal_storage['conversations'][conversation_id] = {
                    'customer_id': customer_id,
                    'messages': [],
                    'created_at': timestamp,
                    'last_updated': timestamp
                }
            
            # 提取多模态内容
            multimodal_content = await self._extract_multimodal_content(multimodal_message)
            
            # 构建存储记录
            message_record = {
                'message_id': multimodal_message.get('message_id'),
                'timestamp': timestamp,
                'input_type': multimodal_message.get('input_type', InputType.TEXT),
                'content': multimodal_content,
                'processing_summary': multimodal_message.get('processing_summary', {}),
                'metadata': {
                    'has_voice': bool(multimodal_content.get('transcriptions')),
                    'has_images': bool(multimodal_content.get('image_analysis')),
                    'processing_time_ms': multimodal_message.get('processing_time_ms', 0)
                }
            }
            
            # 存储消息
            self.multimodal_storage['conversations'][conversation_id]['messages'].append(message_record)
            self.multimodal_storage['conversations'][conversation_id]['last_updated'] = timestamp
            
            # 更新用户模式
            await self._update_user_patterns(customer_id, multimodal_content)
            
            # 异步更新用户画像
            asyncio.create_task(self._update_user_profile(customer_id, multimodal_content))
            
            self.logger.info(f"多模态对话已存储: {conversation_id}")
            
            return {
                'success': True,
                'conversation_id': conversation_id,
                'message_count': len(self.multimodal_storage['conversations'][conversation_id]['messages']),
                'stored_at': timestamp
            }
            
        except Exception as e:
            self.logger.error(f"多模态对话存储失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _extract_multimodal_content(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """提取多模态内容"""
        content = {
            'text': message.get('payload', {}).get('message', ''),
            'transcriptions': [],
            'image_analysis': {},
            'combined_content': message.get('combined_content', '')
        }
        
        # 提取语音转录
        transcriptions = message.get('transcriptions', [])
        if transcriptions:
            content['transcriptions'] = transcriptions
        
        # 提取图像分析结果
        image_analysis = message.get('image_analysis', {})
        if image_analysis:
            # 只存储关键分析结果，不存储原始数据
            processed_analysis = {}
            for attachment_id, analysis_data in image_analysis.items():
                processed_analysis[attachment_id] = {
                    'analysis_type': analysis_data.get('analysis_type'),
                    'summary': self._summarize_image_analysis(analysis_data),
                    'confidence': analysis_data.get('overall_confidence', 0),
                    'timestamp': get_current_datetime()
                }
            content['image_analysis'] = processed_analysis
        
        return content
    
    def _summarize_image_analysis(self, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """汇总图像分析结果"""
        results = analysis_data.get('results', {})
        summary = {
            'type': 'unknown',
            'key_findings': [],
            'confidence': analysis_data.get('overall_confidence', 0)
        }
        
        # 皮肤分析汇总
        if 'skin_concerns' in results:
            summary['type'] = 'skin_analysis'
            summary['skin_type'] = results.get('skin_type', '')
            summary['concern_count'] = len(results.get('skin_concerns', []))
            summary['key_findings'] = [
                concern.get('type', '') for concern in results.get('skin_concerns', [])
            ]
        
        # 产品识别汇总
        elif 'products' in results:
            summary['type'] = 'product_recognition'
            summary['product_count'] = len(results.get('products', []))
            summary['key_findings'] = [
                f"{product.get('brand', '')} {product.get('name', '')}"
                for product in results.get('products', [])
            ]
        
        # 通用分析汇总
        else:
            summary['type'] = 'general_analysis'
            summary['image_type'] = results.get('image_type', '')
            summary['key_findings'] = results.get('main_subjects', [])
        
        return summary
    
    async def _update_user_patterns(
        self,
        customer_id: str,
        multimodal_content: Dict[str, Any]
    ):
        """更新用户多模态模式"""
        # 更新语音模式
        if multimodal_content.get('transcriptions'):
            await self._update_voice_patterns(customer_id, multimodal_content['transcriptions'])
        
        # 更新视觉偏好
        if multimodal_content.get('image_analysis'):
            await self._update_visual_preferences(customer_id, multimodal_content['image_analysis'])
    
    async def _update_voice_patterns(self, customer_id: str, transcriptions: List[str]):
        """更新用户语音模式"""
        if customer_id not in self.multimodal_storage['voice_patterns']:
            self.multimodal_storage['voice_patterns'][customer_id] = {
                'total_messages': 0,
                'common_phrases': {},
                'emotional_indicators': {},
                'language_preference': 'zh',
                'last_updated': get_current_datetime()
            }
        
        patterns = self.multimodal_storage['voice_patterns'][customer_id]
        patterns['total_messages'] += len(transcriptions)
        
        # 分析常用短语（简化版本）
        combined_text = ' '.join(transcriptions).lower()
        words = combined_text.split()
        
        for word in words:
            if len(word) > 2:  # 只记录有意义的词汇
                patterns['common_phrases'][word] = patterns['common_phrases'].get(word, 0) + 1
        
        # 分析情感指标
        emotional_words = {
            'positive': ['喜欢', '爱', '好', '棒', '完美'],
            'negative': ['不好', '差', '失望', '问题'],
            'concern': ['担心', '过敏', '敏感', '问题']
        }
        
        for emotion, words_list in emotional_words.items():
            count = sum(1 for word in words_list if word in combined_text)
            if count > 0:
                patterns['emotional_indicators'][emotion] = patterns['emotional_indicators'].get(emotion, 0) + count
        
        patterns['last_updated'] = get_current_datetime()
    
    async def _update_visual_preferences(
        self,
        customer_id: str,
        image_analysis: Dict[str, Any]
    ):
        """更新用户视觉偏好"""
        if customer_id not in self.multimodal_storage['visual_preferences']:
            self.multimodal_storage['visual_preferences'][customer_id] = {
                'skin_analysis_history': [],
                'product_interests': {},
                'style_preferences': {},
                'upload_frequency': {'skin_selfies': 0, 'product_photos': 0},
                'last_updated': get_current_datetime()
            }
        
        preferences = self.multimodal_storage['visual_preferences'][customer_id]
        
        for attachment_id, analysis in image_analysis.items():
            summary = analysis.get('summary', {})
            analysis_type = summary.get('type', '')
            
            if analysis_type == 'skin_analysis':
                # 记录皮肤分析历史
                skin_record = {
                    'timestamp': get_current_datetime(),
                    'skin_type': summary.get('skin_type', ''),
                    'concerns': summary.get('key_findings', []),
                    'confidence': summary.get('confidence', 0)
                }
                preferences['skin_analysis_history'].append(skin_record)
                preferences['upload_frequency']['skin_selfies'] += 1
                
                # 只保留最近10次记录
                if len(preferences['skin_analysis_history']) > 10:
                    preferences['skin_analysis_history'] = preferences['skin_analysis_history'][-10:]
            
            elif analysis_type == 'product_recognition':
                # 记录产品兴趣
                for product_name in summary.get('key_findings', []):
                    if product_name:
                        preferences['product_interests'][product_name] = preferences['product_interests'].get(product_name, 0) + 1
                
                preferences['upload_frequency']['product_photos'] += 1
        
        preferences['last_updated'] = get_current_datetime()
    
    async def _update_user_profile(
        self,
        customer_id: str,
        multimodal_content: Dict[str, Any]
    ):
        """更新用户多模态画像"""
        try:
            if customer_id not in self.user_profiles:
                self.user_profiles[customer_id] = {
                    'basic_info': {},
                    'communication_preferences': {},
                    'beauty_profile': {},
                    'behavior_patterns': {},
                    'last_updated': get_current_datetime()
                }
            
            profile = self.user_profiles[customer_id]
            
            # 更新沟通偏好
            await self._update_communication_preferences(profile, multimodal_content)
            
            # 更新美容画像
            await self._update_beauty_profile(profile, multimodal_content)
            
            # 更新行为模式
            await self._update_behavior_patterns(profile, multimodal_content)
            
            profile['last_updated'] = get_current_datetime()
            self.profile_update_time[customer_id] = get_current_datetime()
            
        except Exception as e:
            self.logger.error(f"用户画像更新失败: {customer_id}, 错误: {e}")
    
    async def _update_communication_preferences(
        self,
        profile: Dict[str, Any],
        content: Dict[str, Any]
    ):
        """更新沟通偏好"""
        comm_prefs = profile.setdefault('communication_preferences', {
            'preferred_input_types': {},
            'response_preferences': {},
            'interaction_style': 'standard'
        })
        
        # 统计输入类型偏好
        if content.get('transcriptions'):
            comm_prefs['preferred_input_types']['voice'] = comm_prefs['preferred_input_types'].get('voice', 0) + 1
        
        if content.get('image_analysis'):
            comm_prefs['preferred_input_types']['image'] = comm_prefs['preferred_input_types'].get('image', 0) + 1
        
        if content.get('text'):
            comm_prefs['preferred_input_types']['text'] = comm_prefs['preferred_input_types'].get('text', 0) + 1
    
    async def _update_beauty_profile(
        self,
        profile: Dict[str, Any],
        content: Dict[str, Any]
    ):
        """更新美容画像"""
        beauty_profile = profile.setdefault('beauty_profile', {
            'skin_concerns': {},
            'product_interests': {},
            'style_preferences': {},
            'routine_frequency': {}
        })
        
        # 从图像分析更新美容信息
        image_analysis = content.get('image_analysis', {})
        for attachment_id, analysis in image_analysis.items():
            summary = analysis.get('summary', {})
            
            if summary.get('type') == 'skin_analysis':
                # 更新皮肤关注点
                for concern in summary.get('key_findings', []):
                    if concern:
                        beauty_profile['skin_concerns'][concern] = beauty_profile['skin_concerns'].get(concern, 0) + 1
            
            elif summary.get('type') == 'product_recognition':
                # 更新产品兴趣
                for product in summary.get('key_findings', []):
                    if product:
                        beauty_profile['product_interests'][product] = beauty_profile['product_interests'].get(product, 0) + 1
    
    async def _update_behavior_patterns(
        self,
        profile: Dict[str, Any],
        content: Dict[str, Any]
    ):
        """更新行为模式"""
        behavior = profile.setdefault('behavior_patterns', {
            'multimodal_usage': {},
            'engagement_level': 'medium',
            'consultation_frequency': 'weekly'
        })
        
        # 更新多模态使用模式
        if content.get('transcriptions') and content.get('image_analysis'):
            behavior['multimodal_usage']['combined'] = behavior['multimodal_usage'].get('combined', 0) + 1
        elif content.get('transcriptions'):
            behavior['multimodal_usage']['voice_only'] = behavior['multimodal_usage'].get('voice_only', 0) + 1
        elif content.get('image_analysis'):
            behavior['multimodal_usage']['image_only'] = behavior['multimodal_usage'].get('image_only', 0) + 1
    
    @with_error_handling()
    async def retrieve_multimodal_history(
        self,
        customer_id: str,
        conversation_id: Optional[str] = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        检索多模态历史记录
        
        Args:
            customer_id: 客户标识符
            conversation_id: 特定对话ID（可选）
            limit: 返回记录数量限制
            
        Returns:
            历史记录数据
        """
        try:
            if conversation_id:
                # 返回特定对话的历史
                conversation = self.multimodal_storage['conversations'].get(conversation_id, {})
                if conversation.get('customer_id') == customer_id:
                    messages = conversation.get('messages', [])
                    return {
                        'conversation_id': conversation_id,
                        'messages': messages[-limit:] if limit else messages,
                        'total_messages': len(messages)
                    }
                else:
                    return {'error': 'Conversation not found or access denied'}
            
            else:
                # 返回客户的所有对话历史
                customer_conversations = []
                for conv_id, conv_data in self.multimodal_storage['conversations'].items():
                    if conv_data.get('customer_id') == customer_id:
                        messages = conv_data.get('messages', [])
                        customer_conversations.append({
                            'conversation_id': conv_id,
                            'created_at': conv_data.get('created_at'),
                            'last_updated': conv_data.get('last_updated'),
                            'message_count': len(messages),
                            'recent_messages': messages[-3:] if messages else []  # 最近3条
                        })
                
                # 按最后更新时间排序
                customer_conversations.sort(
                    key=lambda x: x.get('last_updated', datetime.min),
                    reverse=True
                )
                
                return {
                    'customer_id': customer_id,
                    'conversations': customer_conversations[:limit],
                    'total_conversations': len(customer_conversations)
                }
        
        except Exception as e:
            self.logger.error(f"多模态历史检索失败: {e}")
            return {'error': str(e)}
    
    @with_error_handling()
    async def get_user_multimodal_profile(self, customer_id: str) -> Dict[str, Any]:
        """
        获取用户多模态画像
        
        Args:
            customer_id: 客户标识符
            
        Returns:
            用户多模态画像
        """
        try:
            # 获取基础画像
            profile = self.user_profiles.get(customer_id, {})
            
            # 获取语音模式
            voice_patterns = self.multimodal_storage['voice_patterns'].get(customer_id, {})
            
            # 获取视觉偏好
            visual_preferences = self.multimodal_storage['visual_preferences'].get(customer_id, {})
            
            # 构建综合画像
            comprehensive_profile = {
                'customer_id': customer_id,
                'basic_profile': profile,
                'voice_patterns': voice_patterns,
                'visual_preferences': visual_preferences,
                'multimodal_insights': await self._generate_multimodal_insights(
                    customer_id, profile, voice_patterns, visual_preferences
                ),
                'last_updated': profile.get('last_updated') or get_current_datetime()
            }
            
            return comprehensive_profile
            
        except Exception as e:
            self.logger.error(f"用户多模态画像获取失败: {e}")
            return {'error': str(e)}
    
    async def _generate_multimodal_insights(
        self,
        customer_id: str,
        profile: Dict[str, Any],
        voice_patterns: Dict[str, Any],
        visual_preferences: Dict[str, Any]
    ) -> Dict[str, Any]:
        """生成多模态洞察"""
        insights = {
            'communication_style': 'unknown',
            'engagement_level': 'medium',
            'beauty_focus_areas': [],
            'preferred_interaction_modes': [],
            'personalization_recommendations': []
        }
        
        # 分析沟通风格
        comm_prefs = profile.get('communication_preferences', {})
        input_types = comm_prefs.get('preferred_input_types', {})
        
        if input_types.get('voice', 0) > input_types.get('text', 0):
            insights['communication_style'] = 'voice_preferred'
            insights['preferred_interaction_modes'].append('voice')
        
        if input_types.get('image', 0) > 0:
            insights['communication_style'] = 'visual_oriented'
            insights['preferred_interaction_modes'].append('image')
        
        # 分析美容关注点
        beauty_profile = profile.get('beauty_profile', {})
        skin_concerns = beauty_profile.get('skin_concerns', {})
        
        # 按关注频次排序
        top_concerns = sorted(skin_concerns.items(), key=lambda x: x[1], reverse=True)[:3]
        insights['beauty_focus_areas'] = [concern[0] for concern in top_concerns]
        
        # 生成个性化建议
        insights['personalization_recommendations'] = self._generate_personalization_tips(
            insights, voice_patterns, visual_preferences
        )
        
        return insights
    
    def _generate_personalization_tips(
        self,
        insights: Dict[str, Any],
        voice_patterns: Dict[str, Any],
        visual_preferences: Dict[str, Any]
    ) -> List[str]:
        """生成个性化建议"""
        tips = []
        
        # 基于沟通偏好的建议
        if 'voice' in insights.get('preferred_interaction_modes', []):
            tips.append('建议使用语音咨询功能，获得更自然的交互体验')
        
        if 'image' in insights.get('preferred_interaction_modes', []):
            tips.append('建议上传皮肤照片，获得更精准的产品推荐')
        
        # 基于美容关注点的建议
        focus_areas = insights.get('beauty_focus_areas', [])
        if '痘痘' in focus_areas:
            tips.append('专注于控油和抗痘产品推荐')
        if '色斑' in focus_areas:
            tips.append('推荐美白和淡斑类产品')
        
        # 基于行为模式的建议
        skin_history = visual_preferences.get('skin_analysis_history', [])
        if len(skin_history) >= 3:
            tips.append('建立皮肤变化追踪，提供个性化护肤方案')
        
        return tips
    
    async def cleanup_old_data(self, days_to_keep: int = 30):
        """清理过期数据"""
        try:
            cutoff_date = get_current_datetime() - timedelta(days=days_to_keep)
            cleaned_count = 0
            
            # 清理过期对话
            expired_conversations = []
            for conv_id, conv_data in self.multimodal_storage['conversations'].items():
                last_updated = conv_data.get('last_updated')
                if isinstance(last_updated, datetime) and last_updated < cutoff_date:
                    expired_conversations.append(conv_id)
            
            for conv_id in expired_conversations:
                del self.multimodal_storage['conversations'][conv_id]
                cleaned_count += 1
            
            self.logger.info(f"数据清理完成，删除了 {cleaned_count} 个过期对话")
            
        except Exception as e:
            self.logger.error(f"数据清理失败: {e}")
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        return {
            'status': 'healthy',
            'service': 'multimodal_memory_manager',
            'tenant_id': self.tenant_id,
            'statistics': {
                'total_conversations': len(self.multimodal_storage['conversations']),
                'total_voice_patterns': len(self.multimodal_storage['voice_patterns']),
                'total_visual_preferences': len(self.multimodal_storage['visual_preferences']),
                'cached_profiles': len(self.user_profiles)
            },
            'timestamp': get_current_datetime()
        }