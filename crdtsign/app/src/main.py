import flet as ft


class CrdtSignApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.current_view = "main"
        self.next_card_id = 1
        self.expanded_card_id = None

        self.page_setup()

        self.page.navigation_bar = self.create_navigation_bar()

        self.show_current_view()

    def page_setup(self):
        self.page.title = "crdtSign"
        self.page.theme_mode = ft.ThemeMode.SYSTEM
        self.page.spacing = 0
        self.page.padding = 0

        self.page.window.width = 400
        self.page.window.height = 800
        self.page.window.resizable = False

        if (
            self.page.platform == ft.PagePlatform.ANDROID
            or self.page.platform == ft.PagePlatform.IOS
        ):
            self.page.window.full_screen = True
        self.create_views_container()
        self.set_main_view()
        self.set_create_view()

    def create_navigation_bar(self):
        """Create bottom navigation bar"""
        return ft.CupertinoNavigationBar(
            destinations=[
                ft.NavigationBarDestination(label="Browse", icon=ft.Icons.VIEW_LIST),
                ft.NavigationBarDestination(label="Create", icon=ft.Icons.ADD),
            ],
            on_change=self.handle_navigation_change,
            selected_index=0,
        )

    def handle_navigation_change(self, e):
        """Handle navigation between views"""
        if self.current_view == "main":
            e.control.selected_index = 1
            self.current_view = "create"
        else:
            e.control.selected_index = 0
            self.current_view = "main"

        self.show_current_view()

    def show_current_view(self):
        if self.current_view == "main":
            self.main_view_container.offset = ft.Offset(0, 0)
            self.create_view_container.offset = ft.Offset(1, 0)
        else:
            self.main_view_container.offset = ft.Offset(-1, 0)
            self.create_view_container.offset = ft.Offset(0, 0)

        if len(self.page.controls) == 0:
            self.page.controls.clear()
            self.page.add(
                ft.Container(
                    content=self.views_container,
                    expand=True,
                )
            )
        self.page.update()

    def set_main_view(self):
        self.main_view_container.content = ft.Container(
            content=ft.Row(
                [
                    ft.SafeArea(
                        ft.Text("Main view", text_align=ft.TextAlign.CENTER),
                        expand=True,
                    )
                ]
            ),
            alignment=ft.alignment.center,
            expand=True,
        )

    def set_create_view(self):
        self.create_view_container.content = ft.Container(
            content=ft.Row(
                [
                    ft.SafeArea(
                        ft.Text("Create view", text_align=ft.TextAlign.CENTER),
                        expand=True,
                    )
                ]
            ),
            alignment=ft.alignment.center,
            expand=True,
        )

    def create_views_container(self):
        self.main_view_container = ft.Container(
            content=None,
            animate_offset=ft.Animation(
                duration=250, curve=ft.AnimationCurve.EASE_IN_OUT
            ),
            offset=ft.Offset(0, 0),
            expand=True,
        )

        self.create_view_container = ft.Container(
            content=None,
            animate_offset=ft.Animation(
                duration=250, curve=ft.AnimationCurve.EASE_IN_OUT
            ),
            offset=ft.Offset(1, 0),
            expand=True,
        )

        self.views_container = ft.Container(
            content=ft.Stack(
                [
                    self.main_view_container,
                    self.create_view_container,
                ],
                expand=True,
            ),
            expand=True,
        )


def main(page: ft.Page):
    """Main entry point"""
    app = CrdtSignApp(page)


if __name__ == "__main__":
    ft.app(main)
