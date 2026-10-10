from pydantic import BaseModel


class VersionInfo(BaseModel):
    name: str
    version: str
