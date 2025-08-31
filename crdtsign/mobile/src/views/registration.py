import flet as ft

class RegistrationView:
    def __init__(self, page: ft.Page):
        self.page = page
        self.view = ft.View(
            route="/registration",
            controls=[
                ft.CupertinoAppBar(
                    title=ft.Text("Welcome to CRDTSign"),
                ),
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text("Please enter a username to get started. This username will be associated with your signatures and cannot be changed later."),
                            ft.TextField(autofocus=True, label="Username", on_submit=lambda _: self.page.go("/")),
                            ft.FilledButton(text="Register", on_click=lambda _: self.page.go("/")),
                        ],
                    ),
                ),
            ],
        )

    def handle_username_submit(self, e):
        # Send the username to the backend
        self.current_user.username = e.control.value
        self.page.go("/")