from pydantic import BaseModel, Field


class OTPRequest(BaseModel):
    email: str


class OTPVerify(BaseModel):
    email: str
    otp: str = Field(min_length=6, max_length=6)