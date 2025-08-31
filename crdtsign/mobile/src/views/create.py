import hashlib
import flet as ft

from datetime import datetime, timedelta

from crdtsign.sign import load_keypair, sign
from utils.storage import file_storage, user

class CreateView:
    def __init__(self, page: ft.Page):
        self.page = page
        self.pick_files_dialog = ft.FilePicker(
            on_result=self.pick_files_result,
        )
        self.selected_file = {
            "file_name": ft.Text("No file selected"),
            "file_digest": "",
            "file_digest_display": ft.Text(),
        }
        self.signing_user = ft.Text(f"{user.username} <{user.user_id.split('user_')[-1]}>")
        self.expiration_date_picker = ft.CupertinoDatePicker(
                                    first_date=datetime.now(),
                                    last_date=datetime.now() + timedelta(days=365),
                                    on_change=self.set_expiration_date,
                                )
        self.expiration_date_text = ft.Text("Not set")
        self.expiration_date = None
        self.submit_button = ft.FilledButton("Submit", disabled=True, on_click=self.on_file_submit)
        self.page.overlay.append(self.pick_files_dialog)

        self.view = ft.View(
            route="/create",
            controls=[
                ft.CupertinoAppBar(
                    leading=ft.IconButton(
                        ft.Icons.ARROW_BACK_IOS, on_click=lambda _: page.go("/")
                    ),
                    title=ft.Text("Sign file"),
                ),
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Row(), # Spacing
                            ft.Row(
                                [
                                    ft.Text("Select a file to sign", size=16),
                                    ft.FilledButton(
                                        "Pick files",
                                        icon=ft.Icons.UPLOAD_FILE,
                                        on_click=lambda _: self.pick_files_dialog.pick_files(
                                            allow_multiple=False
                                        ),
                                    ),
                                ],
                                alignment=ft.MainAxisAlignment.CENTER,
                            ),
                            ft.Row(
                                [
                                    self.selected_file["file_name"],
                                    self.selected_file["file_digest_display"],
                                ],
                                alignment=ft.MainAxisAlignment.CENTER,
                            ),
                            ft.Row(
                                [
                                    ft.Text("Signing user:", weight=ft.FontWeight.BOLD),
                                    self.signing_user,
                                ],
                                alignment=ft.MainAxisAlignment.CENTER,
                            ),
                            ft.Row([ft.FilledButton(
                                "Set expiration date/time",
                                adaptive=True,
                                on_click=lambda e: self.page.open(ft.CupertinoBottomSheet(
                                    content=self.expiration_date_picker,
                                    height=216,
                                    padding=ft.padding.only(top=6),
                                )),
                            ),], alignment=ft.MainAxisAlignment.CENTER),
                            ft.Row(
                                [
                                    ft.Text("Expiration date:", weight=ft.FontWeight.BOLD),
                                    self.expiration_date_text,
                                ],
                                alignment=ft.MainAxisAlignment.CENTER,
                            ),
                            ft.Row(
                                [
                                    self.submit_button,
                                ],
                                alignment=ft.MainAxisAlignment.CENTER,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.START,
                        expand=True,
                    ),
                    padding=10,
                    expand=True,
                ),
            ],
        )

    def pick_files_result(self, e: ft.FilePickerResultEvent):
        self.selected_file["file_name"].value = (
            ", ".join(map(lambda f: f.name, e.files)) if e.files else ""
        )
        self.selected_file["file_name"].weight = ft.FontWeight.BOLD
        if e.files:
            # Read file content and calculate hash
            self.selected_file["file_path"] = e.files[0].path
            with open(self.selected_file["file_path"], 'rb') as f:
                file_content = f.read()
            self.selected_file["file_digest"] = hashlib.sha256(
                file_content
            ).hexdigest()
        self.selected_file["file_digest_display"].value = f"<{self.selected_file['file_digest'][:16]}...>"
        self.selected_file["file_name"].update()
        self.selected_file["file_digest_display"].update()
        self.submit_button.disabled = False
        self.submit_button.update()

    def set_expiration_date(self, e):
        self.expiration_date = e.control.value
        self.expiration_date_text.value = self.expiration_date.strftime('%Y-%m-%d %H:%M:%S')
        self.expiration_date_text.update()

    async def on_file_submit(self, e):
        try:
            private_key, public_key = load_keypair()
            signature = sign(self.selected_file["file_path"], private_key)
            signed_on = datetime.now()
            await file_storage.add_file_signature(
                self.selected_file["file_name"].value,
                self.selected_file["file_digest"],
                signature.hex(),
                user.username,
                user.user_id,
                signed_on,
                self.expiration_date,
                persist=True,
            )

            # Navigate to home and show success message
            self.page.go("/")
            self.page.open(ft.SnackBar(ft.Text(f"File '{self.selected_file['file_name'].value}' was signed successfully.")))

            # Cleanup after successful submission
            self.reset_form()
        except Exception as ex:
            # Show error message if something goes wrong
            self.page.open(ft.SnackBar(ft.Text(f"Error signing file: {str(ex)}")))

    def reset_form(self):
        """Reset the form to initial state"""
        self.selected_file = {
            "file_name": ft.Text("No file selected"),
            "file_digest": "",
            "file_digest_display": ft.Text(),
        }
        self.expiration_date = None
        self.expiration_date_text.value = "Not set"
        self.expiration_date_text.update()
        self.submit_button.disabled = True
        self.submit_button.update()