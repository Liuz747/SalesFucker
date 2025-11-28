    async def _store_moments_memories(
        self,
        request: MomentsAnalysisRequest,
        result: MomentsAnalysisResponse,
        tenant_id: str
    ):
        """存储朋友圈互动记录到记忆"""
        try:
            # 建立 id 到 moment 的映射
            moment_map = {m.id: m for m in request.task_list}

            for task_result in result.tasks:
                moment = moment_map.get(task_result.id)
                if not moment or not moment.thread_id:
                    continue

                # 仅当有互动行为（点赞或评论）时存储
                if not task_result.actions:
                    continue

                # 构建记忆内容
                content_parts = []
                if moment.moment_content:
                    content_parts.append(f"用户发布朋友圈: {moment.moment_content}")
                
                if moment.url_list:
                    content_parts.append(f"[包含{len(moment.url_list)}张图片]")
                
                interaction_parts = []
                if SocialMediaActionType.LIKE in task_result.actions: # 假设 1 是点赞
                    interaction_parts.append("我点赞了")
                if SocialMediaActionType.COMMENT in task_result.actions and task_result.message: # 假设 2 是评论
                    interaction_parts.append(f"我评论: {task_result.message}")
                
                if interaction_parts:
                    content_parts.append(f"交互记录: {', '.join(interaction_parts)}")

                memory_content = " | ".join(content_parts)

                # 存储到记忆
                await self.storage_manager.store_memory(
                    tenant_id=tenant_id,
                    thread_id=uuid4() if not moment.thread_id else moment.thread_id, # thread_id should be UUID
                    content=memory_content,
                    memory_type=MemoryType.MOMENTS_INTERACTION,
                    tags=["moments", "interaction"]
                )
                logger.debug(f"朋友圈互动记忆已存储: {moment.id} -> {moment.thread_id}")

        except Exception as e:
            logger.error(f"存储朋友圈记忆失败: {e}", exc_info=True)
            # 不抛出异常，以免影响主流程

