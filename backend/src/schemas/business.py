from pydantic import BaseModel,Field,field_validator,model_validator
from typing import Literal
class Login(BaseModel):
    email:str
    password:str
class BatchInput(BaseModel):
    code:str=Field(min_length=3,max_length=50,pattern=r"^[A-Za-z0-9_-]+$")
    line:Literal["一线","二线","三线"]
    supplier:str=Field(min_length=1,max_length=80)
    tonnes:float=Field(gt=0,le=10000,allow_inf_nan=False)
    received_date:str
    @field_validator('received_date')
    @classmethod
    def valid_date(cls,v):
        from datetime import date
        date.fromisoformat(v)
        return v
class InspectionInput(BaseModel):
    sample_code:str=Field(min_length=3,max_length=70,pattern=r"^[A-Za-z0-9_-]+$")
    batch_id:int=Field(gt=0)
    flour_yield:float=Field(gt=0,le=100,allow_inf_nan=False)
    moisture:float=Field(ge=0,le=30,allow_inf_nan=False)
    inspector:str=Field(min_length=1,max_length=50)
class ReviewInput(BaseModel):
    title:str=Field(min_length=2,max_length=120)
    line:Literal["全部","一线","二线","三线"]="全部"
    source:Literal["ledger","center"]="ledger"
class ApprovalInput(BaseModel):
    note:str=Field(min_length=5,max_length=1500)
class RepairInput(BaseModel):
    all:bool=False
    codes:list[str]=Field(default_factory=list,max_length=200)
    @field_validator('codes')
    @classmethod
    def valid_codes(cls,v):
        for c in v:
            if not (1<=len(c)<=50):raise ValueError('批次编号长度需在 1-50 之间')
        return v
    @model_validator(mode='after')
    def target(self):
        if not self.all and not self.codes:raise ValueError('请选择要修复的批次，或使用全部修复')
        return self
