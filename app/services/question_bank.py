"""Static fallback question bank, used when the LLM is unavailable.

Seeded from the example questions in the project spec. Keys match
``app.schemas.question.QUESTION_CATEGORIES``.
"""

QUESTION_BANK: dict[str, list[str]] = {
    "Python Core": [
        "Что такое GIL и как он влияет на многопоточность в Python?",
        "Чем list отличается от tuple? Когда выбирать каждый?",
        "Как устроен dict внутри (хеш-таблица, коллизии, порядок ключей)?",
        "Что такое генератор и чем он отличается от обычной функции?",
        "Что такое декоратор? Приведите практический пример.",
        "Чем __new__ отличается от __init__?",
    ],
    "OOP in Python": [
        "Что такое MRO и как Python разрешает множественное наследование?",
        "Чем отличаются @classmethod, @staticmethod и обычный метод?",
        "Что такое дескриптор и где он применяется?",
        "Как работают __slots__ и зачем они нужны?",
        "Чем абстрактный класс отличается от протокола (typing.Protocol)?",
    ],
    "Async Python": [
        "Что такое event loop и как он работает?",
        "Чем async def отличается от обычной def?",
        "Что произойдёт, если вызвать blocking I/O внутри async endpoint?",
        "В чём разница между asyncio.gather и asyncio.create_task?",
        "Как корректно ограничить число одновременных корутин?",
    ],
    "FastAPI": [
        "Как работает dependency injection в FastAPI?",
        "Чем полезен Depends и как строятся цепочки зависимостей?",
        "Как написать middleware в FastAPI?",
        "Как валидируются request/response модели через Pydantic?",
        "Как обрабатывать фоновые задачи (BackgroundTasks)?",
    ],
    "Django": [
        "Что такое lazy loading у QuerySet?",
        "Чем select_related отличается от prefetch_related?",
        "Как работает middleware в Django?",
        "Как устроена Django ORM и что такое менеджеры моделей?",
        "Как избежать проблемы N+1 запросов?",
    ],
    "Flask": [
        "Что такое application context и request context во Flask?",
        "Как устроены blueprints и зачем они нужны?",
        "Как Flask обрабатывает запрос от WSGI до view-функции?",
    ],
    "SQLAlchemy": [
        "Чем отличается Core от ORM в SQLAlchemy?",
        "Что такое session, unit of work и identity map?",
        "Чем lazy отличается от eager loading и как настроить загрузку связей?",
        "Что такое autoflush и expire_on_commit?",
    ],
    "PostgreSQL": [
        "Чем btree-индекс отличается от GIN/GiST и когда выбирать каждый?",
        "Что такое MVCC и как Postgres обеспечивает изоляцию транзакций?",
        "Как читать вывод EXPLAIN ANALYZE?",
        "Чем отличаются уровни изоляции транзакций?",
    ],
    "Redis": [
        "Какие основные структуры данных есть в Redis?",
        "Как реализовать кэш с инвалидацией и TTL?",
        "Чем отличается стратегия cache-aside от write-through?",
        "Как использовать Redis для распределённой блокировки?",
    ],
    "Celery": [
        "Из каких компонентов состоит Celery (broker, worker, backend)?",
        "Чем отличается ack_late и как добиться идемпотентности задач?",
        "Как организовать retry и обработку ошибок в задачах?",
        "Чем apply_async отличается от delay?",
    ],
    "Docker": [
        "Чем образ отличается от контейнера?",
        "Что такое multi-stage build и зачем он нужен?",
        "Как уменьшить размер Python-образа?",
        "Чем CMD отличается от ENTRYPOINT?",
    ],
    "System Design": [
        "Спроектируйте сервис сокращения ссылок (URL Shortener).",
        "Спроектируйте очередь задач (Job Queue).",
        "Спроектируйте систему уведомлений (Notification System).",
        "Спроектируйте rate limiter.",
        "Спроектируйте сервис загрузки файлов (File Upload Service).",
    ],
    "Testing": [
        "Чем отличаются unit, integration и e2e тесты?",
        "Что такое фикстуры в pytest и как управлять их областью видимости?",
        "Как и зачем мокать внешние зависимости?",
        "Как тестировать async-код в pytest?",
    ],
    "Algorithms": [
        "Объясните сложность по времени и памяти основных операций со словарём.",
        "Как развернуть связанный список и какова сложность?",
        "Как обнаружить цикл в связанном списке?",
        "Объясните разницу между BFS и DFS и где применять каждый.",
    ],
}


def get_bank_questions(category: str, count: int) -> list[str]:
    questions = QUESTION_BANK.get(category, [])
    if not questions:
        # Unknown category: fall back to Python Core.
        questions = QUESTION_BANK["Python Core"]
    return questions[:count]
