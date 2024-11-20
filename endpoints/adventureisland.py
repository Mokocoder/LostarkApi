from fastapi import APIRouter
from datetime import datetime, timedelta
import endpoints, json, time, aiohttp

router = APIRouter()

async def Refresh_Calendar(session, keyDate, fsttime, count=0):
    if count >= 5:
        raise Exception("Too many retries")
    
    url = 'https://developer-lostark.game.onstove.com/gamecontents/calendar'
    header = {
        'accept': 'application/json',
        'authorization': f'bearer {endpoints.stove_api_tokens[endpoints.auth_index]}'
    }

    async with session.get(url, headers=header) as resp:
        if str(await resp.text()) == "null" :
            time.sleep(int(resp.headers['retry-after']))
            return await Refresh_Calendar(session, keyDate, fsttime, count+1)
        
        if int(resp.headers['x-ratelimit-remaining']) < 40:
            endpoints.auth_index = (endpoints.auth_index + 1) % 4
            
        response = await resp.json()

        Adv_Calendar = {}
        Reward_history = {}

        for element in (e for e in response if e['CategoryName'] == '모험 섬'):
            contents_name = element['ContentsName']
            Reward_history.setdefault(contents_name, [])

            for date in element.get('StartTimes', []):
                Adv_Calendar.setdefault(date, {})[contents_name] = ""
                for reward in element['RewardItems'][0]['Items']:
                    if reward['Name'] in ['골드', '전설 ~ 고급 카드 팩 III', '해적 주화', '실링']:
                        reward_name = reward['Name'].replace('전설 ~ 고급 카드 팩 III', '카드').replace('해적 주화', '주화')
                        Adv_Calendar[date][contents_name] = reward_name
                        
                        if reward_name not in Reward_history[contents_name]:
                            Reward_history[contents_name].append(reward_name)

        for date, islands in Adv_Calendar.items():
            for island, value in islands.items():
                if value == "":
                    Adv_Calendar[date][island] = Reward_history[island][0]

        lastest_island = {
            "IslandDate": fsttime+" 시작",
            "Island": [{"Name": key, "Reward": Adv_Calendar[keyDate][key]} for key in Adv_Calendar[keyDate]]
        }
        
        with open('./data/calendar.json', 'w', encoding='UTF-8') as f:
            json.dump(Adv_Calendar, f, ensure_ascii=False, indent=4, sort_keys=True)

        with open('./data/island.json', 'w', encoding='UTF-8') as f:
            json.dump(lastest_island, f, ensure_ascii=False, indent=4)

        return Adv_Calendar, lastest_island

@router.get('/adventureisland/')
async def adventureisland():
    """
    다음 시간의 모험섬 정보를 가져옵니다.
    """

    lastest_island = endpoints.load_json('./data/island.json')
    lastest_date = datetime.strptime(
        lastest_island['IslandDate'].replace(" 시작","")[2:].replace("-","/"),
        '%y/%m/%d %H:%M'
    )
    now = datetime.now()

    totalsecond = (lastest_date - now).total_seconds()

    if (totalsecond > 10):
        return {**lastest_island, "Result": "Success"}
    
    Adv_Calendar = endpoints.load_json('./data/calendar.json')

    available_times = [11, 13, 19, 21, 23]
    for t in available_times:
        if now.hour < t:
            suspect_h = str(t)
            break
    else:
        suspect_h = "11"
        now += timedelta(days=1)
    
    date_part = now.strftime("%Y-%m-%d")
    keyDate = f"{date_part}T{suspect_h}:00:00"
    fsttime = f"{date_part} {suspect_h}:00"

    if (keyDate in Adv_Calendar):
        lastest_island = {
            "IslandDate": fsttime+" 시작",
            "Island": [{"Name": key, "Reward": Adv_Calendar[keyDate][key]} for key in Adv_Calendar[keyDate]]
        }

        with open('./data/island.json', 'w', encoding='UTF-8') as f:
            json.dump(lastest_island, f, ensure_ascii=False, indent=4)

        return {**lastest_island, "Result": "Success"}
    
    async with aiohttp.ClientSession() as session:
        _, lastest_island = await Refresh_Calendar(session, keyDate, fsttime)
        return {**lastest_island, "Result": "Success"}

@router.get('/adventure_calendar/')
async def adventure_calendar():
    """
    일주일간의 모험섬 캘린더 정보를 가져옵니다.
    """
    
    Adv_Calendar = endpoints.load_json('./data/calendar.json')
    lastest_date = datetime.strptime(
        list(Adv_Calendar.keys())[-1].replace("T"," ").replace("-","/")[2:],
        '%y/%m/%d %H:%M:%S'
    )
    now = datetime.now()
    
    totalsecond = (lastest_date - now).total_seconds()

    if (totalsecond > 10):
        return {**Adv_Calendar, "Result": "Success"}
    
    available_times = [11, 13, 19, 21, 23]
    for t in available_times:
        if now.hour < t:
            suspect_h = str(t)
            break
    else:
        suspect_h = "11"
        now += timedelta(days=1)

    date_part = now.strftime("%Y-%m-%d")
    keyDate = f"{date_part}T{suspect_h}:00:00"
    fsttime = f"{date_part} {suspect_h}:00"

    async with aiohttp.ClientSession() as session:
        Adv_Calendar, _ = await Refresh_Calendar(session, keyDate, fsttime)

    return {**Adv_Calendar, "Result": "Success"}