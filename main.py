from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.exceptions import RequestValidationError
from fastapi.responses import Response
from starlette.responses import RedirectResponse, JSONResponse
from starlette.status import HTTP_422_UNPROCESSABLE_ENTITY, HTTP_429_TOO_MANY_REQUESTS
import uvicorn, endpoints, traceback, logging, uuid
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
from redis.asyncio import Redis
from contextlib import asynccontextmanager

# 로깅 설정: 파일 핸들러 추가
logging.basicConfig(
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("file.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

WHITELISTED_IPS = {"127.0.0.1"}
rate_limiter = RateLimiter(times=15, seconds=60)
async def custom_rate_limiter(request: Request, response: Response):
    # 화이트리스트에 있는 IP는 제한하지 않음
    if request.client.host in WHITELISTED_IPS:
        return
    else:
        return await rate_limiter(request, response)

# Redis, FastAPILimiter 초기화
@asynccontextmanager
async def lifespan(app: FastAPI):
    redis = Redis(host="localhost", port=6379, encoding="utf8")
    await FastAPILimiter.init(redis)
    yield
    redis.close()

app = FastAPI(lifespan=lifespan, dependencies=[Depends(custom_rate_limiter)])

for module_name in endpoints.__all__:
    module = getattr(endpoints, module_name)
    if hasattr(module, "router"):
        app.include_router(module.router, prefix="")

@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")

# HTTPException에 대한 전역 예외 처리
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code == HTTP_429_TOO_MANY_REQUESTS:
        client_ip = request.client.host
        logger.error(f"Rate Limit Exceeded: {exc.detail} - IP: {client_ip}")
        return JSONResponse(
            status_code=HTTP_429_TOO_MANY_REQUESTS,
            content={
                "Result": "Failed",
                "detail": "요청 한도를 초과하였습니다. 잠시 후 다시 시도해주세요. 추가적인 한도 증가는 관리자에게 문의해주세요.",
                "retry_after_seconds": int(exc.headers.get("Retry-After"))
            },
        )
    
    error_id = str(uuid.uuid4())
    tb_info = traceback.format_exc()
    logger.error(f"Error ID {error_id} - HTTPException: {exc.detail} - Traceback: {tb_info}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"Result": "Failed", "detail": "요청 처리 중 오류가 발생했습니다. 관리자에게 문의해주세요.", "error_id": error_id}
    )

# 유효성 검사 오류에 대한 전역 예외 처리
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    error_id = str(uuid.uuid4())
    tb_info = traceback.format_exc()
    logger.error(f"Error ID {error_id} - Validation Error: {exc.errors()} - Traceback: {tb_info}")
    return JSONResponse(
        status_code=HTTP_422_UNPROCESSABLE_ENTITY,
        content={"Result": "Failed", "detail": "입력값이 유효하지 않습니다.", "error_id": error_id}
    )

# 기타 모든 예외에 대한 전역 예외 처리
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    error_id = str(uuid.uuid4())
    tb_info = traceback.format_exc()
    logger.error(f"Error ID {error_id} - Unexpected error: {exc} - Traceback: {tb_info}")
    return JSONResponse(
        status_code=500,
        content={"Result": "Failed", "detail": "알 수 없는 오류가 발생했습니다. 관리자에게 문의하세요.", "error_id": error_id}
    )

if __name__ == "__main__":
    uvicorn.run(app, host='0.0.0.0',port=80)