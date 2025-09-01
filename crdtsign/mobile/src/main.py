import flet as ft
import asyncio

from views.create import CreateView
from views.home import HomeView
from views.registration import RegistrationView

from pathlib import Path
from crdtsign.user import User
from crdtsign.storage import FileSignatureStorage, UserStorage
from crdtsign.sign import new_keypair

from utils.storage import user, user_storage, file_storage



def setup_user(user: User, new_username: str):
    if not user.username:
        # Re-initialize user with the provided username
        user = User(username=new_username)

        _, public_key = new_keypair(persist=True)

        # Add the new user to storage
        user_storage.add_user(
            user.username,
            user.user_id,
            public_key.public_bytes_raw().hex(),
            user.registration_date,
            persist=True,
        )

class CRDTSignApp:
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

        self.home_view = HomeView(self.page)
        self.create_view = CreateView(self.page)
        self.registration_view = self.create_registration_view()

        if self.page.platform == ft.PagePlatform.ANDROID or ft.PagePlatform.IOS:
            self.page.window.full_screen = True

        self.page.scroll = ft.ScrollMode.ALWAYS

        self.page.update()

        self.page.on_route_change = self.handle_route_change
        # self.page.on_view_pop = self.handle_view_pop

        if not user.username:
            self.page.go("/registration")
        else:
            self.page.go(self.page.route)

    def handle_route_change(self, route):
        self.page.views.clear()
        # Always refresh the container when navigating to home
        if hasattr(self.home_view, 'file_signature_card_container'):
            self.home_view.file_signature_card_container.update_container()
        self.page.views.append(self.home_view.view)
        if self.page.route == "/create":
            self.page.views.append(self.create_view.view)
        if self.page.route == "/registration":
            self.page.views.append(self.registration_view)
        self.page.update()

    def handle_view_pop(self, view):
        self.page.views.pop()
        top_view = self.page.views[-1]
        self.page.go(top_view.route)

    def handle_username_submit(self, e):
        # Get the username from the text field
        new_username = self.username_field.value

        if new_username and new_username.strip():
            setup_user(user, new_username)
            self.page.go("/")
            self.page.update()
        else:
            # Show error if username is empty
            self.username_field.error_text = "Username cannot be empty"
            self.page.update()

    def create_registration_view(self):
        # Create the text field and store a reference to it
        self.username_field = ft.TextField(
            autofocus=True,
            label="Username",
            on_submit=self.handle_username_submit
        )

        return ft.View(
            route="/registration",
            controls=[
                ft.CupertinoAppBar(
                    title=ft.Text("Welcome to CRDTSign"),
                ),
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text("Please enter a username to get started. This username will be associated with your signatures and cannot be changed later."),
                            self.username_field,
                            ft.FilledButton(text="Register", on_click=self.handle_username_submit),
                        ],
                    ),
                ),
            ],
        )

async def main(page: ft.Page):
    """Main entry point"""
    await user_storage.connect()
    await file_storage.connect()
    app = CRDTSignApp(page)


if __name__ == "__main__":
    ft.app(main, view=ft.AppView.WEB_BROWSER)
