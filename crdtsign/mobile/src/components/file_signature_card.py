import flet as ft
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Callable

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
    def __init__(self, file_signature: FileSignature, delete_callback: Callable[[FileSignature], None]):
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
        self.card = ft.Card(content=self.build_card_content())

    def toggle_expand(self, e):
        self.expanded = not self.expanded
        self.card.content = self.build_card_content()
        self.card.update()

    def build_card_content(self):
        base_content = [
            ft.CupertinoListTile(
                notched=True,
                title=ft.Text(self.file_name),
                subtitle=ft.Text(f"{self.signed_by} <{self.signed_id}>"),
                additional_info=ft.Text(f"{datetime.strftime(self.signed_at, '%Y-%m-%d %H:%M:%S')}"),
                leading=ft.Icon(ft.Icons.FILE_PRESENT),
                on_click=self.toggle_expand,
            ),
        ]

        if self.expanded:
            base_content.extend([
                ft.Divider(),
                ft.Text(f"File Hash: {self.file_hash}"),
                ft.Text(f"Signature: {self.signature}"),
                ft.Text(f"Signed At: {datetime.strftime(self.signed_at, '%Y-%m-%d %H:%M:%S')}"),
                ft.Text(f"Expiration Date: {datetime.strftime(self.expiration_date, '%Y-%m-%d %H:%M:%S')}" if self.expiration_date else "No expiration date"),
                ft.Row([
                    ft.CupertinoButton(
                        content=ft.Text("Delete"),
                        color=ft.CupertinoColors.SYSTEM_RED,
                        on_click=self.delete_card,
                    ),
                    ft.CupertinoButton(
                        content=ft.Text("Verify Signature"),
                        color=ft.CupertinoColors.SYSTEM_GREEN,
                    ),
                ], alignment=ft.MainAxisAlignment.END, expand=True),
                ft.Container(height=10),  # Spacing
            ])
        
        return ft.Container(
            content=ft.Column(base_content, spacing=5),
            padding=10,
        )

    def delete_card(self, e):
        """Show confirmation dialog and delete card if confirmed"""
        def on_confirm_delete(e):
            # Remove card from stack by ID
            self.delete_callback(self)
            dlg.open = False
            e.page.update()

        def on_cancel_delete(e):
            dlg.open = False
            e.page.update()

        # Create confirmation dialog
        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Confirm Deletion"),
            content=ft.Text(f"Are you sure you want to delete '{self.file_name}'? This action cannot be undone."),
            actions=[
                ft.TextButton("Cancel", on_click=on_cancel_delete),
                ft.TextButton("Delete", on_click=on_confirm_delete, style=ft.ButtonStyle(color=ft.CupertinoColors.SYSTEM_RED)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        e.page.open(dlg)