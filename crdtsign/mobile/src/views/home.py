import flet as ft

from components.file_signature_card_container import FileSignatureCardContainer


class HomeView:
    def __init__(self, page: ft.Page):
        self.page = page
        self.file_signature_card_container = FileSignatureCardContainer(page)
        self.view = ft.View(
            route="/",
            controls=[
                ft.Container(
                    content=ft.Column(
                        [
                            ft.SafeArea(
                                ft.Container(
                                    ft.Column(
                                        [
                                            ft.Text(
                                                "Home page",
                                                color="#3736f9",
                                                text_align=ft.TextAlign.CENTER,
                                                weight=ft.FontWeight.BOLD,
                                                size=42,
                                            ),
                                            ft.Row(
                                                [
                                                    ft.CupertinoButton(
                                                        content=ft.Text(
                                                            "Update", color="#432dd7"
                                                        ),
                                                        # bgcolor=ft.CupertinoColors.LIGHT_BACKGROUND_GRAY,
                                                        opacity_on_click=0.3,
                                                        on_click=lambda _: self.file_signature_card_container.update_container(),
                                                    ),
                                                    ft.CupertinoButton(
                                                        content=ft.Text(
                                                            "Create new",
                                                            color="#432dd7",
                                                        ),
                                                        opacity_on_click=0.3,
                                                        on_click=lambda _: self.page.go(
                                                            "/create"
                                                        ),
                                                        bgcolor="#e0e7ff",
                                                    ),
                                                ],
                                                alignment=ft.MainAxisAlignment.SPACE_EVENLY,
                                                expand=True,
                                            ),
                                            ft.Container(
                                                content=self.file_signature_card_container,
                                                height=self.page.window.height - 200,
                                                expand=False,
                                            ),
                                        ]
                                    )
                                )
                            ),
                        ],
                        spacing=10,
                        alignment=ft.MainAxisAlignment.CENTER,
                        expand=True,
                    ),
                    padding=10,
                )
            ],
            bgcolor="#f3f4f6",
        )
