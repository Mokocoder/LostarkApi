from fastapi import APIRouter, Query
from bs4 import BeautifulSoup
from endpoints import itemlist
import aiohttp, endpoints, time

router = APIRouter()

async def get_CategoryCodeList(session, count=0):
    if count >= 5:
        raise Exception("Too many retries")
    
    url = 'https://developer-lostark.game.onstove.com/markets/options'
    header = {
        'accept': 'application/json',
        'authorization': f'bearer {endpoints.stove_api_tokens[endpoints.auth_index]}'
    }

    async with session.get(url, headers=header) as resp:
        if str(await resp.text()) == "null" :
            time.sleep(int(resp.headers['retry-after']))
            return await get_CategoryCodeList(session, count+1)
        
        if int(resp.headers['x-ratelimit-remaining']) < 40:
            endpoints.auth_index = (endpoints.auth_index + 1) % 4

        response = await resp.json()

        return [categorie['Code'] for categorie in response['Categories'] if categorie['Code'] != 20000] # 아바타 제외

async def get_itemlist(session, CategoryCode, PageNo, count=0):
    if count >= 5:
        raise Exception("Too many retries")
    
    url = 'https://developer-lostark.game.onstove.com/markets/items'
    header = {
        'accept': 'application/json',
        'authorization': f'bearer {endpoints.stove_api_tokens[endpoints.auth_index]}'
    }
    datas = {
        "Sort": "GRADE",
        "CategoryCode": CategoryCode,
        "PageNo": PageNo,
        "SortCondition": "ASC"
    }

    async with session.post(url, headers=header, data=datas) as resp:
        if str(await resp.text()) == "null" :
            time.sleep(int(resp.headers['retry-after']))
            return await get_CategoryCodeList(session, count+1)
    
        if int(resp.headers['x-ratelimit-remaining']) < 40:
            endpoints.auth_index = (endpoints.auth_index + 1) % 4

        response = await resp.json()

        result = {}

        for item in response['Items']:
            name_key = f"{item['Grade']} {item['Name']}"
            
            if item.get('BundleCount', 1) > 1:
                name_key += f" [{item['BundleCount']}개 단위 판매]"
            if item['TradeRemainCount']:
                name_key += f" [구매 시 거래 {item['TradeRemainCount']}회 가능]"

            result[name_key] = {"Id": item['Id'], "BundleCount": item['BundleCount']}

        return result, response['TotalCount']

@router.get('/get_itemlist/', include_in_schema=False)
async def get_itemlist():
    itemlist = {}
    
    async with aiohttp.ClientSession() as session:
        CategoryCodeList = await get_CategoryCodeList(session)
        
        for CategoryCode in CategoryCodeList:
            pagenum = 1

            while(True):
                response, TotalCount = await get_itemlist(session, CategoryCode, pagenum)
            
                while(len(response) < 1 and pagenum > 1):
                    time.sleep(2)
                    response, TotalCount = await get_itemlist(session, CategoryCode, pagenum)                        

                itemlist.update(response)

                if (TotalCount - 10*pagenum) < 1:
                    break
                
                pagenum += 1
        
        # with open('./data/itemlist.json', 'w', encoding='UTF-8') as f:
        #     json.dump(itemlist, f, ensure_ascii=False, indent=4)

        return itemlist

@router.get('/search_item')
async def search_item(name: str = Query(...), page: int = Query(0, ge=0)):
    """
    이름에 {name}이 들어가는 아이템의 거래소 정보를 검색합니다.
    이름의 길이가 짧은순으로 반환합니다.
    """
    
    name = name.replace("%20"," ")
    # hangul = re.compile('[^ ㄱ-ㅣ가-힣+]')
    # name = hangul.sub('', name)

    if len(name) < 2:
        return {"Result": "Failed", "detail": "Less than 2 characters"}
    
    matches = [key for key in itemlist if name in key]
    TotalCount = len(matches)

    matches.sort(key=len)
    matches = matches[page*10:page*10+10]

    if not matches:
        return {"Result": "Failed", "detail": "No Result"} 
    
    first_match = matches[0]

    return {
        "Result": "Success",
        "Data": matches,
        "Page": page,
        "TotalCount": TotalCount,
        "FirstItem": {
            "name": first_match,
            "id": itemlist[first_match]['Id'],
            "BundleCount": itemlist[first_match]['BundleCount']
        }
    }

async def crawl_item_price(session, itemnumber, isbelong=False, count=0):
    if count >= 5:
        raise Exception("Too many retries")
    
    url = f'https://lostark.game.onstove.com/Market/GetMarketPurchaseInfo?itemNo={itemnumber}'
    if isbelong:
        url += '&belongCode=1&tradeCompleteCount=0&bundleCount=1&_=1646580666673'

    headers = {
        "Host": "lostark.game.onstove.com",
        "Connection": "keep-alive",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    }
    cookies = {
        "SUAT": endpoints.SUATkey,
    }
    
    async with session.get(url, headers=headers ,cookies=cookies) as resp:
        response = await resp.text()

        if (response == "") or ("Bad request" in response) or ("잠시 후 다시" in response) or ("페이지에 오류가 있습니다." in response) or ("Error: Bad request" in response):
            endpoints.SUATkey = endpoints.load_json('./config/crawl_cache.json')["SUAT"]
            return await crawl_item_price(session, itemnumber, False, count+1)
        
        if (("새로고침" not in response) and ("물품 구매" in response)):
            return await crawl_item_price(session, itemnumber, True, count+1)
            
        return response

@router.get('/get_item_price')
async def get_item_price(itemnumber: int = Query(..., ge=0)):
    """
    {itemnumber}아이템의 거래소 시세를 가져옵니다. {itemnumber}와 BundleCount는 search_item에서 얻을 수 있습니다.

    캐시 유효기간은 10초입니다.
    """
    
    cache_data = endpoints.cache_10s.get(f'get_item_price:{itemnumber}')
    
    if cache_data is not None:
        return {**cache_data, "Result": "Success", "Cached": True}
    
    conn=aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=conn) as session:
        response = await crawl_item_price(session, itemnumber)
        
        soup = BeautifulSoup(response, 'html.parser')
        productname = soup.select_one("#modal-deal-exchange > div > div > div.lui-modal__content > div.box-left > div.item-info > span.name").text
        productpicture = soup.select_one("#modal-deal-exchange > div > div > div.lui-modal__content > div.box-left > div.item-info > span.slot > img")['src']

        result = {
            "Name":productname,
            "Image":productpicture,
            "Pricechart":[]
        }
    
        if len(soup.select('td > div > em')) > 0:
            for i in range(0,len(soup.select('td > div > em'))):
                result["Pricechart"].append({
                    "Price":soup.select('td > div > em')[i].text,
                    "Amount":soup.select('#modal-deal-exchange > div > div > div.lui-modal__content > div.box-left > div.info-box.info-box--body > table > tbody > tr > td:nth-child(2) > div')[i].text
                })
        
        endpoints.cache_10s[f'get_item_price:{itemnumber}'] = result

        return {**result, "Result": "Success", "Cached": False}