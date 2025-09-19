import flet as ft
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Callable

from utils.storage import file_storage, user_storage
from crdtsign.sign import is_verified_signature, load_public_key


@dataclass
class FileSignature:
    file_id: str
    file_name: str
    file_hash: str
    signature: str
    signed_by: str
    signed_id: str
    signed_at: datetime
    expiration_date: Optional[datetime] = None


class FileSignatureCard:
    def __init__(
        self,
        file_signature: FileSignature,
        delete_callback: Callable[[FileSignature], None],
    ):
        self.file_id = file_signature.file_id
        self.file_name = file_signature.file_name
        self.file_hash = file_signature.file_hash
        self.signature = file_signature.signature
        self.signed_by = file_signature.signed_by
        self.signed_id = file_signature.signed_id
        self.signed_at = file_signature.signed_at
        self.expiration_date = file_signature.expiration_date
        self.delete_callback = delete_callback
        self.expand_icon = ft.Icon(ft.Icons.EXPAND_MORE)
        self.expanded = False

        # Create the card control
        self.card = ft.Card(content=self.build_card_content(), color="#ffffff")

    def toggle_expand(self, e):
        self.expanded = not self.expanded
        self.card.content = self.build_card_content()
        self.card.update()

    def build_card_content(self):
        base_content = [
            ft.CupertinoListTile(
                notched=True,
                title=ft.Text(self.file_name),
                subtitle=ft.Text(
                    f"{self.signed_by} <{self.signed_id.split('user_')[-1]}>"
                ),
                additional_info=ft.Text(
                    f"{datetime.strftime(self.signed_at, '%Y-%m-%d %H:%M:%S')}"
                ),
                leading=ft.Icon(ft.Icons.FILE_PRESENT, color="#3736f9"),
                on_click=self.toggle_expand,
            ),
        ]

        if self.expanded:
            base_content.extend(
                [
                    ft.Divider(),
                    ft.Text(f"File Hash: {self.file_hash}"),
                    ft.Text(f"Signature: {self.signature}"),
                    ft.Text(
                        f"Signed At: {datetime.strftime(self.signed_at, '%Y-%m-%d %H:%M:%S')}"
                    ),
                    ft.Text(
                        f"Expiration Date: {datetime.strftime(self.expiration_date, '%Y-%m-%d %H:%M:%S')}"
                        if self.expiration_date
                        else "No expiration date"
                    ),
                    ft.Row(
                        [
                            ft.CupertinoButton(
                                content=ft.Text("Delete"),
                                color=ft.CupertinoColors.SYSTEM_RED,
                                on_click=self.delete_card,
                            ),
                            ft.CupertinoButton(
                                content=ft.Text("Validate"),
                                color=ft.CupertinoColors.SYSTEM_GREEN,
                                on_click=self.verify_signature,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.END,
                        expand=True,
                    ),
                    ft.Container(height=10),  # Spacing
                ]
            )

        return ft.Container(
            content=ft.Column(base_content, spacing=5),
            padding=10,
        )

    async def delete_card(self, e):
        """Show confirmation dialog and delete card if confirmed"""

        async def on_confirm_delete(e):
            await file_storage.remove_file_signature(self.file_id, persist=True)
            # Remove card from stack by ID
            self.delete_callback(self)
            dlg.open = False
            e.page.open(ft.SnackBar(ft.Text(f"File '{self.file_name}' was deleted.")))
            e.page.update()

        def on_cancel_delete(e):
            dlg.open = False
            e.page.update()

        # Create confirmation dialog
        dlg = ft.AlertDialog(
            modal=True,
            adaptive=True,
            title=ft.Text("Confirm Deletion"),
            content=ft.Text(
                f"Are you sure you want to delete '{self.file_name}'? This action cannot be undone."
            ),
            actions=[
                ft.TextButton("Cancel", on_click=on_cancel_delete),
                ft.TextButton(
                    "Delete",
                    on_click=on_confirm_delete,
                    style=ft.ButtonStyle(color=ft.CupertinoColors.SYSTEM_RED),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        e.page.open(dlg)

    def verify_signature(self, e):
        if self.expiration_date and self.expiration_date < datetime.now().astimezone(
            datetime.now().tzinfo
        ):
            e.page.open(
                ft.SnackBar(
                    ft.Text(
                        f"Signature for '{self.file_name}' has EXPIRED ({datetime.strftime(self.expiration_date, '%Y-%m-%d %H:%M:%S')}).",
                        color="#531b15",
                    ),
                    bgcolor="#e3b7b4",
                )
            )
            return
        else:
            public_key_hex = user_storage.get_user_public_key(self.signed_id)
            public_key = load_public_key(bytes.fromhex(public_key_hex))
            verified = is_verified_signature(
                bytes.fromhex(self.file_hash), bytes.fromhex(self.signature), public_key
            )
            if verified:
                e.page.open(
                    ft.SnackBar(
                        ft.Text(
                            f"Signature for '{self.file_name}' is VALID."
                            + (
                                f" Signature is valid until {datetime.strftime(self.expiration_date, '%Y-%m-%d %H:%M:%S')}."
                                if self.expiration_date
                                else " No expiration date set."
                            ),
                            color="#122608",
                        ),
                        bgcolor="#cbf0b7",
                    ),
                )
            else:
                e.page.open(
                    ft.SnackBar(
                        ft.Text(f"Signature for '{self.file_name}' is NOT VALID.")
                    )
                )
