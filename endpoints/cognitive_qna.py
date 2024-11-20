from fastapi import APIRouter, Query
from endpoints import retriever, model

router = APIRouter()

async def search_ask(query):
    relevant = await retriever.aget_relevant_documents(query)
    
    if len(relevant) > 0:
        contents = [element.page_content for element in relevant]
        resources = [element.metadata['id'] for element in relevant]

        prompt = f"""당신은 게임 로스트아크에 대한 질문에 답하는 인공지능 비서입니다. 주어진 문서에 있는 내용만 사용하여 답변을 제공하세요. 문서 : {contents} 질문 : {query} 답변 :"""
        response = (await model.generate_content_async(prompt)).text.strip()

        return {"Result":"Success", "Answer":response, "Resources":resources}
    else:
        return {"Result":"Success", "Answer":"흠, 그건 모르겠어요.\n'로스트아크의' 를 앞에 붙여보는건 어떠신가요?\n\n혹은 아래 참고 문서란에 있는 위키에 해당 질문과 관련된 문서를 작성해주세요.\nAi도우미가 빠른 시일내에 해당 내용을 배우고 도울 수 있습니다.", "Resources":["start"]}

@router.get('/cognitive_qna', include_in_schema=False)
async def cognitive_qna(question: str = Query(..., min_length=1, max_length=400)):
    result = await search_ask(question)
    return result