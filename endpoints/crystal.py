from fastapi import APIRouter, Request
from datetime import datetime
import json, endpoints

router = APIRouter()

@router.post('/postcry/', include_in_schema=False)
async def postcry(request: Request):
    params = await request.json()

    Previous_lospi = endpoints.load_json('./data/lastlospi.json')

    if not (Previous_lospi["Buy"] == params["Buy"]) and (Previous_lospi["Sell"] == params["Sell"]):
        params["Date"] = str(datetime.now())

        with open('./data/lastlospi.json', 'w', encoding='UTF-8') as f:
            json.dump(params, f, ensure_ascii=False, indent=4)

@router.get('/crystal/')
async def crystal():
    """
    최근 크리스탈 시세 정보를 가져옵니다.
    """

    last_lospi = endpoints.load_json('./data/lastlospi.json')
    return {**last_lospi, "Result": "Success"}