from zero_semester.bot.handlers import menu, modules, practices, secrets, start, support

routers = [
    start.router,
    menu.router,
    modules.router,
    practices.router,
    secrets.router,
    support.router,
]

__all__ = ["routers"]
