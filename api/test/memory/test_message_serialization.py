"""
测试 Message 序列化/反序列化的完整性，特别是多模态内容。

验证 ConversationStore 使用的 msgpack 序列化能正确处理：
1. 纯文本消息
2. 多模态消息 (Sequence[InputContent])
3. 不同角色的消息
"""

import msgpack

from libs.types import (
    Message,
    UserMessage,
    AssistantMessage,
    SystemMessage,
    InputContent,
    InputType
)


class TestMessageSerialization:
    """测试 Message 模型的序列化与反序列化"""

    def test_text_message_roundtrip(self):
        """测试纯文本消息序列化 - user角色"""
        msg = UserMessage(role="user", content="Hello world")

        # 序列化
        packed = msgpack.packb(msg.model_dump(), use_bin_type=True)

        # 反序列化
        unpacked = msgpack.unpackb(packed, raw=False)
        restored = UserMessage(**unpacked)

        assert restored.role == "user"
        assert restored.content == "Hello world"

    def test_assistant_text_message_roundtrip(self):
        """测试纯文本消息序列化 - assistant角色"""
        msg = AssistantMessage(role="assistant", content="I can help you with that.")

        packed = msgpack.packb(msg.model_dump(), use_bin_type=True)
        unpacked = msgpack.unpackb(packed, raw=False)
        restored = AssistantMessage(**unpacked)

        assert restored.role == "assistant"
        assert restored.content == "I can help you with that."

    def test_system_text_message_roundtrip(self):
        """测试纯文本消息序列化 - system角色"""
        msg = SystemMessage(role="system", content="You are a helpful assistant.")

        packed = msgpack.packb(msg.model_dump(), use_bin_type=True)
        unpacked = msgpack.unpackb(packed, raw=False)
        restored = SystemMessage(**unpacked)

        assert restored.role == "system"
        assert restored.content == "You are a helpful assistant."

    def test_multimodal_text_only_roundtrip(self):
        """测试多模态消息序列化 - 仅文本内容"""
        msg = UserMessage(
            role="user",
            content=[
                InputContent(type=InputType.TEXT, content="What is this?"),
            ]
        )

        packed = msgpack.packb(msg.model_dump(), use_bin_type=True)
        unpacked = msgpack.unpackb(packed, raw=False)
        restored = UserMessage(**unpacked)

        assert restored.role == "user"
        assert isinstance(restored.content, list)
        assert len(restored.content) == 1
        assert restored.content[0].type == InputType.TEXT
        assert restored.content[0].content == "What is this?"

    def test_multimodal_image_roundtrip(self):
        """测试多模态消息序列化 - 文本+图像"""
        msg = UserMessage(
            role="user",
            content=[
                InputContent(type=InputType.TEXT, content="Check this image"),
                InputContent(type=InputType.IMAGE, content="https://example.com/img.png"),
            ]
        )

        packed = msgpack.packb(msg.model_dump(), use_bin_type=True)
        unpacked = msgpack.unpackb(packed, raw=False)
        restored = UserMessage(**unpacked)

        assert restored.role == "user"
        assert isinstance(restored.content, list)
        assert len(restored.content) == 2

        # 验证文本内容
        assert restored.content[0].type == InputType.TEXT
        assert restored.content[0].content == "Check this image"

        # 验证图像内容
        assert restored.content[1].type == InputType.IMAGE
        assert restored.content[1].content == "https://example.com/img.png"

    def test_multimodal_audio_roundtrip(self):
        """测试多模态消息序列化 - 文本+音频"""
        msg = UserMessage(
            role="user",
            content=[
                InputContent(type=InputType.TEXT, content="Transcribed: Hello"),
                InputContent(type=InputType.AUDIO, content="https://example.com/audio.mp3"),
            ]
        )

        packed = msgpack.packb(msg.model_dump(), use_bin_type=True)
        unpacked = msgpack.unpackb(packed, raw=False)
        restored = UserMessage(**unpacked)

        assert restored.role == "user"
        assert len(restored.content) == 2
        assert restored.content[0].type == InputType.TEXT
        assert restored.content[1].type == InputType.AUDIO
        assert restored.content[1].content == "https://example.com/audio.mp3"

    def test_multimodal_mixed_types_roundtrip(self):
        """测试多模态消息序列化 - 混合多种类型"""
        msg = UserMessage(
            role="user",
            content=[
                InputContent(type=InputType.TEXT, content="Check these files"),
                InputContent(type=InputType.IMAGE, content="https://example.com/photo.jpg"),
                InputContent(type=InputType.AUDIO, content="https://example.com/voice.wav"),
                InputContent(type=InputType.VIDEO, content="https://example.com/video.mp4"),
            ]
        )

        packed = msgpack.packb(msg.model_dump(), use_bin_type=True)
        unpacked = msgpack.unpackb(packed, raw=False)
        restored = UserMessage(**unpacked)

        assert restored.role == "user"
        assert len(restored.content) == 4

        # 验证所有类型都正确恢复
        types = [item.type for item in restored.content]
        assert types == [InputType.TEXT, InputType.IMAGE, InputType.AUDIO, InputType.VIDEO]

    def test_enum_serialization_as_string(self):
        """验证 InputType 枚举序列化为字符串值"""
        msg = UserMessage(
            role="user",
            content=[
                InputContent(type=InputType.IMAGE, content="https://example.com/img.png"),
            ]
        )

        dumped = msg.model_dump()

        # 枚举应该被序列化为其字符串值
        assert dumped["content"][0]["type"] == "input_image"

    def test_empty_content_handling(self):
        """测试空内容列表处理"""
        msg = UserMessage(role="user", content=[])

        packed = msgpack.packb(msg.model_dump(), use_bin_type=True)
        unpacked = msgpack.unpackb(packed, raw=False)
        restored = UserMessage(**unpacked)

        assert restored.role == "user"
        assert restored.content == []


class TestMessageListSerialization:
    """测试消息列表（对话历史）的序列化"""

    def test_conversation_history_roundtrip(self):
        """测试完整对话历史序列化"""
        messages = [
            SystemMessage(role="system", content="You are helpful."),
            UserMessage(role="user", content="Hello"),
            AssistantMessage(role="assistant", content="Hi! How can I help?"),
            UserMessage(role="user", content=[
                InputContent(type=InputType.TEXT, content="What's in this image?"),
                InputContent(type=InputType.IMAGE, content="https://example.com/img.png"),
            ]),
            AssistantMessage(role="assistant", content="I see a beautiful landscape."),
        ]

        # 序列化每条消息
        packed_list = [
            msgpack.packb(msg.model_dump(), use_bin_type=True)
            for msg in messages
        ]

        # 反序列化
        restored_messages = [
            Message(**msgpack.unpackb(packed, raw=False))
            for packed in packed_list
        ]

        assert len(restored_messages) == 5

        # 验证角色序列
        roles = [msg.role for msg in restored_messages]
        assert roles == ["system", "user", "assistant", "user", "assistant"]

        # 验证多模态消息
        multimodal_msg = restored_messages[3]
        assert isinstance(multimodal_msg.content, list)
        assert len(multimodal_msg.content) == 2
