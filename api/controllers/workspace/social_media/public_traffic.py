from uuid import UUID
from typing import Annotated
from fastapi import APIRouter, HTTPException, Depends

from utils import get_component_logger


logger = get_component_logger(__name__, "ConversationRouter")

# 创建路由器
router = APIRouter()
