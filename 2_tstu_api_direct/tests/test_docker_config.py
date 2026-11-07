# test_docker_config.py
# Тесты конфигурационных файлов Docker, Docker Compose и переменных окружения

import os
import pytest

currentDir = os.path.dirname(os.path.abspath(__file__))
parentDir = os.path.dirname(currentDir)


class TestDockerConfig:

    def test_dockerfile_structure(self):
        dockerfilePath = os.path.join(parentDir, "Dockerfile")
        assert os.path.exists(dockerfilePath), "Dockerfile must exist"

        with open(dockerfilePath, "r", encoding="utf-8") as f:
            content = f.read()

        assert "FROM python:3.11-slim" in content
        assert "WORKDIR /app" in content
        assert "requirements.txt" in content
        assert "pip install" in content
        assert "ENTRYPOINT" in content
        assert "EXPOSE 8081" in content
        assert "ENV PYTHONUNBUFFERED=1" in content

    def test_docker_compose_structure(self):
        composePath = os.path.join(parentDir, "docker-compose.yml")
        assert os.path.exists(composePath), "docker-compose.yml must exist"

        with open(composePath, "r", encoding="utf-8") as f:
            content = f.read()

        # Проверка ключевых сервисов
        assert "radicale:" in content
        assert "tstu-schedule:" in content
        assert "tomsquest/docker-radicale" in content
        assert "5232:5232" in content
        assert "radicale_data:" in content
        assert "depends_on:" in content

        # Проверка переменных окружения
        assert "SCHEDULE_GROUP" in content
        assert "RADICALE_URL" in content
        assert "EXPORT_RADICALE" in content
        assert "EXPORT_ICS" in content

    def test_env_files_consistency(self):
        envExamplePath = os.path.join(parentDir, ".env.example")
        envPath = os.path.join(parentDir, ".env")

        assert os.path.exists(envExamplePath), ".env.example must exist"
        assert os.path.exists(envPath), ".env must exist"

        with open(envExamplePath, "r", encoding="utf-8") as f:
            exampleContent = f.read()

        with open(envPath, "r", encoding="utf-8") as f:
            envContent = f.read()

        requiredVars = [
            "SCHEDULE_GROUP",
            "RADICALE_URL",
            "RADICALE_USER",
            "RADICALE_CALENDAR",
            "EXPORT_RADICALE",
            "EXPORT_ICS",
            "EXPORT_EXCEL",
            "EXPORT_JSON",
            "SEMESTER_START_DATE",
            "SEMESTER_END_DATE",
            "PORT"
        ]

        for var in requiredVars:
            assert var in exampleContent, f"{var} should be in .env.example"
            assert var in envContent, f"{var} should be in .env"

    def test_dockerignore(self):
        dockerignore = os.path.join(parentDir, ".dockerignore")
        assert os.path.exists(dockerignore), ".dockerignore must exist"
        with open(dockerignore, "r", encoding="utf-8") as f:
            content = f.read()
        assert "__pycache__" in content
        assert ".git" in content
        assert ".env" in content

    def test_requirements_file(self):
        reqPath = os.path.join(parentDir, "requirements.txt")
        assert os.path.exists(reqPath), "requirements.txt must exist"
        with open(reqPath, "r", encoding="utf-8") as f:
            reqs = f.read().lower()
        assert "requests" in reqs
        assert "beautifulsoup4" in reqs
        assert "openpyxl" in reqs
