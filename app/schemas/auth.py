from pydantic import BaseModel, EmailStr, Field

class PasswordResetRequestSchema(BaseModel):
    email: EmailStr

class NewPasswordSchema(BaseModel):
    token: str
    new_password: str = Field(min_length=8) # Example: Enforce min password length
