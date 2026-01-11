"""
音频服务相关异常

包含ASR（自动语音识别）、TTS等音频处理服务的异常定义。
"""

from .base import BaseHTTPException


class AudioServiceException(BaseHTTPException):
    """音频服务异常基类"""
    code = 1500000
    message = "AUDIO_SERVICE_ERROR"
    http_status_code = 500


class AudioConfigurationException(AudioServiceException):
    """音频配置异常"""
    code = 1500001
    message = "AUDIO_CONFIGURATION_ERROR"
    http_status_code = 500

    def __init__(self, audio_service: str):
        super().__init__(detail=f"API_KEY未配置，无法使用{audio_service}相关服务")


class ASRUrlValidationException(AudioServiceException):
    """ASR URL验证异常"""
    code = 1500002
    message = "ASR_URL_VALIDATION_ERROR"
    http_status_code = 400

    def __init__(self, audio_url: str):
        super().__init__(detail=f"无效的音频URL格式: {audio_url}")


class ASRTaskSubmissionException(AudioServiceException):
    """ASR任务提交失败异常"""
    code = 1500003
    message = "ASR_TASK_SUBMISSION_FAILED"
    http_status_code = 500

    def __init__(self):
        super().__init__(detail="ASR任务提交失败")


class ASRTranscriptionException(AudioServiceException):
    """ASR转录失败异常"""
    code = 1500004
    message = "ASR_TRANSCRIPTION_FAILED"
    http_status_code = 500

    def __init__(self, reason: str = ""):
        detail = "ASR转录任务失败"
        if reason:
            detail += f": {reason}"
        super().__init__(detail=detail)


class ASRTimeoutException(AudioServiceException):
    """ASR超时异常"""
    code = 1500005
    message = "ASR_TIMEOUT"
    http_status_code = 408

    def __init__(self, task_id: str, elapsed_time: int):
        super().__init__(detail=f"ASR转录任务超时 - task_id: {task_id}, 已等待: {elapsed_time}秒")


class ASRDownloadException(AudioServiceException):
    """ASR下载失败异常"""
    code = 1500006
    message = "ASR_DOWNLOAD_FAILED"
    http_status_code = 500

    def __init__(self):
        super().__init__(detail="下载转录结果失败")