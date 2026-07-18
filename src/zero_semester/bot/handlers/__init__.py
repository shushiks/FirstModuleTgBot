from zero_semester.bot.handlers import menu, modules, secrets, start, support

routers = [start.router, menu.router, modules.router, secrets.router, support.router]

__all__ = ["routers"]
