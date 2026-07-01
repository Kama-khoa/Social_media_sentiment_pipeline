@echo off
echo ==========================================
echo   STARTING BACKEND, REDIS, AND WEB-DB
echo ==========================================
echo.

REM Command to start backend. Docker compose will automatically start redis and web-db
REM because backend depends on them in docker-compose.yml
docker compose --env-file .env -f docker/docker-compose.yml up backend -d

echo.
echo ==========================================
echo   SUCCESS: Backend stack is starting!
echo ==========================================
echo To view backend logs:
echo   docker compose -f docker/docker-compose.yml logs -f backend
echo.
pause
