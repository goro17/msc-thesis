import hashlib
import flet as ft


class CreateView:
    def __init__(self, page: ft.Page):
        self.page = page
        self.pick_files_dialog = ft.FilePicker(
            on_result=self.pick_files_result,
        )
        self.selected_file = {
            "file_name": ft.Text(),
            "file_digest": ft.Text(),
        }
        self.page.overlay.append(self.pick_files_dialog)

        self.view = ft.View(
            route="/",
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
                                    ft.ElevatedButton(
                                        "Pick files",
                                        icon=ft.Icons.UPLOAD_FILE,
                                        on_click=lambda _: self.pick_files_dialog.pick_files(
                                            allow_multiple=False
                                        ),
                                    ),
                                    self.selected_file["file_name"],
                                    self.selected_file["file_digest"],
                                ]
                            )
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
            ", ".join(map(lambda f: f.name, e.files)) if e.files else "Cancelled!"
        )
        if e.files:
            # Read file content and calculate hash
            file_path = e.files[0].path
            with open(file_path, 'rb') as f:
                file_content = f.read()
            self.selected_file["file_digest"].value = hashlib.sha256(
                file_content
            ).hexdigest()
        self.selected_file["file_name"].update()
        self.selected_file["file_digest"].update()
