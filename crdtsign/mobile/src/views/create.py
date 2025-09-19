import hashlib
import flet as ft
import os

from datetime import datetime, timedelta

from crdtsign.sign import load_keypair, sign
from utils.storage import file_storage, user


class CreateView:
    def __init__(self, page: ft.Page):
        self.page = page
        self.pick_files_dialog = ft.FilePicker(
            on_result=self.pick_files_result,
            on_upload=self.on_upload_progress,
        )
        self.selected_file = {
            "file_name": ft.Text("No file selected"),
            "file_digest": "",
            "file_digest_display": ft.Text(),
        }
        self.signing_user = ft.Text(
            f"{user.username} <{user.user_id.split('user_')[-1]}>"
        )
        self.expiration_date_picker = ft.CupertinoDatePicker(
            first_date=datetime.now(),
            last_date=datetime.now() + timedelta(days=365),
            on_change=self.set_expiration_date,
        )
        self.expiration_date_text = ft.Text("Not set")
        self.expiration_date = None
        self.submit_disabled = True
        self.submit_button = ft.CupertinoButton(
            "Sign file",
            color=ft.Colors.WHITE,
            bgcolor="#4f39f6",
            disabled=True,
            on_click=self.on_file_submit,
        )
        self.page.overlay.append(self.pick_files_dialog)

        self.view = ft.View(
            route="/create",
            controls=[
                ft.CupertinoAppBar(
                    leading=ft.IconButton(
                        ft.Icons.ARROW_BACK_IOS,
                        icon_color="#3736f9",
                        on_click=lambda _: page.go("/"),
                    ),
                    title=ft.Text("Sign file", color="#3736f9"),
                ),
                ft.Container(
                    ft.Card(
                        content=ft.Column(
                            [
                                ft.Row(),
                                ft.Row(
                                    [
                                        ft.Text("Select a file to sign", size=16),
                                        ft.FilledButton(
                                            "Pick file",
                                            color="#432dd7",
                                            bgcolor="#e0e7ff",
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
                                        ft.Text(
                                            "Signing user:", weight=ft.FontWeight.BOLD
                                        ),
                                        self.signing_user,
                                    ],
                                    alignment=ft.MainAxisAlignment.CENTER,
                                ),
                                ft.Row(
                                    [
                                        ft.FilledButton(
                                            "Set expiration date/time",
                                            color="#432dd7",
                                            adaptive=True,
                                            on_click=lambda e: self.page.open(
                                                ft.CupertinoBottomSheet(
                                                    content=self.expiration_date_picker,
                                                    height=216,
                                                    padding=ft.padding.only(top=6),
                                                )
                                            ),
                                        ),
                                    ],
                                    alignment=ft.MainAxisAlignment.CENTER,
                                ),
                                ft.Row(
                                    [
                                        ft.Text(
                                            "Expiration date:",
                                            weight=ft.FontWeight.BOLD,
                                        ),
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
                                ft.Row(),
                            ],
                            alignment=ft.MainAxisAlignment.CENTER,
                            expand=True,
                        ),
                        color="#ffffff",
                    ),
                    padding=20,
                    expand=False,
                ),
            ],
            bgcolor="#f3f4f6",
        )

    def pick_files_result(self, e: ft.FilePickerResultEvent):
        try:
            if e.files:
                self.selected_file["file_name"].value = e.files[0].name
                self.selected_file["file_name"].weight = ft.FontWeight.BOLD
                self.selected_file["original_name"] = e.files[0].name

                print(f"File selected: {e.files[0].name}")

                # Show uploading status
                self.selected_file["file_digest_display"].value = "Uploading..."
                self.selected_file["file_name"].update()
                self.selected_file["file_digest_display"].update()

                # Create upload file list for Flet's upload method
                upload_list = [
                    ft.FilePickerUploadFile(
                        e.files[0].name,
                        upload_url=self.page.get_upload_url(
                            e.files[0].name, 60
                        ),  # 60 second timeout
                    )
                ]

                # Start upload using Flet's upload method
                self.pick_files_dialog.upload(upload_list)

            else:
                self._reset_file_selection()

        except Exception as e:
            print(f"Error in pick_files_result: {e}")
            self.page.open(
                ft.SnackBar(
                    ft.Text(f"Error selecting file: {str(e)}"), bgcolor=ft.Colors.RED
                )
            )
            self._reset_file_selection()

    def on_upload_progress(self, e: ft.FilePickerUploadEvent):
        """Handle file upload progress and completion"""
        try:
            print(f"Upload progress: {e.file_name} - {e.progress * 100:.1f}%")

            if e.progress == 1.0:  # Upload completed
                print(f"Upload completed: {e.file_name}")

                # Get the uploaded file path
                upload_dir = os.getenv("FLET_APP_STORAGE_TEMP")
                uploaded_file_path = os.path.join(upload_dir, e.file_name)

                print(f"Looking for uploaded file at: {uploaded_file_path}")

                if os.path.exists(uploaded_file_path):
                    # Read the uploaded file and calculate hash
                    try:
                        with open(uploaded_file_path, "rb") as f:
                            file_content = f.read()

                        # Calculate hash from uploaded file
                        file_hash = hashlib.sha256(file_content).hexdigest()

                        # Store file info
                        self.selected_file["file_digest"] = file_hash
                        self.selected_file["file_path"] = uploaded_file_path

                        # Update UI
                        self.selected_file[
                            "file_digest_display"
                        ].value = f"<{file_hash[:16]}...>"
                        self.selected_file["file_digest_display"].update()

                        # Enable submit button
                        self.submit_button.disabled = False
                        self.submit_disabled = False
                        self.submit_button.update()

                        print(f"File hash calculated: {file_hash[:16]}...")

                    except Exception as read_error:
                        print(f"Error reading uploaded file: {read_error}")
                        self.page.open(
                            ft.SnackBar(
                                ft.Text(
                                    f"Error reading uploaded file: {str(read_error)}"
                                ),
                                bgcolor=ft.Colors.RED,
                            )
                        )
                        self._reset_file_selection()
                else:
                    print(f"Uploaded file not found at: {uploaded_file_path}")
                    self.page.open(
                        ft.SnackBar(
                            ft.Text("Error: Uploaded file not found"),
                            bgcolor=ft.Colors.RED,
                        )
                    )
                    self._reset_file_selection()
            else:
                # Show upload progress
                progress_percent = e.progress * 100
                self.selected_file[
                    "file_digest_display"
                ].value = f"Uploading... {progress_percent:.1f}%"
                self.selected_file["file_digest_display"].update()

        except Exception as ex:
            print(f"Error in on_upload_progress: {ex}")
            self.page.open(
                ft.SnackBar(ft.Text(f"Upload error: {str(ex)}"), bgcolor=ft.Colors.RED)
            )
            self._reset_file_selection()

    def _reset_file_selection(self):
        """Helper to reset file selection state"""
        self.selected_file["file_name"].value = "No file selected"
        self.selected_file["file_name"].weight = ft.FontWeight.NORMAL
        self.selected_file["file_digest_display"].value = ""
        self.submit_button.disabled = True
        self.selected_file["file_name"].update()
        self.selected_file["file_digest_display"].update()
        self.submit_button.update()

    def set_expiration_date(self, e):
        self.expiration_date = e.control.value
        self.expiration_date_text.value = self.expiration_date.strftime(
            "%Y-%m-%d %H:%M:%S"
        )
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
            self.page.open(
                ft.SnackBar(
                    ft.Text(
                        f"File '{self.selected_file['file_name'].value}' was signed successfully."
                    )
                )
            )
            # Cleanup after successful submission
            self.reset_form()

            # Navigate to home and show success message
            self.page.go("/")

        except Exception as ex:
            self.page.open(ft.SnackBar(ft.Text(f"Error signing file: {str(ex)}")))

    def _cleanup_uploaded_file(self):
        if "file_path" in self.selected_file and self.selected_file["file_path"]:
            uploaded_file_path = self.selected_file["file_path"]
            try:
                if os.path.exists(uploaded_file_path):
                    os.remove(uploaded_file_path)
                    print(f"Cleaned up uploaded file: {uploaded_file_path}")
            except Exception as e:
                print(f"Error cleaning up uploaded file: {e}")

    def reset_form(self):
        """Reset the form to initial state"""
        # Clean up any existing uploaded file
        self._cleanup_uploaded_file()
        self.selected_file["file_name"].value = "No file selected"
        self.selected_file["file_name"].weight = ft.FontWeight.NORMAL
        self.selected_file["file_digest_display"].value = ""
        self.selected_file["file_name"].update()
        self.expiration_date = None
        self.expiration_date_text.value = "Not set"
        self.expiration_date_text.update()
        self.submit_button.disabled = True
        self.submit_button.update()
