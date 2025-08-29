import flet as ft

from views.create import CreateView
from views.home import HomeView


class CrdtSignApp:
    def __init__(self, page: ft.Page):
        """App startup"""
        self.page = page
        self.page.title = "crdtSign"
        self.page.theme_mode = ft.ThemeMode.SYSTEM
        self.page.theme = ft.Theme(
            page_transitions=ft.PageTransitionsTheme(
                android=ft.PageTransitionTheme.CUPERTINO,
                ios=ft.PageTransitionTheme.CUPERTINO,
                macos=ft.PageTransitionTheme.CUPERTINO,
                linux=ft.PageTransitionTheme.CUPERTINO,
                windows=ft.PageTransitionTheme.CUPERTINO,
            )
        )
        self.page.padding = 0
        self.page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

        self.page.window.width = 400
        self.page.window.height = 800
        self.page.window.resizable = False

        if self.page.platform == ft.PagePlatform.ANDROID or ft.PagePlatform.IOS:
            self.page.window.full_screen = True

        self.page.scroll = ft.ScrollMode.ALWAYS

        self.page.update()

        self.page.on_route_change = self.handle_route_change
        # self.page.on_view_pop = self.handle_view_pop
        self.page.go(self.page.route)
        print(f"Initial route: {self.page.route}")

    def handle_route_change(self, route):
        self.page.views.clear()
        self.page.views.append(HomeView(self.page).view)
        if self.page.route == "/create":
            self.page.views.append(CreateView(self.page).view)

        self.page.update()

    def handle_view_pop(self, view):
        self.page.views.pop()
        top_view = self.page.views[-1]
        self.page.go(top_view.route)


def main(page: ft.Page):
    """Main entry point"""
    app = CrdtSignApp(page)


if __name__ == "__main__":
    ft.app(main, view=ft.AppView.WEB_BROWSER)
