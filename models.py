from pydantic import BaseModel
from typing import List, Dict, Optional, Union

class FunctionParameter(BaseModel):
    type: str
    properties: Dict[str, Dict[str, str]]
    required: List[str]

# 定义 Function 模型
class Function(BaseModel):
    name: str
    description: str
    parameters: FunctionParameter

# 定义 Tool 模型
class Tool(BaseModel):
    type: str
    function: Function

class ImageUrl(BaseModel):
    url: str

class ContentItem(BaseModel):
    type: str
    text: Optional[str] = None
    image_url: Optional[ImageUrl] = None

class Message(BaseModel):
    role: str
    name: Optional[str] = None
    arguments: Optional[str] = None
    content: Union[str, List[ContentItem]]

class RequestModel(BaseModel):
    model: str
    messages: List[Message]
    logprobs: Optional[bool] = None
    top_logprobs: Optional[int] = None
    stream: Optional[bool] = False
    include_usage: Optional[bool] = None
    temperature: Optional[float] = 0.5
    top_p: Optional[float] = 1.0
    max_tokens: Optional[int] = None
    presence_penalty: Optional[float] = 0.0
    frequency_penalty: Optional[float] = 0.0
    n: Optional[int] = 1
    user: Optional[str] = None
    tool_choice: Optional[str] = None
    tools: Optional[List[Tool]] = None