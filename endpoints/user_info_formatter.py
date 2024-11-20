import re, json, endpoints

def extract_tooltip_data(tooltip):
    def clean_html(text):
        return re.sub(r"<[^>]*FONT[^>]*>", "", text).strip()

    Quality = None
    Advanced_Reforge = None
    Elixir, Transcendence, Plus, Engrave, Basic, ArkPassive, Grinding = [], [], [], [], [], [], []

    for sub_element in tooltip:
        data = tooltip[sub_element]
        value = data.get('value', {})

        if data['type'] == "ItemTitle":
            Quality = str(value.get('qualityValue', -1)) if value.get('qualityValue') != -1 else None
        elif data['type'] == "SingleTextBox" and "상급 재련" in value:
            Advanced_Reforge = clean_html(value)
        elif data['type'] == "IndentStringGroup" and value:
            for element_key, element_data in value.items():
                top_str = element_data['topStr'].strip()

                if "엘릭서" in top_str and not Elixir:
                    Elixir = [
                        re.sub(r"<[^>]*FONT[^>]*>", "", element_data['contentStr'][key]['contentStr']).split('<br>')[0].strip()
                        for key in element_data['contentStr']
                    ]
                elif "초월" in top_str and not Transcendence:
                    Transcendence = [
                        clean_html(top_str)
                        .replace("<img src='emoticon_Transcendence_Grade' width='18' height='18' vspace ='-4'></img>", "{ GradeEmoji } ")
                        .replace("슬롯 효과<BR>", "").strip(),
                        element_data['contentStr']['Element_000']['contentStr'].strip()
                    ]
                elif "각인 효과" in top_str and not Engrave:
                    Engrave = [
                        {
                            "EngraveName": engrave.split("활성도")[0].strip(),
                            "Effect": engrave.split("활성도")[1].strip()
                        }
                        for engrave in [
                            clean_html(item['contentStr']).replace("<BR>","").replace("[","").replace("]","")
                            for item in element_data['contentStr'].values()
                        ]
                    ]
                elif "아크 패시브" in top_str and not ArkPassive:
                    ArkPassive = [
                        clean_html(element_data['contentStr'][key]['contentStr']).split('<BR>')[0]
                        .replace("<img src='emoticon_tooltip_ability_stone_symbol' width='11' height='14' vspace ='-2'></img>", "{ emoticon_ability_stone_blue } ").strip()
                        for key in element_data['contentStr']
                    ]
        elif data['type'] == "ItemPartBox":
            element_000 = value.get('Element_000', "")
            element_001 = value.get('Element_001', "")
            
            if "기본 효과" in element_000 and not Basic:
                Basic = [effect.strip() for effect in element_001.split("<BR>") if "#686660" not in effect]
            elif "추가 효과" in element_000 and not Plus:
                Plus = [effect.strip() for effect in element_001.split("<BR>")]
            elif "세공 단계 보너스" in element_000 and not Plus:
                Plus = [effect.strip() for effect in element_001.split("<BR>")]
            elif "팔찌 효과" in element_000 and not Plus:
                Plus = [
                    effect.strip() for effect in clean_html(element_001)
                    .replace("<img src='emoticon_tooltip_bracelet_locked' vspace='-5'></img>", "[잠김] ")
                    .replace("<img src='emoticon_tooltip_bracelet_changeable' width='20' height='20' vspace='-6'></img>", "[변경가능] ")
                    .replace("  ", " ")
                    .split("<BR>")
                ]
            elif "아크 패시브" in element_000 and not ArkPassive:
                ArkPassive = [effect.strip() for effect in element_001.split("<BR>")]
            elif "연마 효과" in element_000 and not Grinding:
                Grinding = [
                    effect.strip() for effect in clean_html(element_001)
                    .replace("<img src='emoticon_sign_greenDot' width='0' height='0' vspace='-3'></img>", "")
                    .split("<BR>")
                ]         

    return Quality, Advanced_Reforge, Elixir, Transcendence, Plus, Engrave, Basic, ArkPassive, Grinding

def process_weapon_armor(element, tooltip):
    Quality, Advanced_Reforge, Elixir, Transcendence, Plus, _, Basic, ArkPassive, _ = extract_tooltip_data(tooltip)
    return {
        "Name": element["Name"],
        "Quality": Quality,
        "Basic": Basic or None,
        "Plus": Plus or None,
        "Advanced_Reforge": Advanced_Reforge or None,
        "Elixir": Elixir or None,
        "Transcendence": Transcendence or None,
        "ArkPassive": ArkPassive or None
    }

def process_accessory(element, tooltip):
    Quality, _, _, _, Plus, Engrave, Basic, ArkPassive, Grinding = extract_tooltip_data(tooltip)
    return {
        "Name": element["Name"],
        "Quality": Quality,
        "Basic": Basic or None,
        "Plus": Plus or None,
        "Engrave": Engrave or None,
        "ArkPassive": ArkPassive or None,
        "Grinding": Grinding or None
    }

def process_ability_stone(element, tooltip):
    _, _, _, _, Plus, Engrave, Basic, ArkPassive, _ = extract_tooltip_data(tooltip)
    return {
        "Name": element["Name"],
        "Plus": Plus or None,
        "Basic": Basic or None,
        "Engrave": Engrave or None,
        "ArkPassive": ArkPassive or None
    }

def process_bracelet_item(element, tooltip):
    _, _, _, _, Plus, _, _, ArkPassive, _ = extract_tooltip_data(tooltip)
    return {
        "Name": element["Name"],
        "Plus": Plus or None,
        "ArkPassive": ArkPassive or None
    }

def process_misc_item(element, tooltip):
    _, _, _, _, Plus, *_ = extract_tooltip_data(tooltip)
    return {
        "Name": element["Name"],
        "Plus": Plus or None
    }

def process_equipment(response):
    if not response['ArmoryEquipment']:
        return {"Items": None}
    
    equipment_types = [
        "무기", "머리 방어구", "상의", "하의", "장갑", "어깨 방어구",
        "목걸이", "귀걸이1", "귀걸이2", "반지1", "반지2",
        "어빌리티 스톤", "팔찌",
        "나침반", "부적", "문장"
    ]
    equipment = {"Items": {etype: None for etype in equipment_types}}

    for element in response['ArmoryEquipment']:
        item_type = element['Type']
        tooltip = json.loads(element['Tooltip'])
        
        if item_type in ["무기","투구","상의","하의","장갑","어깨"]:
            if item_type == "투구":
                item_type = "머리 방어구"
            elif item_type == "어깨":
                item_type = "어깨 방어구"

            equipment["Items"][item_type] = process_weapon_armor(element, tooltip)
        if item_type in ["목걸이","귀걸이","반지"]:
            if item_type == "귀걸이":
                item_type = "귀걸이1" if not equipment["Items"]["귀걸이1"] else "귀걸이2"
            elif item_type == "반지":
                item_type = "반지1" if not equipment["Items"]["반지1"] else "반지2"

            equipment["Items"][item_type] = process_accessory(element, tooltip)
        if item_type == "어빌리티 스톤":
            equipment["Items"][item_type] = process_ability_stone(element, tooltip)
        if item_type == "팔찌":
            equipment["Items"][item_type] = process_bracelet_item(element, tooltip)
        if item_type in ["나침반","부적","문장"]:
            equipment["Items"][item_type] = process_misc_item(element, tooltip)

    return equipment

def calculate_gold(level):
    def calculate_gold_for_rewards(reward_dict):
        unique_raids = set()
        total_raids = []
        total_gold = 0
        tries = 0

        for raid, details in reward_dict.items():
            if tries >= 3:
                break
            if level >= details["LevelMin"] and level < details["LevelMax"]:
                raid_name = raid.split('[')[0].strip()
                if raid_name not in unique_raids:
                    unique_raids.add(raid_name)
                    total_raids.append(raid)
                    total_gold += details["Gold"]
                    tries += 1

        return total_gold, total_raids

    final_low, raids_low = calculate_gold_for_rewards(endpoints.gold_reward_low)
    final_high, raids_high = calculate_gold_for_rewards(endpoints.gold_reward_high)

    return final_low, raids_low, final_high, raids_high

def process_characterlist(sblings, name):
    expedition_infos = {
        "Gold": {
            "GoldList": [],
            "TotalGoldLow": 0,
            "TotalGoldHigh": 0
        },
        "CharacterList": []
    }

    MainServer = next((c['ServerName'] for c in sblings['Siblings'] if c['CharacterName'] == name), None)
    
    for character in sblings['Siblings']:
        expedition_infos['CharacterList'].append({
            "Class": character['CharacterClassName'],
            "Level": "Lv." + str(character['ItemAvgLevel']),
            "Name": character['CharacterName'],
            "Server": character['ServerName'],
            "Combat_Level": "Lv." + str(character['CharacterLevel'])
        })

        if MainServer and character['ServerName'] == MainServer:
            expedition_infos["Gold"]["GoldList"].append({
                "Class": character['CharacterClassName'],
                "Name": character['CharacterName'],
                "Level": "Lv." + str(character['ItemAvgLevel']),
            })

    expedition_infos["Gold"]["GoldList"] = sorted(
        expedition_infos["Gold"]["GoldList"],
        key=lambda x: float(x['Level'].replace('Lv.', '').replace(',', '')),
        reverse=True
    )[:6]
    
    for char in expedition_infos["Gold"]["GoldList"]:
        gold_low, raids_low, gold_high, raids_high = calculate_gold(float(char["Level"].replace("Lv.", "").replace(',', '')))
        char.update({
            "Low": {"Gold": gold_low, "Raids": raids_low},
            "High": {"Gold": gold_high, "Raids": raids_high}
        })
        expedition_infos["Gold"]["TotalGoldLow"] += gold_low
        expedition_infos["Gold"]["TotalGoldHigh"] += gold_high

    return expedition_infos

def process_basic(response, name):
    en_cl = endpoints.english_class.get(response['ArmoryProfile']['CharacterClassName'], "specialist")

    basic = {
        "Basic":{
            "Name": name,
            "Server": response['ArmoryProfile']['ServerName'],
            "Guild": response['ArmoryProfile']['GuildName'],
            "GuildMemberGrade": response['ArmoryProfile']['GuildMemberGrade'],
            "PvpGradeName": response['ArmoryProfile']['PvpGradeName'],
            "Title": response['ArmoryProfile']['Title'],
            "Class": {
                "Name": response['ArmoryProfile']['CharacterClassName'],
                "Icon": f'https://cdn-lostark.game.onstove.com/2018/obt/assets/images/common/thumb/emblem_{en_cl}.png'
            },
            "Level": {
                "Expedition": 'Lv.' + str(response['ArmoryProfile']['ExpeditionLevel']),
                "Battle": 'Lv.' + str(response['ArmoryProfile']['CharacterLevel']),
                "Item": 'Lv.' + str(response['ArmoryProfile']['ItemAvgLevel'])
            },
            "Tendency": {key: str(tend['Point']) for key, tend in zip(
                ["Intellect", "Bravery", "Charm", "Kindness"], response['ArmoryProfile']['Tendencies']
            )},
            "SkillPoint": {
                "Total": str(response['ArmoryProfile']['TotalSkillPoint']),
                "Used": str(response['ArmoryProfile']['UsingSkillPoint'])
            },
            "Stat": None if response['ArmoryProfile']['Stats'] is None else {
                stat_name: response['ArmoryProfile']['Stats'][index]['Value'] 
                for stat_name, index in zip(
                    ["Attack", "Health", "Critical", "Specialty", "Subdue", "Agility", "Endurance", "Proficiency"],
                    [7, 6, 0, 1, 2, 3, 4, 5]
                )
            },
            "Wisdom": None if response['ArmoryProfile']['TownLevel'] is None else {
                "Name": response['ArmoryProfile']['TownName'],
                "Level": f"Lv.{response['ArmoryProfile']['TownLevel']}"
            }
        },
        "Avatar_img":response['ArmoryProfile']['CharacterImage']
    }

    return basic

def process_engravings(response):
    if not response['ArmoryEngraving']:
        return {"Engravings": None}
    
    engravings = {"Engravings": []}
    effects = response['ArmoryEngraving'].get('Effects', []) or response['ArmoryEngraving'].get('ArkPassiveEffects', [])
    
    for effect in effects:
        if 'AbilityStoneLevel' in effect:
            engravings["Engravings"].append(
                f"{effect['Name']}"
                + (f" {{ emoticon_ability_stone_blue }} Lv. {effect['AbilityStoneLevel']}" if effect['AbilityStoneLevel'] else "")
                + f" {{ emoticon_engrave_grade_relic }} Lv. {effect['Level']}"
            )
        else:
            engravings["Engravings"].append(
                effect['Name'].replace("Lv.", "{ emoticon_ability_stone_blue } Lv.")
            )

    return engravings

def parse_effect(effect_text):
    if "피해" in effect_text:
        skill, remainder = effect_text.rsplit("피해", 1)
        effect_type, extra = remainder.rsplit("추가 효과", 1)
        return skill.strip(), "피해 " + effect_type.strip(), extra.strip()
    elif "재사용 대기시간" in effect_text:
        skill, remainder = effect_text.rsplit("재사용", 1)
        effect_type, extra = remainder.rsplit("추가 효과", 1)
        return skill.strip(), "재사용 " + effect_type.strip(), extra.strip()
    return "", "", ""

def process_gems(response):
    if not response['ArmoryGem']:
        return {"Jewl": None}
    
    gems = {"Jewl": []}
    gem_data = response['ArmoryGem'].get('Gems', [])
    
    for element in gem_data:
        tooltip_text = re.sub('<[^>]+>', '', element['Tooltip'])
        tooltip = json.loads(tooltip_text)
        jewl  = {}

        for key, value in tooltip.items():
            if value.get('type') == "NameTagBox":
                jewl["JewlName"] = value['value']

            elif value.get('type') == "ItemPartBox" and value['value'].get('Element_000') == "효과":
                effect_text = re.sub(r"\[(.*?)\] ", "", value['value']['Element_001'])
                skill, effect_type, extra = parse_effect(effect_text)
                jewl.update({"SkillName": skill, "Effect": effect_type, "Plus": extra})

        gems['Jewl'].append(jewl)
    
    return gems

def process_avatars(response):
    if not response['ArmoryAvatars']:
        return {"Avatars": None}
    
    return {
        "Avatars": [
            f"{element['Grade']} {element['Name']}"
            for element in response['ArmoryAvatars']
        ]
    }

def process_card(response):
    if not response['ArmoryCard']:
        return {"Card": None, "CardList": None}
    
    return {
        "Card": [
            {"Name": item['Name'], "Effect": item['Description']}
            for effect in response['ArmoryCard'].get('Effects', [])
            for item in effect.get('Items', [])
        ],
        "CardList": [
            {
                "Awake": f"{card['AwakeCount']}/{card['AwakeTotal']}",
                "Name": card['Name'],
                "Tier": card['Grade']
            }
            for card in response['ArmoryCard'].get('Cards', [])
        ]
    }

def process_collectibles(response):
    return {
        "Collections": [
            {"Name": collect['Type'], "Point": f"{collect['Point']} / {collect['MaxPoint']}"}
            for collect in response['Collectibles']
        ]
    }

def process_combat_skills(response):
    if not response['ArmorySkills']:
        return {"Skill": None}
    
    skills = {"Skill": []}

    for skill in response['ArmorySkills']:
        if skill['Level'] > 1 or skill['Rune']:
            temp_skill = {
                "Name": skill['Name'],
                "Level": skill['Level'],
                "Tri": {
                    f"Tier_{t['Tier']}": {
                        "Name": t['Name'],
                        "Level": t['Level'],
                        "Slot": str(t['Slot'])
                    }
                    for t in skill['Tripods'] if t['IsSelected']
                } or None,
                "Rune": f"{skill['Rune']['Grade']} {skill['Rune']['Name']}" if skill['Rune'] else None
            }
            skills['Skill'].append(temp_skill)

    return skills