from pydantic import BaseModel, field_validator


class ScopedConfig(BaseModel):
    """Plugin Config Here"""

    app_id: str
    """智能体编辑页面 → 概览 → 后端服务API → APPID"""

    app_token: str
    """智能体编辑页面 → 概览 → 后端服务API → API 密钥 → 密钥"""

    api_base: str = "https://agent.bit.edu.cn/api/proxy/api/v1"
    """智能体编辑页面 → 概览 → 后端服务API → API访问凭据"""

    user_id: str = "通讯官"
    """终端用户的标识
    
    “方便检索、统计”，“由开发者定义规则，需保证用户标识在应用内唯一”。
    然而目前完全匿名，随意定个固定值即可。
    """

    @field_validator("api_base")
    @classmethod
    def check_api_base(cls, v: str) -> str:
        assert v.endswith("/v1")
        return v


class Config(BaseModel):
    chat: ScopedConfig
