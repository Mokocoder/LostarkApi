from fastapi import APIRouter, Query
from bs4 import BeautifulSoup
import aiohttp, endpoints, time, re
from . import user_info_formatter

router = APIRouter()

async def get_request(session, url):
    async with session.get(url) as resp:
        response = await resp.text()
        return response
    
async def load_character(session, userName, filters, count=0):
    if count >= 5:
        raise Exception("Too many retries")
    
    filters = filters.replace('+','%2B')
    url = f'https://developer-lostark.game.onstove.com/armories/characters/{userName}?filters={filters}'
    header = {
        'accept': 'application/json',
        'authorization': f'bearer {endpoints.stove_api_tokens[endpoints.auth_index]}'
    }

    async with session.get(url, headers=header) as resp:
        if str(await resp.text()) == "null" :
            time.sleep(int(resp.headers['retry-after']))
            return await load_character(session, userName, filters, count+1)
        
        if int(resp.headers['x-ratelimit-remaining']) < 40:
            endpoints.auth_index = (endpoints.auth_index + 1) % 4

        response = await resp.json()
        return response
    
async def check_profile_status(session, userName, count=0):
    if count >= 5:
        raise Exception("Too many retries")
    
    url = f'https://api.onstove.com/main-common/game-character/lostark/search/characters/{userName}'
    headers = {
        "Host": "api.onstove.com",
        "Authorization": f'bearer {endpoints.SUATkey}'
    }
    
    async with session.get(url, headers=headers) as resp:
        response = await resp.json()
        
        if response['message'] != "OK":
            endpoints.SUATkey = endpoints.load_json('./config/crawl_cache.json')["SUAT"]
            return await check_profile_status(session, userName, count+1)
        
        return response

async def load_siblings(session, userName, count=0):
    if count >= 5:
        raise Exception("Too many retries")
    
    url = f'https://developer-lostark.game.onstove.com/characters/{userName}/siblings'
    header = {
        'accept': 'application/json',
        'authorization': f'bearer {endpoints.stove_api_tokens[endpoints.auth_index]}'
    }

    async with session.get(url, headers=header) as resp:
        if str(await resp.text()) == "null" :
            time.sleep(int(resp.headers['retry-after']))
            return await load_siblings(session, userName, count+1)
        
        if int(resp.headers['x-ratelimit-remaining']) < 40:
            endpoints.auth_index = (endpoints.auth_index + 1) % 4

        response = await resp.json()
        return {
            "Siblings": response,
            "Result": "Success"
        }

@router.get('/sasa')
async def sasa(name: str = Query(..., min_length=1, max_length=12)):
    """
    최근 1만개의 게시글 중 {name}과 관련성이 있는 사사게 정보를 가져옵니다.
    """
    
    conn=aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=conn) as session:
        checker = await get_request(session, f'https://lostark.game.onstove.com/Profile/Character/{name}')
        if "캐릭터 정보가 없습니다." in checker:
            return {"Result":"Failed","Reason":"Not Found"}
        
        userinfo = await load_character(session, name, "profiles")
        
        if userinfo['Result'] == "Failed":
            return {"Result":"Failed","Reason":userinfo["Reason"]}
        
        userServer = userinfo['ArmoryProfile']['ServerName']
        sasaurl = f'https://www.inven.co.kr/board/lostark/5355?query=list&p=1&category={userServer}&sterm=&name=subjcont&keyword={name}'

        sasa = await get_request(session, sasaurl)
        sasasoup = BeautifulSoup(sasa, 'html.parser')

        search_result = {
            "SasaList": [],
            "SasaUrl": sasaurl,
            "Result": "Success"
        }

        links = sasasoup.select('#new-board > form > div > table > tbody > tr > td.tit > div > div > a')

        if len(links) > 1:
            max_items = min(len(links) - 1, 5)

            for link in links[1:max_items + 1]:
                title = link.text.replace("\r\n", "").strip()[len(userServer) + 3:]
                search_result["SasaList"].append(title)
        else:
            search_result["SasaList"].append("최근 1만 게시글 중 (제목/내용) 검색 결과가 없습니다.")

        return search_result

@router.get("/userinfo")
async def userinfo(name: str = Query(..., min_length=1, max_length=12), filters: str = "profiles+equipment+avatars+combat-skills+engravings+cards+gems+colosseums+collectibles+characterlist"):
    """
    {name} 캐릭터의 정보를 가져옵니다.
    만약 정지를 당했다면 해당 캐릭터의 프로필 및 원정대 정보를 가져옵니다.

    profiles+equipment+avatars+combat-skills+engravings+cards+gems+colosseums+collectibles+characterlist 의 항목들을 지원합니다.
    default는 모두 다 반환입니다.

    filters Parameter에 원하는 항목을 적으면 해당 항목만 반환합니다.
    ex) profiles+equipment -> 프로필과 장비정보만 반환
    
    캐시 유효기간은 30초입니다.
    """
    
    value = endpoints.cache_30s.get(f'userinfo:{name}:{filters}')
    if value is not None:
        value["Cached"] = True
        return value
            
    async with aiohttp.ClientSession() as session:                
        checker = await get_request(session, f'https://lostark.game.onstove.com/Profile/Character/{name}')
        if "캐릭터 정보가 없습니다." in checker:
            return (await suspended_userinfo(name))
            # return {"Result": "Failed", "detail": "Not Found"}

        response = await load_character(session, name, filters)

        # with open('./test.json', 'w', encoding='UTF-8') as f:
        #     json.dump(response, f, ensure_ascii=False, indent=4)

        search_result = {"Result": "Success"}
        
        if "profiles" in filters:
            basic = user_info_formatter.process_basic(response, name)
            search_result.update(basic)

        if "equipment" in filters:
            equipment = user_info_formatter.process_equipment(response)
            search_result.update(equipment)
        
        if "avatars" in filters:
            avatars = user_info_formatter.process_avatars(response)
            search_result.update(avatars)

        if "engravings" in filters:
            engravings = user_info_formatter.process_engravings(response)
            search_result.update(engravings)

        if "cards" in filters:
            cards = user_info_formatter.process_card(response)
            search_result.update(cards)

        if "gems" in filters:
            gems = user_info_formatter.process_gems(response)
            search_result.update(gems)

        if "collectibles" in filters:
            collectibles = user_info_formatter.process_collectibles(response)
            search_result.update(collectibles)

        if "colosseums" in filters:
            search_result.update({"ColosseumInfo":response['ColosseumInfo']})

        if "characterlist" in filters:
            sblings = await load_siblings(session, name)
            expedition_infos = user_info_formatter.process_characterlist(sblings, name)
            search_result.update(expedition_infos)

        if "combat-skills" in filters:
            skills = user_info_formatter.process_combat_skills(response)
            search_result.update(skills)

        endpoints.cache_30s[f'userinfo:{name}:{filters}'] = search_result
        return {**search_result, "Cached": False}

@router.get('/verysimple_userinfo')
async def verysimple_userinfo(name: str = Query(..., min_length=1, max_length=12)):
    """
    매우 간단한 {name} 캐릭터의 기초 정보를 가져옵니다.

    캐시 유효기간은 30초입니다.
    """
    
    cache_data = endpoints.cache_30s.get(f'verysimple_userinfo:{name}')

    if cache_data is not None:
        return {**cache_data, "Cached": True}
    
    async with aiohttp.ClientSession() as session:
        checker = await get_request(session, f'https://lostark.game.onstove.com/Profile/Character/{name}')

        if "캐릭터 정보가 없습니다." in checker:
            return {"Result":"Failed","Reason":"Not Found"}
        
        response = await load_character(session, name, "profiles")

        if int(response['ArmoryProfile']['ItemAvgLevel'].replace(",","").replace(".","")) > 0:
            result = {"Result": "Success", "itemAvgLevel": int(response['ArmoryProfile']['ItemAvgLevel'].replace(",","").replace(".",""))/100, "pcClassName": response['ArmoryProfile']['CharacterClassName'], "pcName": name}
            endpoints.cache_30s[f'verysimple_userinfo:{name}'] = result
            return {**result, "Cached": False}
        else:
            return {"Result": "Failed", "detail": "Not enough level"}
        
@router.get("/getward", include_in_schema=False)
async def getward(name: str = Query(..., min_length=1, max_length=12)):
    async with aiohttp.ClientSession() as session:
        rawdata = await get_request(session, f'https://lostark.game.onstove.com/Profile/Character/{name}')
        
        if "캐릭터 정보가 없습니다." in rawdata:
            return {"Result": "Failed", "detail": "Not Found"}

        _memberNo = re.findall("var _memberNo = '(.+?)';", rawdata)[0]
        
        return {"Result": "Success", "Ward": _memberNo}
    
@router.get("/useward", include_in_schema=False)
async def getward(ward: str = Query(..., min_length=1)):
    async with aiohttp.ClientSession() as session:
        rawdata = await get_request(session, f'https://lostark.game.onstove.com/Profile/Member?id={ward}')
        
        if "캐릭터 정보가 없습니다." in rawdata:
            return {"Result": "Failed", "detail": "Not Found"}

        _pcName = re.findall("var _pcName = '(.+?)';", rawdata)[0]
        return (await userinfo(_pcName))
    
@router.get('/suspended_userinfo')
async def suspended_userinfo(name: str = Query(..., min_length=1, max_length=12)):
    """
    {name} 캐릭터의 정지 여부를 알려줍니다.
    
    Example name : 그린대표

    캐시 유효기간은 30초입니다.
    """

    cache_data = endpoints.cache_30s.get(f'suspended_userinfo:{name}')

    if cache_data is not None:
        return {**cache_data, "Cached": True}
    
    async with aiohttp.ClientSession() as session:
        checker = await get_request(session, f'https://lostark.game.onstove.com/Profile/Character/{name}')
        
        if "캐릭터 정보가 없습니다." not in checker:
            return{"Result": "Passed", "detail": "해당 캐릭터는 정지상태가 아닙니다."}
        
        response = await check_profile_status(session, name)

        if len(response['value']) > 0:
            search_result = {
                "Result":"Suspended",
                "detail": "해당 캐릭터는 100% 정지상태입니다.",
                "CharacterList": response['value']
            }
        else:
            search_result = {"Result": "Unknown", "detail": "해당 캐릭터는 정지 여부를 알 수 없습니다."}
        
        endpoints.cache_30s[f'suspended_userinfo:{name}'] = search_result
        return {**search_result, "Cached": False}